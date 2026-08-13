"""Run the existing tools without reimplementing or reinterpreting them.

Every mutation still goes through `apply.py`, every check through
`validate.py`, and every projection through `view.py`. wb adds argument
assembly and path resolution; it never parses canon, applies a change, or
decides what is valid. Child output and exit codes are preserved as-is so a
caller sees exactly what the underlying tool said.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from .paths import ToolPaths


RESULT_SCHEMA = "wb.result/v1"


@dataclass
class ToolResult:
    tool: str
    argv: list[str]
    returncode: int
    stdout: str = ""
    stderr: str = ""

    def as_json(self) -> dict[str, Any]:
        return {
            "schema": RESULT_SCHEMA,
            "tool": self.tool,
            "command": self.argv,
            "exit_code": self.returncode,
            "ok": self.returncode == 0,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


def run_tool(
    paths: ToolPaths,
    tool: str,
    arguments: Sequence[str],
    *,
    stdin_text: str | None = None,
    capture: bool = False,
) -> ToolResult:
    """Invoke one packaged tool with the interpreter already running wb."""
    script = paths.require(tool)
    argv = [sys.executable, str(script), *arguments]

    if capture:
        completed = subprocess.run(
            argv,
            input=stdin_text,
            capture_output=True,
            text=True,
            check=False,
        )
        return ToolResult(
            tool=tool,
            argv=[str(script), *arguments],
            returncode=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
        )

    completed = subprocess.run(argv, input=stdin_text, text=True, check=False)
    return ToolResult(
        tool=tool, argv=[str(script), *arguments], returncode=completed.returncode
    )


def read_input(input_file: Path | None) -> str:
    """Read capture JSON from a file or from stdin, whichever was supplied."""
    if input_file is not None:
        return Path(input_file).expanduser().read_text(encoding="utf-8")
    if sys.stdin is None or sys.stdin.isatty():
        raise ValueError(
            "no input: pipe artifact JSON on stdin or pass --input-file"
        )
    return sys.stdin.read()


def check_capture_payload(raw: str) -> tuple[bool, str]:
    """Fail fast on input apply.py would reject, before touching the canon."""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return False, f"input is not valid JSON: {exc}"
    if not isinstance(parsed, list):
        return False, "input must be a JSON array of artifact objects"
    if not parsed:
        return False, "input contains no artifacts"
    for position, item in enumerate(parsed, start=1):
        if not isinstance(item, dict):
            return False, f"item {position} is not an object"
        if not item.get("id"):
            return False, f"item {position} is missing 'id'"
        if not item.get("kind"):
            return False, f"item {position} ({item.get('id')}) is missing 'kind'"
    return True, f"{len(parsed)} artifact(s)"
