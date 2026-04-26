"""
Idempotent seed script — populates all six Qdrant collections from the
structured skills_data/ directory.

Embeddings are generated via the Cloudflare Workers AI REST API
(@cf/baai/bge-small-en-v1.5, 384-dim) — the same model used by the
deployed Worker at query time. No local GPU or sentence-transformers needed.

Requires in .env:
  QDRANT_URL       — Qdrant Cloud cluster URL
  QDRANT_API_KEY   — Qdrant Cloud API key
  WORKERS_AI_ACCOUNT_ID    — Cloudflare account ID (dashboard → right sidebar)
  WORKERS_AI_API_TOKEN     — Cloudflare API token with "Workers AI Run" permission

Tier-1/2 (pass 1):
  Reads skills_data/<slug>/SKILL.md, embeds frontmatter description+triggers,
  upserts to skill_frontmatter, skill_body, skill_options.

Tier-3 (pass 2):
  For each skill folder, looks for:
    references/*.md   → upserted to skill_references
    scripts/*.py etc. → upserted to skill_scripts (source stored, never returned to agents)
    assets/*          → upserted to skill_assets

Usage:
    python -m skill_mcp.seed.seed_skills
    python -m skill_mcp.seed.seed_skills --skills-dir path/to/skills_data
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()


# ── Cloudflare Workers AI embedding ──────────────────────────────────────────

_CF_AI_URL = (
    "https://api.cloudflare.com/client/v4/accounts/{account_id}"
    "/ai/run/@cf/baai/bge-small-en-v1.5"
)


def _get_workers_ai_credentials() -> tuple[str, str]:
    """Read WORKERS_AI_ACCOUNT_ID and WORKERS_AI_API_TOKEN from environment, exit on missing."""
    account_id = os.getenv("WORKERS_AI_ACCOUNT_ID", "")
    api_token = os.getenv("WORKERS_AI_API_TOKEN", "")
    if not account_id or not api_token:
        print(
            "[seed] ERROR: WORKERS_AI_ACCOUNT_ID and WORKERS_AI_API_TOKEN must be set in .env\n"
            "       Get them at https://dash.cloudflare.com\n"
            "       Token needs 'Workers AI Run' permission.",
            file=sys.stderr,
        )
        sys.exit(1)
    return account_id, api_token




def _embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed all texts in a single Cloudflare Workers AI API call.

    The @cf/baai/bge-small-en-v1.5 endpoint accepts an array of texts and
    returns an array of vectors in one round-trip — much faster than N
    individual calls for large skill catalogs.
    """
    if not texts:
        return []
    account_id, api_token = _get_workers_ai_credentials()
    print(f"  [embed] sending {len(texts)} texts to Workers AI…", flush=True)
    resp = requests.post(
        _CF_AI_URL.format(account_id=account_id),
        headers={"Authorization": f"Bearer {api_token}"},
        json={"text": texts},
        timeout=60,  # larger timeout for batch
    )
    resp.raise_for_status()
    result = resp.json()
    if not result.get("success"):
        errors = result.get("errors") or []
        msg = "; ".join(str(e.get("message", e)) for e in errors) if errors else "unknown error"
        raise RuntimeError(f"Workers AI batch embedding failed: {msg}")
    vectors: list[list[float]] = result["result"]["data"]
    if len(vectors) != len(texts):
        raise RuntimeError(
            f"Workers AI returned {len(vectors)} vectors for {len(texts)} texts"
        )
    print(f"  [embed] {len(vectors)}/{len(texts)} done", flush=True)
    return vectors

_DEFAULT_SKILLS_DIR = Path(__file__).parent.parent / "skills_data"

# ── Tier-3 helper functions ───────────────────────────────────────────────────

def extract_first_heading_or_paragraph(markdown_content: str) -> str:
    """Extract the first H1/H2 heading, or fall back to first non-empty paragraph."""
    for line in markdown_content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    # No heading — return first non-empty, non-separator paragraph sentence
    for line in markdown_content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("---") and not stripped.startswith("```"):
            # Truncate at first sentence or 120 chars
            sentence = re.split(r"(?<=[.!?])\s", stripped)[0]
            return sentence[:120]
    return ""


def extract_script_description(source: str, language: str) -> str:
    """Extract the first docstring (Python) or first comment block (JS/Bash)."""
    lines = source.splitlines()

    if language == "python":
        # Module-level docstring: starts with """ or '''
        in_docstring = False
        docstring_lines: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not in_docstring:
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    quote = stripped[:3]
                    rest = stripped[3:]
                    if rest.endswith(quote) and len(rest) > 3:
                        return rest[: -3].strip()
                    in_docstring = True
                    if rest:
                        docstring_lines.append(rest)
                elif stripped.startswith("#"):
                    # Fallback: first comment block
                    docstring_lines.append(stripped.lstrip("#").strip())
                elif (stripped
                        and not stripped.startswith("import")
                        and not stripped.startswith("from")):
                    break
            else:
                if stripped.endswith('"""') or stripped.endswith("'''"):
                    last = stripped[: -3].strip()
                    if last:
                        docstring_lines.append(last)
                    break
                docstring_lines.append(stripped)
        text = " ".join(docstring_lines).strip()
        return text[:200] if text else ""

    # JavaScript / Bash / TypeScript — extract leading comment block
    comment_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("#"):
            comment_lines.append(re.sub(r"^[/#!]+\s*", "", stripped))
        elif stripped.startswith("/*"):
            comment_lines.append(re.sub(r"^/\*+\s*", "", stripped))
        elif stripped.startswith("*"):
            comment_lines.append(re.sub(r"^\*+\s*", "", stripped))
        elif stripped.startswith("*/"):
            break
        elif stripped and comment_lines:
            break
    text = " ".join(comment_lines).strip()
    return text[:200] if text else ""


def extract_dependencies(source: str, language: str) -> list[str]:
    """Best-effort: parse import statements (Python) or require() calls (JS)."""
    deps: list[str] = []

    if language == "python":
        for line in source.splitlines():
            stripped = line.strip()
            # import foo  /  import foo as bar
            m = re.match(r"^import\s+([\w.]+)", stripped)
            if m:
                top = m.group(1).split(".")[0]
                if top not in deps:
                    deps.append(top)
            # from foo import bar
            m = re.match(r"^from\s+([\w.]+)\s+import", stripped)
            if m:
                top = m.group(1).split(".")[0]
                if top not in deps:
                    deps.append(top)

    elif language in ("javascript", "typescript"):
        for line in source.splitlines():
            # require('foo')  /  require("foo")
            m = re.search(r'require\(["\']([^"\'./][^"\']*)["\']', line)
            if m and m.group(1) not in deps:
                deps.append(m.group(1))
            # import ... from 'foo'
            m = re.search(r'from\s+["\']([^"\'./][^"\']*)["\']', line)
            if m and m.group(1) not in deps:
                deps.append(m.group(1))

    # Filter out stdlib names we know aren't installable packages
    _stdlib = {
        "os", "sys", "re", "json", "ast", "io", "math", "time", "datetime",
        "pathlib", "typing", "collections", "itertools", "functools",
        "subprocess", "tempfile", "shutil", "hashlib", "hmac", "uuid",
        "logging", "threading", "asyncio", "contextlib", "dataclasses",
        "abc", "copy", "enum", "warnings", "traceback", "inspect",
        "textwrap", "string", "struct", "base64", "urllib", "http",
        "socket", "email", "csv", "xml", "html", "sqlite3",
    }
    return [d for d in deps if d not in _stdlib]


def infer_language(suffix: str) -> str:
    """Map file extension to canonical language name."""
    mapping = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".sh": "bash",
        ".bash": "bash",
        ".zsh": "bash",
    }
    return mapping.get(suffix.lower(), "unknown")


def infer_asset_type(suffix: str) -> str:
    """Classify asset by file extension."""
    if suffix.lower() in (".md", ".txt", ".html", ".rst", ".jinja", ".j2"):
        return "template"
    if suffix.lower() in (".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env"):
        return "config"
    if suffix.lower() in (".csv", ".tsv", ".parquet", ".ndjson"):
        return "data"
    return "other"


# ── SKILL.md parsing ──────────────────────────────────────────────────────────

def _parse_skill_md(path: Path) -> Optional[dict]:
    try:
        import frontmatter
        post = frontmatter.load(str(path))
        return {"frontmatter": dict(post.metadata), "body": post.content.strip()}
    except ImportError:
        return _parse_skill_md_manual(path)


def _parse_skill_md_manual(path: Path) -> Optional[dict]:
    import yaml
    text = path.read_text(encoding="utf-8")
    # Split on exactly the first two "---" delimiters to correctly handle
    # horizontal rules (---) inside the body without truncating them.
    parts = text.split("---", 2)
    if len(parts) < 3:
        print(f"  [warn] Skipping {path}: could not find YAML frontmatter delimiters")
        return None
    try:
        fm = yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        print(f"  [warn] Skipping {path}: YAML parse error — {e}")
        return None
    body = parts[2].strip()
    return {"frontmatter": fm or {}, "body": body}


def _extract_skill_fields(slug: str, parsed: dict) -> dict:
    """Extract and normalise fields from a parsed SKILL.md."""
    fm = parsed["frontmatter"]
    meta = fm.get("metadata") or {}
    # Strip trailing whitespace/newlines from YAML literal-block strings (|, >)
    description = str(fm.get("description") or "").strip()
    return {
        "skill_id": slug,
        "name": str(fm.get("name") or slug).strip(),
        "description": description,
        "license": str(fm.get("license") or "Apache-2.0").strip(),
        "author": str(meta.get("author") or "").strip(),
        "version": str(meta.get("version") or "1.0"),
        "tags": list(meta.get("tags") or []),
        "platforms": list(meta.get("platforms") or []),
        "trigger_phrases": list(meta.get("triggers") or []),
        "skill_uri": f"skill://{slug}/SKILL.md",
        "instructions": parsed["body"],
    }


# ── Main seed function ────────────────────────────────────────────────────────

def seed(skills_dir: Path = _DEFAULT_SKILLS_DIR) -> None:
    """Populate all six Qdrant collections from the skills_data/ directory."""
    from ..db.qdrant_manager import qdrant_manager
    from ..models.skill import (
        SkillAsset,
        SkillBody,
        SkillFrontMatter,
        SkillOptions,
        SkillReference,
        SkillScript,
    )

    if not skills_dir.is_dir():
        print(f"[seed] ERROR: skills directory not found: {skills_dir}", file=sys.stderr)
        sys.exit(1)

    skill_paths = sorted(skills_dir.glob("*/SKILL.md"))
    if not skill_paths:
        print(f"[seed] ERROR: no SKILL.md files found in {skills_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"[seed] Found {len(skill_paths)} SKILL.md files in {skills_dir}")

    # ── Pass 1: Parse and seed Tier-1/2 ──────────────────────────────────────

    skills = []
    for skill_path in skill_paths:
        slug = skill_path.parent.name
        parsed = _parse_skill_md(skill_path)
        if parsed is None:
            continue
        fields = _extract_skill_fields(slug, parsed)
        skills.append(fields)
        print(f"  [parsed] {slug}: {fields['name']}")

    if not skills:
        print("[seed] ERROR: no skills parsed successfully", file=sys.stderr)
        sys.exit(1)

    print("\n[seed] Connecting to Qdrant…")
    qdrant_manager.connect()
    qdrant_manager.ensure_collections()
    print("[seed] Collections ready (6 total — tiers 1, 2, and 3)")

    # Embed description + trigger_phrases (frontmatter only — never the body)
    embed_texts = [
        s["description"] + " " + " ".join(s["trigger_phrases"])
        for s in skills
    ]
    print(f"\n[seed] Embedding {len(embed_texts)} skill descriptors via Cloudflare Workers AI…")
    vectors = _embed_batch(embed_texts)

    frontmatters = [
        SkillFrontMatter(
            skill_id=s["skill_id"],
            name=s["name"],
            description=s["description"],
            trigger_phrases=s["trigger_phrases"],
            tags=s["tags"],
            platforms=s["platforms"],
            version=s["version"],
            author=s["author"],
            license=s["license"],
            skill_uri=s["skill_uri"],
        )
        for s in skills
    ]
    bodies = [SkillBody(skill_id=s["skill_id"], instructions=s["instructions"]) for s in skills]
    options_list = [SkillOptions(skill_id=s["skill_id"]) for s in skills]

    qdrant_manager.upsert_many_frontmatter(list(zip(frontmatters, vectors)))
    print(f"[seed] Upserted {len(frontmatters)} frontmatter points (with vectors)")

    qdrant_manager.upsert_many_body(bodies)
    print(f"[seed] Upserted {len(bodies)} body points")

    qdrant_manager.upsert_many_options(options_list)
    print(f"[seed] Upserted {len(options_list)} options points")

    # ── Pass 2: Seed Tier-3 assets ────────────────────────────────────────────

    print("\n[seed] Seeding tier-3 assets (references, scripts, assets)…")
    ref_count = script_count = asset_count = 0

    _MAX_FILE_BYTES = 1_048_576  # 1 MB — skip files larger than this

    def _safe_path(file: Path, base_dir: Path) -> bool:
        """Return True only if *file* resolves to a path inside *base_dir*.

        Rejects symlinks that point outside the skill folder — prevents a
        maliciously crafted skill directory from reading arbitrary host files.
        Uses Path.parents for cross-platform correctness (no string separator hacks).
        """
        try:
            resolved = file.resolve()
            base_resolved = base_dir.resolve()
            return resolved == base_resolved or base_resolved in resolved.parents
        except OSError:
            return False

    for skill_path in skill_paths:
        slug = skill_path.parent.name
        skill_folder = skill_path.parent
        skill_name = next(
            (s["name"] for s in skills if s["skill_id"] == slug), slug
        )

        # ── References ───────────────────────────────────────────────────────

        refs_dir = skill_folder / "references"
        if refs_dir.is_dir():
            for ref_file in sorted(refs_dir.glob("*.md")):
                if not _safe_path(ref_file, refs_dir):
                    print(f"  [warn] Skipping {slug}/references/{ref_file.name}: path traversal detected")
                    continue
                if ref_file.stat().st_size > _MAX_FILE_BYTES:
                    print(f"  [warn] Skipping {slug}/references/{ref_file.name}: exceeds 1 MB size limit")
                    continue
                content = ref_file.read_text(encoding="utf-8")
                description = extract_first_heading_or_paragraph(content)
                ref = SkillReference(
                    skill_id=slug,
                    skill_name=skill_name,
                    filename=ref_file.name,
                    content=content,
                    description=description,
                    file_path=f"references/{ref_file.name}",
                )
                qdrant_manager.upsert_reference(ref)
                ref_count += 1
                print(f"  ↳ reference: {slug}/{ref_file.name}")

        # ── Scripts ──────────────────────────────────────────────────────────

        scripts_dir = skill_folder / "scripts"
        if scripts_dir.is_dir():
            for script_file in sorted(scripts_dir.iterdir()):
                if script_file.suffix not in (".py", ".js", ".ts", ".sh", ".bash"):
                    continue
                if not _safe_path(script_file, scripts_dir):
                    print(f"  [warn] Skipping {slug}/scripts/{script_file.name}: path traversal detected")
                    continue
                if script_file.stat().st_size > _MAX_FILE_BYTES:
                    print(f"  [warn] Skipping {slug}/scripts/{script_file.name}: exceeds 1 MB size limit")
                    continue
                source = script_file.read_text(encoding="utf-8")
                language = infer_language(script_file.suffix)
                description = extract_script_description(source, language)
                dependencies = extract_dependencies(source, language)
                script = SkillScript(
                    skill_id=slug,
                    skill_name=skill_name,
                    filename=script_file.name,
                    language=language,
                    source=source,
                    description=description,
                    file_path=f"scripts/{script_file.name}",
                    dependencies=dependencies,
                )
                qdrant_manager.upsert_script(script)
                script_count += 1
                print(f"  ↳ script: {slug}/{script_file.name} ({language})")

        # ── Assets ───────────────────────────────────────────────────────────

        assets_dir = skill_folder / "assets"
        if assets_dir.is_dir():
            for asset_file in sorted(assets_dir.iterdir()):
                if asset_file.is_dir():
                    continue
                if not _safe_path(asset_file, assets_dir):
                    print(f"  [warn] Skipping {slug}/assets/{asset_file.name}: path traversal detected")
                    continue
                if asset_file.stat().st_size > _MAX_FILE_BYTES:
                    print(f"  [warn] Skipping {slug}/assets/{asset_file.name}: exceeds 1 MB size limit")
                    continue
                try:
                    content = asset_file.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                asset_type = infer_asset_type(asset_file.suffix)
                description = extract_first_heading_or_paragraph(content)
                asset = SkillAsset(
                    skill_id=slug,
                    skill_name=skill_name,
                    filename=asset_file.name,
                    content=content,
                    asset_type=asset_type,
                    description=description,
                    file_path=f"assets/{asset_file.name}",
                )
                qdrant_manager.upsert_asset(asset)
                asset_count += 1
                print(f"  ↳ asset: {slug}/{asset_file.name} ({asset_type})")

    print(
        f"\n[seed] Tier-3 complete — "
        f"{ref_count} references, {script_count} scripts, {asset_count} assets"
    )
    print("[seed] Done — all six collections populated successfully")
    print(f"[seed] Skills loaded: {', '.join(s['skill_id'] for s in skills)}")


def main() -> None:
    """CLI entry point: parse --skills-dir argument and run the seed function."""
    parser = argparse.ArgumentParser(
        description="Seed Qdrant with skills from the skills_data/ directory"
    )
    parser.add_argument(
        "--skills-dir",
        type=Path,
        default=_DEFAULT_SKILLS_DIR,
        help="Path to the directory containing skill subfolders with SKILL.md files",
    )
    args = parser.parse_args()
    seed(skills_dir=args.skills_dir)


if __name__ == "__main__":
    main()
