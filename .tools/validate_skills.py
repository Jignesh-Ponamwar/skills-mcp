#!/usr/bin/env python3
"""Validate every manifest skill: directory exists, SKILL.md valid YAML, no em-dash anywhere, gitkeep present."""
import json, sys, re
from pathlib import Path
import yaml

ROOT = Path("/sessions/optimistic-adoring-ramanujan/mnt/Skillsovermcp")
MANIFEST = ROOT / "skills_expansion_manifest.json"
SKILLS_DIR = ROOT / "skill_mcp" / "skills_data"

REQUIRED_TOP = ["name","description","author","version","license","metadata"]
REQUIRED_META = ["tags","platforms","triggers","use_cases","estimated_time",
                 "complexity_level","prerequisites","source_url","last_updated","has_tier3"]

EM_DASH = "—"
EN_DASH = "–"

def parse_frontmatter(text):
    if not text.startswith("---"):
        return None, "no frontmatter"
    end = text.find("\n---", 3)
    if end == -1:
        return None, "no closing ---"
    try:
        fm = yaml.safe_load(text[3:end])
        return fm, None
    except Exception as e:
        return None, f"yaml error: {e}"

def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    skills = manifest["skills"]
    errors, warnings = [], []
    for s in skills:
        sid = s["skill_id"]
        d = SKILLS_DIR / sid
        if not d.is_dir():
            errors.append(f"{sid}: directory missing")
            continue
        for sub in ("references","scripts","assets"):
            gk = d / sub / ".gitkeep"
            if not gk.exists():
                errors.append(f"{sid}: missing {sub}/.gitkeep")
        skill_md = d / "SKILL.md"
        if not skill_md.exists():
            errors.append(f"{sid}: SKILL.md missing")
            continue
        text = skill_md.read_text(encoding="utf-8", errors="replace")
        if EM_DASH in text:
            errors.append(f"{sid}: contains em-dash")
        if EN_DASH in text:
            errors.append(f"{sid}: contains en-dash")
        fm, err = parse_frontmatter(text)
        if err:
            errors.append(f"{sid}: {err}")
            continue
        for k in REQUIRED_TOP:
            if k not in fm:
                errors.append(f"{sid}: missing top-level '{k}'")
        meta = fm.get("metadata") or {}
        for k in REQUIRED_META:
            if k not in meta:
                errors.append(f"{sid}: missing metadata.{k}")
        desc = fm.get("description","")
        if not (50 <= len(desc) <= 220):
            warnings.append(f"{sid}: description length {len(desc)} (target 100-200)")
        if not meta.get("source_url"):
            errors.append(f"{sid}: empty source_url")
    n = len(skills)
    built = sum(1 for s in skills if (SKILLS_DIR/s["skill_id"]/"SKILL.md").exists())
    print(f"Skills in manifest: {n}")
    print(f"SKILL.md present:   {built}")
    print(f"Errors:             {len(errors)}")
    print(f"Warnings:           {len(warnings)}")
    for e in errors: print("  ERR ", e)
    for w in warnings[:10]: print("  warn", w)
    if warnings[10:]:
        print(f"  warn ... and {len(warnings)-10} more")
    sys.exit(1 if errors else 0)

if __name__ == "__main__":
    main()
