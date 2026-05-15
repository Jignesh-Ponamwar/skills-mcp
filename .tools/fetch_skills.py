#!/usr/bin/env python3
"""Assemble SKILL.md files from manifest + per-skill source excerpts on disk.

For each skill in the manifest, we expect (optionally) a file at
    skill_mcp/skills_data/{skill_id}/references/source_excerpt.md
that was fetched from the official source URL by a subagent.

If present, its content becomes the body of the generated SKILL.md.
If absent, the body falls back to a short stub pointing to the source URL.
"""
import json, os, re, sys, unicodedata
from pathlib import Path
import yaml

ROOT = Path("/sessions/optimistic-adoring-ramanujan/mnt/Skillsovermcp")
MANIFEST = ROOT / "skills_expansion_manifest.json"
SKILLS_DIR = ROOT / "skill_mcp" / "skills_data"

LICENSE_MAP = {
    "Pallets": "BSD-3-Clause", "Sebastian Ramirez": "MIT",
    "Sebastián Ramírez": "MIT", "Rails Core Team": "MIT",
    "Pivotal Software": "Apache-2.0", "Microsoft": "MIT",
    "Nest.js Team": "MIT", "Fiber Team": "MIT", "Gin Team": "MIT",
    "Tokio Team": "MIT", "Laravel Team": "MIT", "Express.js Team": "MIT",
    "Phoenix Team": "MIT", "Meta": "MIT", "Google": "MIT",
    "Rich Harris": "MIT", "Ryan Carniato": "MIT", "Astro Team": "MIT",
    "Remix Team": "MIT", "Svelte Team": "MIT", "Builder.io": "MIT",
    "Carson Gross": "BSD-2-Clause", "MDN": "CC-BY-SA-2.5",
    "Caleb Porzio": "MIT",
    "PostgreSQL Global Development Group": "PostgreSQL", "MongoDB": "SSPL",
    "Oracle": "GPL-2.0", "AWS": "Apache-2.0", "Redis": "BSD-3-Clause",
    "Elastic": "Elastic-2.0", "Apache": "Apache-2.0",
    "CockroachDB": "BSL-1.1", "PlanetScale": "Apache-2.0",
    "Cloud Native Computing Foundation": "Apache-2.0", "CNCF": "Apache-2.0",
    "Docker": "Apache-2.0", "HashiCorp": "BSL-1.1",
    "Grafana": "AGPL-3.0", "GitLab": "MIT", "CircleCI": "Proprietary",
    "LangChain": "MIT", "Together AI": "Apache-2.0", "dbt Labs": "Apache-2.0",
    "Hugging Face": "Apache-2.0", "Pinecone": "Proprietary",
    "OpenAI": "Proprietary", "Anthropic": "Proprietary", "Ollama": "MIT",
    "Apple": "Proprietary", "JetBrains": "Apache-2.0", "Expo": "MIT",
    "IETF": "RFC", "Cloudflare": "CC-BY-4.0", "OWASP": "CC-BY-SA-4.0",
}
PLATFORMS = ["claude-code", "cursor", "windsurf", "any"]

EM_DASH = "—"
EN_DASH = "–"
SMART = {
    "‘":"'", "’":"'", "“":'"', "”":'"',
    "…":"...", " ":" ", EM_DASH:"-", EN_DASH:"-",
    "‐":"-", "‑":"-", "‒":"-", "―":"-",
    "﹘":"-", "﹣":"-", "－":"-",
}
def sanitize(t):
    if not t: return t
    for k,v in SMART.items(): t = t.replace(k, v)
    t = unicodedata.normalize("NFKC", t)
    return t.replace(EM_DASH, "-").replace(EN_DASH, "-")

USE_CASE_TEMPLATES = {
    "Backend Frameworks": ["Build REST APIs with {n}", "Develop server-side web applications with {n}", "Implement authentication and database access in {n}", "Deploy {n} services to production"],
    "Frontend Frameworks": ["Build interactive UI components with {n}", "Manage application state and routing in {n}", "Optimize rendering and performance in {n}", "Test and deploy {n} applications"],
    "Databases": ["Design schemas and data models for {n}", "Write efficient queries against {n}", "Operate, scale, and back up {n}", "Integrate {n} with applications"],
    "DevOps & Infrastructure": ["Provision and manage infrastructure with {n}", "Automate deployments and CI/CD with {n}", "Monitor and observe systems using {n}", "Troubleshoot production issues in {n}"],
    "AI/ML & Data": ["Build production AI/ML pipelines with {n}", "Integrate {n} into existing applications", "Evaluate and tune {n} workloads", "Operate {n} at scale"],
    "Mobile Development": ["Build cross-platform mobile apps with {n}", "Implement navigation, state, and storage in {n}", "Integrate native APIs through {n}", "Ship {n} apps to the App Store and Play Store"],
    "Security & Auth": ["Apply {n} to secure applications and APIs", "Audit existing systems against {n} guidance", "Implement {n} controls in code and infrastructure", "Train teams on {n} fundamentals"],
}
PREREQS = {
    "Backend Frameworks": ["Programming fundamentals", "HTTP and REST basics", "SQL or NoSQL familiarity"],
    "Frontend Frameworks": ["HTML, CSS, JavaScript", "Basic build tooling (Node, npm)", "Component-based UI concepts"],
    "Databases": ["Basic SQL or query language familiarity", "Command-line basics", "Networking basics"],
    "DevOps & Infrastructure": ["Linux command line", "Containers and networking basics", "Cloud account or local lab"],
    "AI/ML & Data": ["Python programming", "Basic ML or data engineering", "API and HTTP basics"],
    "Mobile Development": ["JavaScript or platform language basics", "Mobile UI concepts", "Build tooling for the platform"],
    "Security & Auth": ["HTTP and TLS basics", "Web application fundamentals", "Threat modeling familiarity"],
}
def derive_complexity(c):
    return "advanced" if c in ("Security & Auth","DevOps & Infrastructure","AI/ML & Data") else "intermediate"
def est_time(c):
    return {"beginner":"10-20 minutes","intermediate":"20-40 minutes","advanced":"30-60 minutes"}[c]
def derive_triggers(name, tags):
    out, seen = [], set()
    for t in tags + [name.lower(), name.lower().split()[0]]:
        s = t.strip().lower()
        if s and s not in seen:
            seen.add(s); out.append(s)
    return out[:10]
def make_description(name, raw_desc, tags):
    base = sanitize(raw_desc or "").strip()
    base = re.sub(r"\s+", " ", base)
    if 100 <= len(base) <= 200:
        return base
    if len(base) > 200:
        return base[:197].rsplit(" ", 1)[0] + "..."
    extra = ", ".join(t for t in tags if t.lower() not in name.lower())[:80]
    cand = f"Official {name} documentation guide covering {extra}, with examples, core concepts, and best practices."
    if base:
        cand = f"{base} Covers {extra}, with examples and best practices."
    if len(cand) < 100:
        cand += " Includes setup, configuration, integration patterns, and production guidance."
    if len(cand) > 200:
        cand = cand[:197].rsplit(" ", 1)[0] + "..."
    return sanitize(cand)

def parse_excerpt(text):
    """Parse a fetched-doc file. First non-empty line treated as a hint description.
    Body is the rest of the file (already markdown)."""
    text = sanitize(text or "")
    lines = text.splitlines()
    desc, body_start = "", 0
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s and not s.startswith("#") and not s.startswith(">"):
            desc = s
            body_start = i + 1
            break
    body = "\n".join(lines[body_start:]).strip() if body_start else text
    return desc, body

def truncate_md(md, mx=9000):
    if len(md) <= mx: return md
    cut = md[:mx].rfind("\n## ")
    if cut > mx*0.5:
        return md[:cut].rstrip() + "\n\n[Excerpt truncated. See source URL for the full documentation.]"
    return md[:mx].rstrip() + "\n\n[Excerpt truncated. See source URL for the full documentation.]"

def build_skill_md(skill, fetched_desc, body_md):
    name = skill["name"]; cat = skill["category"]; tags = skill["tags"]
    author = skill["author"]; lic = LICENSE_MAP.get(author, "See source")
    cx = derive_complexity(cat)
    desc = make_description(name, fetched_desc, tags)
    use_cases = [t.format(n=name) for t in USE_CASE_TEMPLATES.get(cat, [f"Apply {name} in real projects"])]
    prereqs = PREREQS.get(cat, ["General programming experience"])
    fm = {
        "name": name, "description": desc, "author": author,
        "version": skill["version"], "license": lic,
        "metadata": {
            "tags": tags, "platforms": PLATFORMS,
            "triggers": derive_triggers(name, tags),
            "use_cases": use_cases,
            "estimated_time": est_time(cx),
            "complexity_level": cx,
            "prerequisites": prereqs,
            "source_url": skill["source_url"],
            "last_updated": "2026-05-15",
            "has_tier3": False,
        },
    }
    yaml_text = yaml.safe_dump(fm, sort_keys=False, allow_unicode=False, default_flow_style=False, width=1000)
    yaml_text = sanitize(yaml_text)
    body = sanitize(body_md or f"This skill points to the official documentation at {skill['source_url']}. The fetcher was unable to capture an excerpt; please consult the source URL above for full content.")
    body = truncate_md(body)
    md = (
        f"---\n{yaml_text}---\n\n"
        f"# {sanitize(name)}\n\n"
        f"> Source: {skill['source_url']}\n\n"
        f"{body}\n\n---\n\n## Source\n\n"
        f"This skill is sourced from the official documentation at {skill['source_url']}.\n"
        f"Author: {sanitize(author)} | Version: {skill['version']} | License: {lic}\n"
    )
    md = sanitize(md)
    if EM_DASH in md or EN_DASH in md:
        raise RuntimeError("dash leaked")
    return md

def build_one(skill):
    sid = skill["skill_id"]
    target = SKILLS_DIR / sid
    target.mkdir(parents=True, exist_ok=True)
    for sub in ("references","scripts","assets"):
        (target/sub).mkdir(exist_ok=True)
        gk = target/sub/".gitkeep"
        if not gk.exists(): gk.write_text("")
    excerpt = target / "references" / "source_excerpt.md"
    if excerpt.exists():
        desc, body = parse_excerpt(excerpt.read_text(encoding="utf-8", errors="replace"))
        used_excerpt = True
    else:
        desc, body = "", ""
        used_excerpt = False
    md = build_skill_md(skill, desc, body)
    (target/"SKILL.md").write_text(md, encoding="utf-8")
    return {"id": skill["id"], "skill_id": sid, "ok": True,
            "fetched": used_excerpt, "bytes": len(md)}

def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    skills = manifest["skills"]
    selected = skills
    if len(sys.argv) > 1:
        ids = set()
        for part in sys.argv[1].split(","):
            if "-" in part:
                a,b = part.split("-"); ids.update(range(int(a), int(b)+1))
            else:
                ids.add(int(part))
        selected = [s for s in skills if s["id"] in ids]
    rows = []
    for s in selected:
        try:
            rows.append(build_one(s))
        except Exception as e:
            rows.append({"id": s["id"], "skill_id": s["skill_id"], "ok": False, "error": str(e)})
            print(f"  FAILED {s['skill_id']}: {e}", file=sys.stderr)
    ok = sum(1 for r in rows if r.get("ok"))
    fetched = sum(1 for r in rows if r.get("fetched"))
    print(f"Built: {ok}/{len(rows)} | with-excerpt: {fetched}")
    for r in rows:
        flag = "ok" if r.get("ok") else "FAIL"
        ext = "+ex" if r.get("fetched") else "stub"
        print(f"  [{r['id']:>2}] {flag:4} {ext:4} {r['skill_id']}")

if __name__ == "__main__":
    main()
