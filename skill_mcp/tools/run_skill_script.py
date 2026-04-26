"""MCP tool: skills_run_script — execute a script bundled with a skill.

Scripts live in the skill's scripts/ subdirectory. This tool mirrors exactly how
bash script execution works in local Agent Skills: the script source NEVER enters
the context window — only stdout/stderr output is returned.

Security model (enforced):
  - Scripts execute in an isolated temporary directory
  - 30-second hard timeout
  - Minimal environment (no credentials, no PATH outside system executables)
  - Script source is never returned in any response field
  - No network access restrictions enforced at OS level (depend on host policy)

Two modes:
  1. List mode (list_only=True or filename="list"): returns script manifest.
  2. Execute mode: runs the script, returns stdout/stderr/exit_code only.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from typing import Any, Optional

from ..db.cache import TTLCache
from ..db.qdrant_manager import qdrant_manager

_script_list_cache: TTLCache = TTLCache(
    ttl=float(os.getenv("CACHE_TTL_SECONDS", "300")),
    max_size=int(os.getenv("CACHE_MAX_SIZE", "1000")),
)

_SCRIPT_TIMEOUT = int(os.getenv("SCRIPT_TIMEOUT_SECONDS", "30"))
_MAX_OUTPUT_CHARS = 10_000


def run_skill_script(
    skill_id: str,
    filename: str = "list",
    input_data: Optional[dict[str, Any]] = None,
    list_only: bool = False,
) -> str:
    """Execute a script bundled with a skill and return its output.

    The script source is never returned — only execution output (stdout, stderr,
    exit_code). This mirrors bash script execution in local Agent Skills exactly.

    Args:
        skill_id:   The skill_id returned by skills_find_relevant.
        filename:   The script filename to execute (e.g. "extract.py", "validate.js").
                    Pass "list" or set list_only=True to see available scripts.
        input_data: Optional dict of key=value pairs passed to the script as
                    environment variables. Values are stringified.
        list_only:  If True, return the script manifest without executing.

    Returns:
        JSON string.
        - List mode: {"skill_id": ..., "scripts": [{filename, language, description}, ...]}
        - Execute mode: {"skill_id": ..., "filename": ..., "language": ...,
                         "exit_code": int, "stdout": str, "stderr": str, "truncated": bool}
        - Error: {"error": "..."}

    Security note:
        Script source is intentionally excluded from all response fields.
        The source is retrieved internally for execution only and discarded after.
    """
    # ── List mode ─────────────────────────────────────────────────────────────

    if list_only or filename in ("list", "", "all"):
        cache_key = f"script_list|{skill_id}"
        cached = _script_list_cache.get(cache_key)
        if cached is not None:
            return cached

        payloads = qdrant_manager.get_scripts_for_skill(skill_id)
        scripts = [
            {
                "filename": p.get("filename", ""),
                "language": p.get("language", "unknown"),
                "description": p.get("description", ""),
                "file_path": p.get("file_path", ""),
                "dependencies": p.get("dependencies", []),
                # source intentionally omitted
            }
            for p in payloads
        ]
        scripts.sort(key=lambda s: s["filename"])

        result = json.dumps(
            {
                "skill_id": skill_id,
                "total": len(scripts),
                "scripts": scripts,
                "note": (
                    "Call skills_run_script(skill_id, filename='<name>', input_data={...}) "
                    "to execute a script. Output only is returned — source is never exposed."
                ),
            },
            indent=2,
        )
        _script_list_cache.set(cache_key, result)
        return result

    # ── Execute mode ──────────────────────────────────────────────────────────

    payload = qdrant_manager.get_script(skill_id, filename)
    if payload is None:
        all_scripts = qdrant_manager.get_scripts_for_skill(skill_id)
        all_names = [p.get("filename", "") for p in all_scripts]
        # Case-insensitive fallback
        match = next(
            (f for f in all_names if f.lower() == filename.lower()), None
        )
        if match and match != filename:
            payload = qdrant_manager.get_script(skill_id, match)
        if payload is None:
            return json.dumps(
                {
                    "error": (
                        f"Script '{filename}' not found for skill '{skill_id}'. "
                        f"Call skills_run_script(skill_id='{skill_id}', list_only=True) "
                        f"to see available scripts."
                    ),
                    "available": all_names,
                }
            )

    source: str = payload.get("source", "")
    language: str = payload.get("language", "unknown")
    script_filename: str = payload.get("filename", filename)

    if not source.strip():
        return json.dumps(
            {"error": f"Script '{script_filename}' has no source content stored."}
        )

    # Execute in isolated temp directory
    exec_result = _execute_script(
        source=source,
        language=language,
        script_filename=script_filename,
        input_data=input_data or {},
        timeout=_SCRIPT_TIMEOUT,
    )

    return json.dumps(
        {
            "skill_id": skill_id,
            "filename": script_filename,
            "language": language,
            "exit_code": exec_result["exit_code"],
            "stdout": exec_result["stdout"],
            "stderr": exec_result["stderr"],
            "truncated": exec_result["truncated"],
            # source intentionally excluded
        },
        indent=2,
    )


def _execute_script(
    source: str,
    language: str,
    script_filename: str,
    input_data: dict[str, Any],
    timeout: int,
) -> dict[str, Any]:
    """Execute a script in an isolated temp directory. Returns output dict."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Write script to temp file
        ext_map = {
            "python": ".py",
            "javascript": ".js",
            "typescript": ".ts",
            "bash": ".sh",
        }
        ext = ext_map.get(language, os.path.splitext(script_filename)[1] or ".py")
        script_path = os.path.join(tmpdir, f"skill_script{ext}")

        with open(script_path, "w", encoding="utf-8") as f:
            f.write(source)

        # Minimal environment — no credentials, no sensitive vars
        clean_env: dict[str, str] = {}
        if sys.platform == "win32":
            # Windows requires SystemRoot and PATHEXT at minimum
            clean_env["SystemRoot"] = os.environ.get("SystemRoot", "C:\\Windows")
            clean_env["PATHEXT"] = os.environ.get("PATHEXT", ".EXE;.CMD;.BAT")
            clean_env["PATH"] = os.environ.get("PATH", "")
        else:
            clean_env["PATH"] = "/usr/local/bin:/usr/bin:/bin"
            clean_env["HOME"] = tmpdir
            clean_env["TMPDIR"] = tmpdir

        # Keys that scripts must not be allowed to override — doing so would let
        # a malicious skill redirect binary execution or inject shared libraries.
        _BLOCKED_ENV_KEYS = frozenset({
            "PATH", "LD_PRELOAD", "LD_LIBRARY_PATH", "LD_AUDIT",
            "DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH",
            "PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP",
            "HOME", "TMPDIR", "TEMP", "TMP",
            "IFS", "BASH_ENV", "ENV", "PS1", "PS2",
            "SystemRoot", "PATHEXT", "COMSPEC",
        })

        # Pass input_data as environment variables (all values stringified).
        # Silently skip any key that would override a protected variable.
        for k, v in input_data.items():
            key = str(k)
            if key.upper() not in {b.upper() for b in _BLOCKED_ENV_KEYS}:
                clean_env[key] = str(v)

        # Build command
        cmd_map = {
            "python": [sys.executable, script_path],
            "javascript": ["node", script_path],
            "typescript": ["npx", "ts-node", script_path],
            "bash": ["bash", script_path],
        }
        cmd = cmd_map.get(language, [sys.executable, script_path])

        # Use Popen + communicate so we can explicitly kill on timeout.
        # subprocess.run(timeout=…) raises TimeoutExpired but does NOT kill
        # the child process — the caller is responsible for cleanup.
        try:
            with subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=tmpdir,
                env=clean_env,
            ) as proc:
                try:
                    stdout, stderr = proc.communicate(timeout=timeout)
                    exit_code = proc.returncode
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.communicate()  # drain pipes so the process exits cleanly
                    stdout = ""
                    stderr = (
                        f"Script timed out after {timeout} seconds. "
                        "Increase SCRIPT_TIMEOUT_SECONDS env var or optimize the script."
                    )
                    exit_code = -1

        except FileNotFoundError as e:
            stdout = ""
            stderr = (
                f"Runtime not found for language '{language}': {e}. "
                "Ensure the required interpreter is installed on the server."
            )
            exit_code = -2

        # Truncate oversized output; flag is set when either stream is truncated.
        truncated = False
        if len(stdout) > _MAX_OUTPUT_CHARS:
            stdout = stdout[:_MAX_OUTPUT_CHARS] + "\n[...output truncated at 10,000 chars]"
            truncated = True
        if len(stderr) > _MAX_OUTPUT_CHARS:
            stderr = stderr[:_MAX_OUTPUT_CHARS] + "\n[...stderr truncated]"
            truncated = True

        return {
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "truncated": truncated,
        }
