"""
Python AST static analysis — bundled with the code-review skill.

Performs fast, zero-dependency static analysis using Python's built-in ast module.
Returns structured JSON with severity-tagged issues.

Input (environment variables):
  CODE      — Python source code to analyze (required)
  FILENAME  — filename hint for error messages (default: "code.py")
  SEVERITY  — minimum severity to report: CRITICAL|HIGH|MEDIUM|LOW|INFO (default: LOW)

Output (stdout): JSON with found issues and summary
"""

import ast
import json
import os
import re
import sys

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}


def main() -> None:
    code = os.environ.get("CODE", "")
    filename = os.environ.get("FILENAME", "code.py")
    min_severity = os.environ.get("SEVERITY", "LOW").upper()

    if not code:
        print(json.dumps({
            "error": "CODE environment variable is required",
            "usage": 'CODE="$(cat myfile.py)" python lint_check.py',
        }))
        sys.exit(1)

    # Parse
    try:
        tree = ast.parse(code, filename=filename)
    except SyntaxError as e:
        print(json.dumps({
            "valid": False,
            "filename": filename,
            "syntax_error": {"line": e.lineno, "col": e.offset, "message": str(e)},
            "issues": [],
            "summary": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0},
        }, indent=2))
        return

    issues = []
    _walk_ast(tree, code, issues)
    _check_line_lengths(code, issues)

    # Filter by minimum severity
    min_level = SEVERITY_ORDER.get(min_severity, 3)
    issues = [i for i in issues if SEVERITY_ORDER.get(i["severity"], 99) <= min_level]
    issues.sort(key=lambda i: (SEVERITY_ORDER.get(i["severity"], 99), i["line"]))

    summary = {sev: sum(1 for i in issues if i["severity"] == sev)
               for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO")}

    print(json.dumps({
        "valid": True,
        "filename": filename,
        "total_issues": len(issues),
        "issues": issues,
        "summary": summary,
    }, indent=2))


def _walk_ast(tree: ast.AST, code: str, issues: list) -> None:
    lines = code.splitlines()

    for node in ast.walk(tree):

        # ── Dangerous builtins ──────────────────────────────────────────────
        if isinstance(node, ast.Call):
            func_name = None
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr

            if func_name in ("eval", "exec"):
                issues.append({
                    "line": node.lineno,
                    "severity": "HIGH",
                    "category": "security",
                    "rule": "dangerous-builtin",
                    "message": (
                        f"Use of {func_name}() is dangerous if called with untrusted "
                        f"input (CWE-78 / CWE-94). Consider a safe alternative."
                    ),
                })

            if func_name == "__import__":
                issues.append({
                    "line": node.lineno,
                    "severity": "MEDIUM",
                    "category": "security",
                    "rule": "dynamic-import",
                    "message": "__import__() with dynamic arguments can be abused for code injection.",
                })

        # ── Hardcoded secrets (basic pattern match) ─────────────────────────
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    name_lower = target.id.lower()
                    secret_keywords = (
                        "password", "passwd", "secret", "api_key", "apikey",
                        "token", "auth_token", "access_key", "private_key",
                    )
                    if any(kw in name_lower for kw in secret_keywords):
                        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                            val = node.value.value
                            if len(val) > 4 and val not in ("", "changeme", "your_key_here"):
                                issues.append({
                                    "line": node.lineno,
                                    "severity": "CRITICAL",
                                    "category": "security",
                                    "rule": "hardcoded-secret",
                                    "message": (
                                        f"Possible hardcoded secret in variable '{target.id}'. "
                                        f"Use environment variables instead."
                                    ),
                                })

        # ── Bare except ─────────────────────────────────────────────────────
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            issues.append({
                "line": node.lineno,
                "severity": "MEDIUM",
                "category": "error-handling",
                "rule": "bare-except",
                "message": (
                    "Bare 'except:' catches SystemExit and KeyboardInterrupt. "
                    "Specify at least 'except Exception:' or narrower types."
                ),
            })

        # ── Mutable default arguments ────────────────────────────────────────
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for default in node.args.defaults:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    kind = type(default).__name__.lower()
                    issues.append({
                        "line": node.lineno,
                        "severity": "MEDIUM",
                        "category": "bug",
                        "rule": "mutable-default-arg",
                        "message": (
                            f"Function '{node.name}' has a mutable default argument ({kind}). "
                            f"Use None and initialize inside the function body instead."
                        ),
                    })

        # ── Assert in production code ────────────────────────────────────────
        if isinstance(node, ast.Assert):
            issues.append({
                "line": node.lineno,
                "severity": "LOW",
                "category": "correctness",
                "rule": "assert-in-production",
                "message": (
                    "assert statements are disabled with python -O. "
                    "Use explicit if-raise for production guards."
                ),
            })

        # ── TODO / FIXME / HACK comments ────────────────────────────────────
        # (these are in the source but ast doesn't give us comments, so check lines)

    # Check source for TODO markers
    for i, line in enumerate(code.splitlines(), 1):
        if re.search(r"\b(TODO|FIXME|HACK|XXX)\b", line, re.IGNORECASE):
            issues.append({
                "line": i,
                "severity": "INFO",
                "category": "maintenance",
                "rule": "todo-comment",
                "message": f"Found marker comment: {line.strip()!r}",
            })


def _check_line_lengths(code: str, issues: list) -> None:
    for i, line in enumerate(code.splitlines(), 1):
        if len(line) > 120:
            issues.append({
                "line": i,
                "severity": "LOW",
                "category": "style",
                "rule": "line-too-long",
                "message": (
                    f"Line is {len(line)} characters. "
                    f"Recommended: ≤88 (Black) or ≤120 (PEP 8 relaxed)."
                ),
            })


if __name__ == "__main__":
    main()
