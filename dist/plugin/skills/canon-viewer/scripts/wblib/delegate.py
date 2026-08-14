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
CAPTURE_SCHEMA = "wb.capture/v1"


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


@dataclass(frozen=True)
class CaptureBundle:
    """One approval bundle declared alongside a capture batch."""

    id: str
    headline: str
    artifact_ids: tuple[str, ...]


@dataclass(frozen=True)
class CapturePayload:
    """Validated capture input, with the writer-facing array kept separate."""

    artifacts: list[dict[str, Any]]
    bundles: tuple[CaptureBundle, ...] | None

    @property
    def is_bundled(self) -> bool:
        return self.bundles is not None

    def writer_input(self) -> str:
        """The legacy array consumed by apply.py; it never sees wb metadata."""
        return json.dumps(self.artifacts, ensure_ascii=False)


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


def parse_capture_payload(raw: str) -> CapturePayload:
    """Validate legacy arrays and the optional approval-accounting envelope."""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"input is not valid JSON: {exc}") from exc

    bundles: tuple[CaptureBundle, ...] | None = None
    if isinstance(parsed, list):
        artifacts = parsed
    elif isinstance(parsed, dict):
        if parsed.get("schema") != CAPTURE_SCHEMA:
            raise ValueError(
                f"capture envelope requires schema '{CAPTURE_SCHEMA}'"
            )
        artifacts = parsed.get("artifacts")
        raw_bundles = parsed.get("bundles")
        if not isinstance(raw_bundles, list):
            raise ValueError("capture envelope field 'bundles' must be an array")
        if not 2 <= len(raw_bundles) <= 5:
            raise ValueError("capture envelope requires 2 to 5 bundles")
        bundles = _parse_bundles(raw_bundles)
    else:
        raise ValueError(
            "input must be a JSON array of artifact objects or a wb.capture/v1 envelope"
        )

    if not isinstance(artifacts, list):
        raise ValueError("input field 'artifacts' must be a JSON array")
    if not artifacts:
        raise ValueError("input contains no artifacts")
    ids: list[str] = []
    for position, item in enumerate(artifacts, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"item {position} is not an object")
        if not isinstance(item.get("id"), str) or not item["id"]:
            raise ValueError(f"item {position} is missing 'id' (must be a non-empty string)")
        if not item.get("kind"):
            raise ValueError(f"item {position} ({item.get('id')}) is missing 'kind'")
        ids.append(item["id"])

    duplicates = sorted({artifact_id for artifact_id in ids if ids.count(artifact_id) > 1})
    if duplicates:
        raise ValueError("duplicate artifact id(s): " + ", ".join(duplicates))

    if bundles is not None:
        _check_bundle_coverage(ids, bundles)
    return CapturePayload(artifacts=artifacts, bundles=bundles)


def _parse_bundles(raw_bundles: list[Any]) -> tuple[CaptureBundle, ...]:
    bundles: list[CaptureBundle] = []
    seen: set[str] = set()
    for position, raw_bundle in enumerate(raw_bundles, start=1):
        if not isinstance(raw_bundle, dict):
            raise ValueError(f"bundle {position} is not an object")
        bundle_id = raw_bundle.get("id")
        headline = raw_bundle.get("headline")
        artifact_ids = raw_bundle.get("artifact_ids")
        if not isinstance(bundle_id, str) or not bundle_id:
            raise ValueError(f"bundle {position} is missing a non-empty string 'id'")
        if bundle_id in seen:
            raise ValueError(f"duplicate bundle id: {bundle_id}")
        seen.add(bundle_id)
        if not isinstance(headline, str) or not headline:
            raise ValueError(f"bundle {bundle_id} is missing a non-empty string 'headline'")
        if not isinstance(artifact_ids, list) or not artifact_ids:
            raise ValueError(f"bundle {bundle_id} needs a non-empty 'artifact_ids' array")
        if not all(isinstance(artifact_id, str) and artifact_id for artifact_id in artifact_ids):
            raise ValueError(f"bundle {bundle_id} has an invalid artifact id")
        local_duplicates = sorted(
            {artifact_id for artifact_id in artifact_ids if artifact_ids.count(artifact_id) > 1}
        )
        if local_duplicates:
            raise ValueError(
                f"bundle {bundle_id} repeats artifact id(s): " + ", ".join(local_duplicates)
            )
        bundles.append(CaptureBundle(bundle_id, headline, tuple(artifact_ids)))
    return tuple(bundles)


def _check_bundle_coverage(ids: list[str], bundles: tuple[CaptureBundle, ...]) -> None:
    known = set(ids)
    assignments: dict[str, list[str]] = {}
    for bundle in bundles:
        for artifact_id in bundle.artifact_ids:
            assignments.setdefault(artifact_id, []).append(bundle.id)
    unknown = sorted(set(assignments) - known)
    if unknown:
        raise ValueError("bundle references unknown artifact id(s): " + ", ".join(unknown))
    duplicate_assignments = sorted(
        artifact_id for artifact_id, owners in assignments.items() if len(owners) > 1
    )
    if duplicate_assignments:
        raise ValueError(
            "artifact id(s) assigned to more than one bundle: "
            + ", ".join(duplicate_assignments)
        )
    unassigned = sorted(known - set(assignments))
    if unassigned:
        raise ValueError(
            f"bundle membership accounts for {len(assignments)} of {len(known)} artifact(s); "
            f"unassigned: {', '.join(unassigned)}"
        )


def check_capture_payload(raw: str) -> tuple[bool, str]:
    """Compatibility helper for callers that only need a fast yes/no check."""
    try:
        payload = parse_capture_payload(raw)
    except ValueError as exc:
        return False, str(exc)
    return True, f"{len(payload.artifacts)} artifact(s)"
