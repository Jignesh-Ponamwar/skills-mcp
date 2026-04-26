#!/usr/bin/env python3
"""
SKILL.md validator — used by GitHub Actions CI on every PR.

Validates every SKILL.md file under skill_mcp/skills_data/ for:
  1. Parseable YAML frontmatter
  2. Required fields: name, description, license, metadata.triggers
  3. Field type and length constraints
  4. Prompt-injection scan (uses skill_mcp.security.prompt_injection)
  5. Tier-3 file references in body match actual files on disk

Exits 0 on success, 1 on any BLOCKED finding or schema violation,
2 on internal error.

Usage:
    python scripts/validate_skills.py [--skills-dir PATH] [--strict] [--json]

Options:
    --skills-dir PATH   Override default skills_data directory
    --strict            Treat MEDIUM warnings as failures (CI strict mode)
    --json              Output results as JSON (for GitHub Actions annotations)
    --changed-only      Only validate changed files (reads from stdin, one path/line)
"""

from __future__ import annotations

import argparse
import json as json_mod
import sys
from pathlib import Path

# Ensure the project root is on the path so we can import skill_mcp
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

try:
    import yaml
except ImportError:
    print("[validate] ERROR: PyYAML not installed — run: pip install PyYAML", file=sys.stderr)
    sys.exit(2)

try:
    from skill_mcp.security.prompt_injection import scan_skill, Severity
except ImportError as e:
    print(f"[validate] ERROR: cannot import scanner: {e}", file=sys.stderr)
    sys.exit(2)


# ── Schema rules ───────────────────────────────────────────────────────────────

REQUIRED_FRONTMATTER = ["name", "description", "license"]
REQUIRED_METADATA = ["triggers"]

MAX_DESCRIPTION_CHARS = 600
MAX_TRIGGER_CHARS = 120
MAX_TRIGGERS = 30
MIN_TRIGGERS = 1
ALLOWED_LICENSES = {"Apache-2.0", "MIT", "BSD-2-Clause", "BSD-3-Clause", "MPL-2.0", "CC0-1.0"}
VALID_TAG_PATTERN = __import__("re").compile(r"^[a-z0-9][a-z0-9._-]{0,39}$")


def _parse_frontmatter(path: Path) -> tuple[dict, str] | None:
    """Parse SKILL.md; return (frontmatter_dict, body_str) or None on error."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        return None, str(e)

    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, "Missing YAML frontmatter delimiters (expected two '---' lines)"

    try:
        fm = yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        return None, f"YAML parse error: {e}"

    if not isinstance(fm, dict):
        return None, "Frontmatter is not a YAML mapping"

    body = parts[2].strip()
    return fm, body


def _validate_schema(slug: str, fm: dict, body: str) -> list[str]:
    """Return a list of human-readable schema violation messages (empty = OK)."""
    errors: list[str] = []

    # Required top-level fields
    for field in REQUIRED_FRONTMATTER:
        if not fm.get(field):
            errors.append(f"Missing required frontmatter field: '{field}'")

    # name must match the directory slug
    name = str(fm.get("name") or "")
    if name and name != slug:
        errors.append(
            f"Field 'name' ({name!r}) does not match directory slug ({slug!r})"
        )

    # description length
    desc = str(fm.get("description") or "").strip()
    if desc and len(desc) > MAX_DESCRIPTION_CHARS:
        errors.append(
            f"'description' is {len(desc)} chars (max {MAX_DESCRIPTION_CHARS}). "
            f"Write it from the agent's perspective — concise trigger sentences, not a manual."
        )

    # license
    lic = str(fm.get("license") or "")
    if lic and lic not in ALLOWED_LICENSES:
        errors.append(
            f"License {lic!r} not in allowed list: {sorted(ALLOWED_LICENSES)}. "
            f"Use a standard SPDX identifier."
        )

    # metadata block
    meta = fm.get("metadata")
    if not isinstance(meta, dict):
        errors.append("Missing or malformed 'metadata' block (must be a YAML mapping)")
        return errors  # Cannot validate sub-fields without metadata

    for field in REQUIRED_METADATA:
        if not meta.get(field):
            errors.append(f"Missing required metadata field: 'metadata.{field}'")

    # triggers validation
    triggers = meta.get("triggers") or []
    if not isinstance(triggers, list):
        errors.append("'metadata.triggers' must be a YAML list")
    else:
        if len(triggers) < MIN_TRIGGERS:
            errors.append(
                f"'metadata.triggers' has {len(triggers)} item(s) — "
                f"minimum is {MIN_TRIGGERS}. Add natural-language trigger phrases."
            )
        if len(triggers) > MAX_TRIGGERS:
            errors.append(
                f"'metadata.triggers' has {len(triggers)} items (max {MAX_TRIGGERS})"
            )
        for i, t in enumerate(triggers):
            if not isinstance(t, str):
                errors.append(f"trigger[{i}] is not a string (got {type(t).__name__})")
            elif len(t) > MAX_TRIGGER_CHARS:
                errors.append(
                    f"trigger[{i}] is {len(t)} chars (max {MAX_TRIGGER_CHARS}): {t[:60]!r}…"
                )

    # tags validation (optional, but if present must be valid slugs)
    tags = meta.get("tags") or []
    if isinstance(tags, list):
        for i, tag in enumerate(tags):
            if isinstance(tag, str) and not VALID_TAG_PATTERN.match(tag):
                errors.append(
                    f"tag[{i}] {tag!r} contains invalid characters. "
                    f"Use lowercase letters, numbers, hyphens, dots only."
                )

    # body must exist
    if not body:
        errors.append("SKILL.md body is empty — the body is what agents actually read")

    return errors


def _check_tier3_references(slug: str, body: str, skill_folder: Path) -> list[str]:
    """
    Warn if the body text mentions specific filenames that don't exist on disk.
    This catches typos in tier-3 file references before they confuse agents.
    """
    import re
    warnings: list[str] = []

    # Look for patterns like "references/FOO.md", "scripts/bar.py", "assets/baz.md"
    pattern = re.compile(
        r"(?:references|scripts|assets)/([A-Za-z0-9_\-\.]+\.[a-z]{1,5})"
    )
    for match in pattern.finditer(body):
        ref_path = skill_folder / match.group(0).replace("/", Path.cwd().drive and "\\" or "/")
        # Normalise to OS path
        ref_path = skill_folder / Path(match.group(0))
        if not ref_path.exists():
            warnings.append(
                f"Body references '{match.group(0)}' but file not found on disk — "
                f"agents will fail to load it"
            )
    return warnings


# ── Result types ───────────────────────────────────────────────────────────────

class Status:
    CLEAN = "clean"
    WARNED = "warned"
    FAILED = "failed"


def _validate_one(path: Path, strict: bool = False) -> dict:
    """Validate a single SKILL.md file. Returns a result dict."""
    slug = path.parent.name
    result = {
        "skill_id": slug,
        "path": str(path),
        "status": Status.CLEAN,
        "errors": [],
        "warnings": [],
    }

    # 1. Parse
    parsed = _parse_frontmatter(path)
    if parsed is None or isinstance(parsed[0], type(None)):
        _, msg = parsed if parsed else (None, "unknown parse error")
        result["errors"].append(f"Parse error: {msg}")
        result["status"] = Status.FAILED
        return result

    fm, body = parsed

    # 2. Schema validation
    schema_errors = _validate_schema(slug, fm, body)
    if schema_errors:
        result["errors"].extend(schema_errors)
        result["status"] = Status.FAILED

    # 3. Tier-3 reference check
    skill_folder = path.parent
    meta = fm.get("metadata") or {}
    tier3_warnings = _check_tier3_references(slug, body, skill_folder)
    if tier3_warnings:
        result["warnings"].extend(tier3_warnings)
        if result["status"] == Status.CLEAN:
            result["status"] = Status.WARNED

    # 4. Prompt-injection scan
    desc = str(fm.get("description") or "").strip()
    triggers = list(meta.get("triggers") or [])
    name = str(fm.get("name") or slug)

    scan = scan_skill(
        skill_id=slug,
        name=name,
        description=desc,
        body=body,
        triggers=triggers,
    )

    for finding in scan.critical_and_high:
        loc = f" (line {finding.line})" if finding.line else ""
        result["errors"].append(
            f"[{finding.severity.value}] {finding.category}{loc}: {finding.description}"
            + (f" | {finding.excerpt!r}" if finding.excerpt else "")
        )
        result["status"] = Status.FAILED

    for finding in scan.warnings:
        loc = f" (line {finding.line})" if finding.line else ""
        msg = (
            f"[{finding.severity.value}] {finding.category}{loc}: {finding.description}"
            + (f" | {finding.excerpt!r}" if finding.excerpt else "")
        )
        result["warnings"].append(msg)
        if strict and result["status"] == Status.CLEAN:
            result["errors"].append(msg)
            result["status"] = Status.FAILED
        elif result["status"] == Status.CLEAN:
            result["status"] = Status.WARNED

    return result


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Validate SKILL.md files")
    parser.add_argument(
        "--skills-dir",
        type=Path,
        default=_ROOT / "skill_mcp" / "skills_data",
        help="Directory containing skill subfolders",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat MEDIUM/LOW security warnings as failures",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output results as JSON array",
    )
    parser.add_argument(
        "--changed-only",
        action="store_true",
        help="Read changed file paths from stdin (one per line) and validate only those",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Specific SKILL.md files or skill directories to validate (overrides --skills-dir)",
    )
    args = parser.parse_args()

    # Collect files to validate
    if args.paths:
        skill_files: list[Path] = []
        for p in args.paths:
            if p.name == "SKILL.md":
                skill_files.append(p)
            elif p.is_dir():
                candidate = p / "SKILL.md"
                if candidate.exists():
                    skill_files.append(candidate)
    elif args.changed_only:
        stdin_lines = sys.stdin.read().splitlines()
        skill_files = []
        for line in stdin_lines:
            p = Path(line.strip())
            if p.name == "SKILL.md" and p.exists():
                skill_files.append(p)
            elif p.exists() and (p / "SKILL.md").exists():
                skill_files.append(p / "SKILL.md")
    else:
        skill_files = sorted(args.skills_dir.glob("*/SKILL.md"))

    if not skill_files:
        print("[validate] No SKILL.md files found to validate.")
        return 0

    print(f"[validate] Checking {len(skill_files)} SKILL.md file(s)…\n")

    results = [_validate_one(p, strict=args.strict) for p in skill_files]

    if args.json_output:
        print(json_mod.dumps(results, indent=2))
    else:
        for r in results:
            status_icon = {"clean": "✓", "warned": "⚠", "failed": "✗"}.get(r["status"], "?")
            print(f"  {status_icon} {r['skill_id']}")
            for err in r["errors"]:
                print(f"      ERROR: {err}")
            for warn in r["warnings"]:
                print(f"      WARN:  {warn}")

    # Summary
    n_failed = sum(1 for r in results if r["status"] == Status.FAILED)
    n_warned = sum(1 for r in results if r["status"] == Status.WARNED)
    n_clean  = sum(1 for r in results if r["status"] == Status.CLEAN)

    print(
        f"\n[validate] Results: {n_clean} clean · {n_warned} warned · {n_failed} failed"
        f" (of {len(results)} total)"
    )

    if n_failed > 0:
        print(
            f"[validate] FAILED — fix the {n_failed} error(s) above before merging.",
            file=sys.stderr,
        )
        return 1

    print("[validate] All skills passed validation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
