"""
Python test coverage analyzer — bundled with the test-writer skill.

Uses Python's built-in ast module to statically analyze source and test code.
No test execution required — pure static analysis.

Input (environment variables):
  SOURCE_CODE   — Python source code to analyze (required)
  TEST_CODE     — Python test code to cross-reference (optional)
  FILENAME      — source filename hint (default: "module.py")

Output (stdout): JSON with coverage analysis and recommendations
"""

import ast
import json
import os
import re
import sys
from dataclasses import dataclass, field


@dataclass
class FunctionInfo:
    name: str
    line: int
    is_async: bool
    args: list[str] = field(default_factory=list)
    raises: list[str] = field(default_factory=list)
    has_return: bool = False
    complexity: int = 1  # cyclomatic complexity estimate


def main() -> None:
    source_code = os.environ.get("SOURCE_CODE", "")
    test_code = os.environ.get("TEST_CODE", "")
    filename = os.environ.get("FILENAME", "module.py")

    if not source_code:
        print(json.dumps({
            "error": "SOURCE_CODE environment variable is required",
            "usage": 'SOURCE_CODE="$(cat mymodule.py)" python coverage_check.py',
        }))
        sys.exit(1)

    # Parse source
    try:
        source_tree = ast.parse(source_code, filename=filename)
    except SyntaxError as e:
        print(json.dumps({"error": f"Syntax error in SOURCE_CODE: {e}"}))
        sys.exit(1)

    # Analyze source
    functions = _extract_functions(source_tree)
    classes = _extract_classes(source_tree)
    branches = _count_branches(source_tree)
    exception_types = _extract_raised_exceptions(source_tree)

    # Cross-reference with test code
    tested_names: set[str] = set()
    test_count = 0
    if test_code:
        try:
            test_tree = ast.parse(test_code, filename="test_" + filename)
            tested_names, test_count = _extract_tested_names(test_tree)
        except SyntaxError:
            pass

    # Compute coverage estimates
    public_fns = [f for f in functions if not f.name.startswith("_")]
    tested_fns = [f for f in public_fns if f.name in tested_names]
    untested_fns = [f for f in public_fns if f.name not in tested_names]

    fn_coverage_pct = (
        round(len(tested_fns) / len(public_fns) * 100, 1)
        if public_fns else 100.0
    )

    # Build recommendations
    recommendations = []

    if untested_fns:
        names = ", ".join(f.name for f in untested_fns[:5])
        if len(untested_fns) > 5:
            names += f" (+{len(untested_fns) - 5} more)"
        recommendations.append(f"Add tests for: {names}")

    high_complexity = [f for f in functions if f.complexity >= 3]
    if high_complexity:
        names = ", ".join(f.name for f in high_complexity)
        recommendations.append(
            f"Functions with high branch complexity (≥3 paths) need edge case tests: {names}"
        )

    if exception_types:
        recommendations.append(
            f"Ensure error paths are tested for: {', '.join(exception_types)}"
        )

    if branches > 0 and not test_code:
        recommendations.append(
            f"Found {branches} branch conditions (if/for/while/except). "
            f"Provide TEST_CODE to analyze which branches are covered."
        )

    result = {
        "filename": filename,
        "source_analysis": {
            "total_lines": len(source_code.splitlines()),
            "functions": len(functions),
            "public_functions": len(public_fns),
            "classes": len(classes),
            "branch_conditions": branches,
            "exception_types_raised": exception_types,
            "function_details": [
                {
                    "name": f.name,
                    "line": f.line,
                    "is_async": f.is_async,
                    "args": f.args,
                    "complexity": f.complexity,
                }
                for f in functions
            ],
        },
        "coverage_estimate": {
            "test_functions_found": test_count,
            "public_functions_tested": len(tested_fns),
            "public_functions_untested": len(untested_fns),
            "function_coverage_pct": fn_coverage_pct if test_code else "unknown — provide TEST_CODE",
            "untested_function_names": [f.name for f in untested_fns],
        },
        "recommendations": recommendations,
        "note": "Static analysis only — run 'pytest --cov --cov-report=term-missing' for actual line coverage.",
    }

    print(json.dumps(result, indent=2))


def _extract_functions(tree: ast.AST) -> list[FunctionInfo]:
    functions = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            complexity = 1 + sum(
                1 for child in ast.walk(node)
                if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler,
                                      ast.With, ast.Assert))
            )
            has_return = any(
                isinstance(child, ast.Return) and child.value is not None
                for child in ast.walk(node)
            )
            raises = []
            for child in ast.walk(node):
                if isinstance(child, ast.Raise) and child.exc is not None:
                    if isinstance(child.exc, ast.Call) and isinstance(child.exc.func, ast.Name):
                        raises.append(child.exc.func.id)
                    elif isinstance(child.exc, ast.Name):
                        raises.append(child.exc.id)

            functions.append(FunctionInfo(
                name=node.name,
                line=node.lineno,
                is_async=isinstance(node, ast.AsyncFunctionDef),
                args=[arg.arg for arg in node.args.args],
                raises=raises,
                has_return=has_return,
                complexity=complexity,
            ))
    return functions


def _extract_classes(tree: ast.AST) -> list[dict]:
    return [
        {"name": node.name, "line": node.lineno}
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
    ]


def _count_branches(tree: ast.AST) -> int:
    return sum(
        1 for node in ast.walk(tree)
        if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler))
    )


def _extract_raised_exceptions(tree: ast.AST) -> list[str]:
    seen: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise) and node.exc is not None:
            if isinstance(node.exc, ast.Call) and isinstance(node.exc.func, ast.Name):
                seen.add(node.exc.func.id)
            elif isinstance(node.exc, ast.Name):
                seen.add(node.exc.id)
    return sorted(seen)


def _extract_tested_names(test_tree: ast.AST) -> tuple[set[str], int]:
    """Extract function/attribute names called in the test code."""
    called: set[str] = set()
    test_fn_count = 0

    for node in ast.walk(test_tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            test_fn_count += 1
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called.add(node.func.attr)

    return called, test_fn_count


if __name__ == "__main__":
    main()
