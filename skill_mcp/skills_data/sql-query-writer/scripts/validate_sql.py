"""
SQL syntax validator — bundled with the sql-query-writer skill.

Parses and analyzes SQL for syntax errors and common anti-patterns.
Uses sqlparse for tokenization; falls back to basic checks if not installed.

Input (environment variables):
  SQL      — SQL query to validate (required)
  DIALECT  — target dialect: postgresql | mysql | sqlite (default: postgresql)

Output (stdout): JSON with validation result and detected issues
"""

import json
import os
import re
import sys


def main() -> None:
    sql = os.environ.get("SQL", "").strip()
    dialect = os.environ.get("DIALECT", "postgresql").lower()

    if not sql:
        print(json.dumps({
            "error": "SQL environment variable is required",
            "usage": 'SQL="SELECT * FROM users" python validate_sql.py',
        }))
        sys.exit(1)

    try:
        import sqlparse
        result = validate_with_sqlparse(sql, dialect)
    except ImportError:
        result = validate_basic(sql, dialect)

    print(json.dumps(result, indent=2))


def validate_with_sqlparse(sql: str, dialect: str) -> dict:
    import sqlparse

    issues = []
    parsed_list = sqlparse.parse(sql.strip())

    if not parsed_list:
        return {
            "valid": False,
            "dialect": dialect,
            "issues": [{"severity": "HIGH", "message": "Could not parse SQL"}],
        }

    stmt = parsed_list[0]
    stmt_type = stmt.get_type() or "UNKNOWN"
    sql_upper = sql.upper()

    # ── Pattern checks ──────────────────────────────────────────────────────

    if "SELECT *" in sql_upper:
        issues.append({
            "severity": "LOW",
            "rule": "select-star",
            "message": (
                "SELECT * fetches all columns including hidden/future ones. "
                "List explicit columns for clarity and performance."
            ),
        })

    if stmt_type in ("UPDATE", "DELETE") and "WHERE" not in sql_upper:
        issues.append({
            "severity": "HIGH",
            "rule": "missing-where",
            "message": (
                f"{stmt_type} without WHERE clause will affect ALL rows in the table. "
                f"Add a WHERE clause or use LIMIT 0 to test first."
            ),
        })

    if re.search(r"\bIN\s*\(\s*SELECT\b", sql_upper):
        issues.append({
            "severity": "LOW",
            "rule": "in-subquery",
            "message": (
                "IN (SELECT ...) may perform poorly on large datasets. "
                "Consider rewriting with EXISTS or a JOIN."
            ),
        })

    if re.search(r"\bNOT\s+IN\s*\(\s*SELECT\b", sql_upper):
        issues.append({
            "severity": "MEDIUM",
            "rule": "not-in-subquery",
            "message": (
                "NOT IN (SELECT ...) returns no rows if the subquery contains any NULL. "
                "Use NOT EXISTS instead to avoid this silent bug."
            ),
        })

    # Non-sargable patterns (index bypass)
    non_sargable = [
        (r"\bWHERE\s+\w+\s*\(", "Function call on filtered column disables index use (non-sargable predicate). Move the function to the constant side."),
        (r"\bWHERE\s+\w+\s*\+", "Arithmetic on filtered column may disable index use."),
    ]
    for pattern, msg in non_sargable:
        if re.search(pattern, sql_upper):
            issues.append({"severity": "MEDIUM", "rule": "non-sargable", "message": msg})

    if sql_upper.count("DISTINCT") > 0 and "ORDER BY" not in sql_upper and stmt_type == "SELECT":
        issues.append({
            "severity": "LOW",
            "rule": "distinct-without-order",
            "message": "DISTINCT without ORDER BY produces non-deterministic ordering.",
        })

    paren_balance = sql.count("(") - sql.count(")")
    if paren_balance != 0:
        issues.append({
            "severity": "HIGH",
            "rule": "unbalanced-parens",
            "message": f"Unbalanced parentheses: {abs(paren_balance)} extra {'opening' if paren_balance > 0 else 'closing'} paren(s).",
        })

    # ── Dialect-specific notes ──────────────────────────────────────────────
    dialect_notes = []
    if dialect == "mysql":
        if re.search(r"\bINTERVAL\s+'\d+", sql):
            dialect_notes.append(
                "MySQL INTERVAL syntax: use INTERVAL 7 DAY not INTERVAL '7 days'"
            )
        if "DISTINCT ON" in sql_upper:
            dialect_notes.append(
                "DISTINCT ON is PostgreSQL-only. Use ROW_NUMBER() OVER (...) in MySQL."
            )
    elif dialect == "sqlite":
        if "EXTRACT(" in sql_upper:
            dialect_notes.append(
                "EXTRACT() is not supported in SQLite. Use strftime('%Y', date_col) instead."
            )

    return {
        "valid": len([i for i in issues if i["severity"] == "HIGH"]) == 0,
        "dialect": dialect,
        "statement_type": stmt_type,
        "total_issues": len(issues),
        "issues": issues,
        "dialect_notes": dialect_notes,
        "summary": {
            sev: sum(1 for i in issues if i["severity"] == sev)
            for sev in ("HIGH", "MEDIUM", "LOW", "INFO")
        },
    }


def validate_basic(sql: str, dialect: str) -> dict:
    """Fallback validator without sqlparse."""
    sql_upper = sql.upper().strip()
    issues = []

    if sql.count("(") != sql.count(")"):
        issues.append({"severity": "HIGH", "rule": "unbalanced-parens", "message": "Unbalanced parentheses."})

    keywords = ("SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "WITH", "EXPLAIN")
    if not any(sql_upper.startswith(kw) for kw in keywords):
        issues.append({"severity": "MEDIUM", "rule": "unknown-statement", "message": "Statement doesn't start with a recognized SQL keyword."})

    if "SELECT *" in sql_upper:
        issues.append({"severity": "LOW", "rule": "select-star", "message": "SELECT * — list explicit columns."})

    return {
        "valid": len([i for i in issues if i["severity"] == "HIGH"]) == 0,
        "dialect": dialect,
        "issues": issues,
        "note": "Install sqlparse for deeper analysis: pip install sqlparse",
    }


if __name__ == "__main__":
    main()
