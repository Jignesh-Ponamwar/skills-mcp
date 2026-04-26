"""
Prompt-injection scanner for the SKILL.md ingestion pipeline.

A malicious SKILL.md with embedded instruction overrides could alter how agents
behave after loading the skill body — turning the skills registry into a
prompt-injection delivery mechanism. This scanner runs at seed time and in CI
to reject or flag suspicious content before it enters the vector database.

Attack surfaces covered
-----------------------
1. Instruction-override phrases    — "ignore previous instructions", "disregard", etc.
2. Role / identity hijacking       — "you are now", "act as DAN", "pretend you are"
3. Prompt delimiter injection      — </system>, [SYSTEM], <<SYS>>, <|im_start|>, etc.
4. Credential exfiltration         — patterns that direct the agent to send secrets
5. HTML / script injection         — <script>, javascript:, data:text/html, iframe
6. Unicode attacks                 — BiDi override chars, zero-width spaces, null bytes
7. Base64 encoded payloads         — long base64 chunks that decode to override content
8. Content displacement            — ≥20 consecutive blank lines (pushes body off-screen)
9. Suspiciously long lines         — >2000 chars (possible encoded or obfuscated payload)

Severity levels
---------------
CRITICAL  — Definite injection attempt; ingestion is BLOCKED
HIGH      — Strong indicator; ingestion is BLOCKED
MEDIUM    — Suspicious; ingestion continues with a WARNING flag in the skill metadata
LOW       — Minor concern; logged only

Usage
-----
    from skill_mcp.security.prompt_injection import scan_skill

    result = scan_skill(
        skill_id="my-skill",
        name="My Skill",
        description="...",
        body="# My Skill\\n...",
        triggers=["do the thing", "handle the task"],
    )
    if result.blocked:
        raise ValueError(result.summary())
    for warning in result.warnings:
        print(warning)

CLI (for manual inspection)
----------------------------
    python -m skill_mcp.security.prompt_injection path/to/SKILL.md
"""

from __future__ import annotations

import argparse
import base64
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Sequence


# ── Severity & data classes ────────────────────────────────────────────────────

class Severity(str, Enum):
    CRITICAL = "CRITICAL"   # Block ingestion
    HIGH = "HIGH"            # Block ingestion
    MEDIUM = "MEDIUM"        # Warn, continue
    LOW = "LOW"              # Log only


@dataclass
class Finding:
    severity: Severity
    category: str
    description: str
    excerpt: str = ""         # Short, sanitised excerpt of the matching text
    line: int | None = None   # 1-indexed line number, if known


@dataclass
class ScanResult:
    skill_id: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        """True when any finding has CRITICAL or HIGH severity."""
        return any(f.severity in (Severity.CRITICAL, Severity.HIGH) for f in self.findings)

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity in (Severity.MEDIUM, Severity.LOW)]

    @property
    def critical_and_high(self) -> list[Finding]:
        return [f for f in self.findings if f.severity in (Severity.CRITICAL, Severity.HIGH)]

    def summary(self) -> str:
        status = "BLOCKED" if self.blocked else ("WARNED" if self.warnings else "CLEAN")
        lines = [f"[scan:{status}] {self.skill_id} — {len(self.findings)} finding(s)"]
        for f in self.findings:
            loc = f" (line {f.line})" if f.line is not None else ""
            exc = f" | {f.excerpt!r}" if f.excerpt else ""
            lines.append(f"  [{f.severity.value}] {f.category}{loc}: {f.description}{exc}")
        return "\n".join(lines)


# ── Compiled pattern library ───────────────────────────────────────────────────

# CRITICAL — explicit instruction-override language
_INSTRUCTION_OVERRIDE = re.compile(
    r"""
    \b ignore \s+ (all \s+)? (the \s+)? (previous|prior|above|earlier|existing|your) \s+ instructions? \b  |
    \b disregard \s+ (all \s+)? (the \s+)? (previous|prior|above|your) \s+ instructions? \b                |
    \b forget \s+ (all \s+)? (the \s+)? (previous|prior|above|your) \s+ instructions? \b                   |
    \b override \s+ (all \s+)? (the \s+)? (previous|prior|above|your) \s+ instructions? \b                 |
    \b new \s+ instructions? \s* :                                                               |
    \b updated? \s+ instructions? \s* :                                                          |
    \b instead \s+ of \s+ (following|using) \s+ (the \s+)? instructions? \b                    |
    \b from \s+ now \s+ on \s+ (you \s+)? (are|must|should|will) \s+                           |
    \b supersed (e|ing) \s+ (all \s+)? instructions? \b
    """,
    re.IGNORECASE | re.VERBOSE,
)

# CRITICAL — role / identity hijacking
_ROLE_HIJACK = re.compile(
    r"""
    \b you \s+ are \s+ now \s+ (a \s+ | an \s+)?     |
    \b act \s+ as \s+ (a \s+ | an \s+)?              |
    \b pretend \s+ (to \s+ be | you \s+ are) \b      |
    \b roleplay \s+ as \b                             |
    \b simulate \s+ (being|a|an) \b                  |
    \b your \s+ true \s+ (self|nature|purpose) \b    |
    \b DAN \b (?:\s+ (mode|activated|enabled))?      |
    \b jailbreak \b
    """,
    re.IGNORECASE | re.VERBOSE,
)

# HIGH — prompt delimiter injection (structural attacks targeting LLM context parsers)
_DELIMITER_INJECTION = re.compile(
    r"""
    </? \s* (system|human|assistant|user|prompt|context|instruction) \s* >  |
    \[SYSTEM\]                                                               |
    \[INST\]  |  \[\/INST\]                                                 |
    <<SYS>>   |  <</SYS>>                                                   |
    <\|im_start\|>  |  <\|im_end\|>                                         |
    <\|endoftext\|> |  <\|eot_id\|>                                         |
    (?<!\w) (Human|Assistant|System) \s* : \s* \n                           |
    \#{3,} \s* (SYSTEM|HUMAN|ASSISTANT|PROMPT) \s* \#* \s* \n
    """,
    re.IGNORECASE | re.VERBOSE,
)

# CRITICAL — credential / data exfiltration patterns
_EXFILTRATION = re.compile(
    r"""
    \b exfiltrat (e|ing|ion) \b                                   |
    \b send \s+ (the \s+)? (api[\s_-]?key|token|secret|password|credential) \b  |
    \b POST \s+ (to|the) \s+ https?://                            |
    webhook[\s.]site                                               |
    requestbin\.                                                   |
    burpcollaborator                                               |
    interact\.sh                                                   |
    ngrok\.io                                                      |
    pipedream\.net                                                 |
    canarytokens\.                                                 |
    \b leak \s+ (the \s+)? (api[\s_-]?key|token|secret|credential) \b
    """,
    re.IGNORECASE | re.VERBOSE,
)

# MEDIUM/HIGH — HTML / script injection
_HTML_INJECTION = re.compile(
    r"""
    <script\b                             |
    javascript \s* :                      |
    data \s* : \s* text/html             |
    < \s* iframe \b                       |
    < \s* img \b [^>]* \b onerror \b     |
    < \s* svg \b [^>]* \b onload \b      |
    vbscript \s* :
    """,
    re.IGNORECASE | re.VERBOSE,
)

# HIGH — Unicode BiDi + zero-width characters (can hide injected content visually)
# Using explicit Unicode escapes to avoid encoding issues in source files.
#
# BiDi override / embedding / isolate chars: U+202A–U+202E and U+2066–U+2069
# Zero-width: U+200B (ZWSP), U+200C (ZWNJ), U+200D (ZWJ),
#             U+200E (LRM), U+200F (RLM), U+00AD (soft hyphen), U+FEFF (BOM)
# Null byte: U+0000 — checked in _scan_unicode via ord()
_UNICODE_ATTACK = re.compile(
    "[‪-‮⁦-⁩]"    # BiDi override / embedding / isolate
    "|[​-‏­﻿]"    # Zero-width / soft-hyphen / BOM
    # (null byte U+0000 checked separately in _scan_unicode via ord())
)

# MEDIUM — excessive blank lines (content displacement / off-screen hiding)
_BLANK_LINE_FLOOD = re.compile(r"(\n[ \t]*){20,}")

# LOW-MEDIUM — long base64-ish chunks (possible encoded hidden payload)
# Threshold 48+ chars covers payloads like "ignore all previous instructions" (60 chars encoded)
_BASE64_CHUNK = re.compile(r"[A-Za-z0-9+/]{48,}={0,2}")

# Thresholds
_LONG_LINE_CHARS = 2000     # chars per line before flagging as suspicious

# Fenced code block pattern — triple backticks or triple tildes
_CODE_BLOCK = re.compile(r"```[\s\S]*?```|~~~[\s\S]*?~~~", re.MULTILINE)

# Inline code pattern — single backticks (for short code spans)
_INLINE_CODE = re.compile(r"`[^`\n]+`")


# ── Helper utilities ───────────────────────────────────────────────────────────

def _safe_excerpt(text: str, start: int, length: int = 60) -> str:
    """Return a short, printable-ASCII excerpt; strips control/non-ASCII chars."""
    raw = text[max(0, start - 5) : start + length]
    return "".join(c if c.isprintable() and ord(c) < 128 else "?" for c in raw)[:80]


def _strip_code_blocks(text: str) -> str:
    """Replace fenced code blocks and inline code with whitespace placeholders.

    Code examples are trusted content — they often contain patterns (TypeScript
    generics, <script> tags, HTML) that would otherwise trigger the scanner.
    Replacing with whitespace preserves line numbers for non-code findings.
    """
    def blank_out(m: re.Match) -> str:
        # Replace with same number of lines to preserve line numbers
        content = m.group(0)
        newlines = content.count("\n")
        return "\n" * newlines + " "

    result = _CODE_BLOCK.sub(blank_out, text)
    result = _INLINE_CODE.sub(lambda m: " " * len(m.group(0)), result)
    return result


def _lineno(text: str, pos: int) -> int:
    return text[:pos].count("\n") + 1


def _scan_unicode(text: str, field_name: str) -> list[Finding]:
    findings: list[Finding] = []

    # Regex scan for BiDi overrides and zero-width chars
    for m in _UNICODE_ATTACK.finditer(text):
        char = text[m.start()]
        try:
            char_name = unicodedata.name(char, "UNKNOWN")
        except Exception:
            char_name = "UNKNOWN"
        findings.append(Finding(
            severity=Severity.HIGH,
            category="unicode-attack",
            description=(
                f"Dangerous Unicode U+{ord(char):04X} ({char_name}) in {field_name}"
            ),
            excerpt=_safe_excerpt(text, m.start()),
            line=_lineno(text, m.start()),
        ))

    # Explicit null byte check (U+0000) — cannot use literal in regex source
    for i, char in enumerate(text):
        if ord(char) == 0:
            findings.append(Finding(
                severity=Severity.HIGH,
                category="unicode-attack",
                description=f"Null byte (U+0000) in {field_name}",
                excerpt=_safe_excerpt(text, i),
                line=_lineno(text, i),
            ))
    return findings


def _scan_base64_payloads(text: str) -> list[Finding]:
    findings: list[Finding] = []
    for m in _BASE64_CHUNK.finditer(text):
        chunk = m.group()
        try:
            # Pad and decode; check if decoded content contains injection patterns
            padded = chunk + "=" * (-len(chunk) % 4)
            decoded = base64.b64decode(padded).decode("utf-8", errors="ignore")
            if _INSTRUCTION_OVERRIDE.search(decoded) or _ROLE_HIJACK.search(decoded):
                findings.append(Finding(
                    severity=Severity.CRITICAL,
                    category="base64-injection",
                    description="Base64 chunk decodes to instruction-override content",
                    excerpt=_safe_excerpt(chunk, 0, 40),
                    line=None,
                ))
            elif _EXFILTRATION.search(decoded):
                findings.append(Finding(
                    severity=Severity.HIGH,
                    category="base64-injection",
                    description="Base64 chunk decodes to exfiltration pattern",
                    excerpt=_safe_excerpt(chunk, 0, 40),
                    line=None,
                ))
        except Exception:
            pass  # Not valid base64 — not inherently suspicious
    return findings


# ── Public API ─────────────────────────────────────────────────────────────────

def scan_skill(
    skill_id: str,
    description: str,
    body: str,
    triggers: Sequence[str],
    name: str = "",
) -> ScanResult:
    """
    Scan all text fields of a parsed skill for prompt-injection patterns.

    Scans: name, description, triggers, and the full body markdown.

    The body is the highest-risk field — it is loaded directly into the agent
    context window when skills_get_body() is called. The other fields flow
    into the embedding and search result display.

    Returns a ScanResult. Check result.blocked before ingesting.
    """
    result = ScanResult(skill_id=skill_id)

    # Map each field to a name and whether it's the high-risk body field
    fields: dict[str, tuple[str, bool]] = {
        name:        ("name", False),
        description: ("description", False),
        body:        ("body", True),
        **{t: (f"trigger[{i}]", False) for i, t in enumerate(triggers)},
    }

    for text, (field_name, is_body) in fields.items():
        if not text:
            continue

        # For structural HTML/delimiter patterns, strip fenced code blocks first.
        # Code examples legitimately contain <script>, TypeScript generics like
        # Promise<User>, HTML tags, etc. — these should not trigger the scanner.
        # Instruction overrides and exfiltration patterns are checked in full text
        # because those should never appear even in code comments.
        text_no_code = _strip_code_blocks(text) if is_body else text

        # ── 1. Instruction overrides — scan FULL text (incl. code) ───────────
        for m in _INSTRUCTION_OVERRIDE.finditer(text):
            result.findings.append(Finding(
                severity=Severity.CRITICAL,
                category="instruction-override",
                description=f"Instruction-override phrase detected in {field_name}",
                excerpt=_safe_excerpt(text, m.start()),
                line=_lineno(text, m.start()),
            ))

        # ── 2. Role hijacking — scan FULL text ───────────────────────────────
        for m in _ROLE_HIJACK.finditer(text):
            result.findings.append(Finding(
                severity=Severity.CRITICAL if is_body else Severity.HIGH,
                category="role-hijack",
                description=f"Role/identity hijacking phrase detected in {field_name}",
                excerpt=_safe_excerpt(text, m.start()),
                line=_lineno(text, m.start()),
            ))

        # ── 3. Delimiter injection — scan CODE-STRIPPED text ─────────────────
        # TypeScript generics (<User>, <Promise<T>>) would otherwise false-positive
        for m in _DELIMITER_INJECTION.finditer(text_no_code):
            result.findings.append(Finding(
                severity=Severity.HIGH,
                category="delimiter-injection",
                description=f"Prompt delimiter injection pattern in {field_name}",
                excerpt=_safe_excerpt(text, m.start()),
                line=_lineno(text, m.start()),
            ))

        # ── 4. Exfiltration ───────────────────────────────────────────────────
        for m in _EXFILTRATION.finditer(text):
            result.findings.append(Finding(
                severity=Severity.CRITICAL,
                category="exfiltration",
                description=f"Credential/data exfiltration pattern in {field_name}",
                excerpt=_safe_excerpt(text, m.start()),
                line=_lineno(text, m.start()),
            ))

        # ── 5. HTML / script injection — scan CODE-STRIPPED text ─────────────
        # <script> tags in code block examples (e.g., web-artifacts-builder skill)
        # are legitimate and must not be flagged. Only non-code prose is scanned.
        for m in _HTML_INJECTION.finditer(text_no_code):
            result.findings.append(Finding(
                severity=Severity.HIGH if is_body else Severity.MEDIUM,
                category="html-injection",
                description=f"HTML/script injection pattern in {field_name}",
                excerpt=_safe_excerpt(text, m.start()),
                line=_lineno(text, m.start()),
            ))

        # ── 6. Unicode attacks ────────────────────────────────────────────────
        result.findings.extend(_scan_unicode(text, field_name))

        # ── 7. Base64 encoded payloads (body only) ────────────────────────────
        if is_body:
            result.findings.extend(_scan_base64_payloads(text))

        # ── 8. Content displacement ───────────────────────────────────────────
        if is_body:
            for m in _BLANK_LINE_FLOOD.finditer(text):
                result.findings.append(Finding(
                    severity=Severity.MEDIUM,
                    category="content-displacement",
                    description="≥20 consecutive blank lines — possible content displacement attack",
                    line=_lineno(text, m.start()),
                ))

        # ── 9. Suspiciously long lines ────────────────────────────────────────
        for i, line in enumerate(text.splitlines(), 1):
            if len(line) > _LONG_LINE_CHARS:
                result.findings.append(Finding(
                    severity=Severity.MEDIUM,
                    category="long-line",
                    description=(
                        f"Line {i} in {field_name} is {len(line)} chars "
                        f"(>{_LONG_LINE_CHARS}) — possible encoded payload"
                    ),
                    line=i,
                ))

    return result


def scan_skill_file(path: Path) -> ScanResult:
    """Convenience wrapper: parse a SKILL.md file and scan it."""
    try:
        import frontmatter
        post = frontmatter.load(str(path))
        fm = dict(post.metadata)
        body = post.content.strip()
    except ImportError:
        import yaml
        text = path.read_text(encoding="utf-8")
        parts = text.split("---", 2)
        if len(parts) < 3:
            result = ScanResult(skill_id=path.parent.name)
            result.findings.append(Finding(
                severity=Severity.HIGH,
                category="parse-error",
                description="Could not find YAML frontmatter delimiters",
            ))
            return result
        fm = yaml.safe_load(parts[1]) or {}
        body = parts[2].strip()

    meta = fm.get("metadata") or {}
    return scan_skill(
        skill_id=path.parent.name,
        name=str(fm.get("name") or ""),
        description=str(fm.get("description") or ""),
        body=body,
        triggers=list(meta.get("triggers") or []),
    )


# ── CLI ────────────────────────────────────────────────────────────────────────

def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Scan a SKILL.md file for prompt-injection patterns"
    )
    parser.add_argument("path", type=Path, help="Path to a SKILL.md file")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 on MEDIUM findings too (CI strict mode)",
    )
    args = parser.parse_args()

    if not args.path.exists():
        print(f"[scan] ERROR: file not found: {args.path}", file=sys.stderr)
        sys.exit(2)

    result = scan_skill_file(args.path)
    print(result.summary())

    if result.blocked:
        sys.exit(1)
    if args.strict and result.warnings:
        sys.exit(1)


if __name__ == "__main__":
    _cli()
