"""The lens vocabulary exists in two places. This keeps them one place.

KERNEL.md §8 tells a scribe what it may write in a type file; `project.py`
decides what a viewer does with it. Nothing but human memory has been
keeping those two lists equal, and the first live world already produced a
lens the spec licensed and the code ignored.

These tests read the worked example in KERNEL §8 — the fenced block
containing `lens:` — and assert it agrees with the implementation. If you
reformat that block, these fail on purpose: the canonical example is load
bearing and should stay machine-readable.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from viewer.project import BEHAVIORS, LENS_KEYS

KERNEL = Path(__file__).resolve().parents[3] / "Specification" / "KERNEL.md"


def lens_example() -> str:
    """The fenced code block in KERNEL that carries the lens example."""
    if not KERNEL.is_file():  # packaged copies may not ship the spec
        pytest.skip(f"KERNEL.md not present at {KERNEL}")
    blocks = re.findall(r"```[a-z]*\n(.*?)```", KERNEL.read_text(encoding="utf-8"), re.S)
    matching = [b for b in blocks if re.search(r"^lens:\s*$", b, re.M)]
    assert matching, "KERNEL.md has no fenced example containing a `lens:` block"
    return matching[0]


def test_kernel_documents_every_implemented_behavior() -> None:
    block = lens_example()
    documented = re.search(r"^\s+as:\s+\w+\s*#\s*([a-z |]+)$", block, re.M)
    assert documented, "the `as:` line in KERNEL's lens example lost its `# a | b | c` list"
    names = {part.strip() for part in documented.group(1).split("|") if part.strip()}
    assert names == BEHAVIORS, (
        "KERNEL §8 and project.BEHAVIORS disagree.\n"
        f"  only in KERNEL: {sorted(names - BEHAVIORS)}\n"
        f"  only in code:   {sorted(BEHAVIORS - names)}"
    )


def test_kernel_documents_every_implemented_lens_key() -> None:
    block = lens_example()
    body = block.split("lens:", 1)[1]
    keys = set(re.findall(r"^\s{2,}(\w+):", body, re.M))
    unknown = keys - LENS_KEYS
    assert not unknown, f"KERNEL documents lens keys the viewer ignores: {sorted(unknown)}"
    # collapse_default is deferred (v1 collapse work), so it may be undocumented.
    missing = LENS_KEYS - keys - {"collapse_default"}
    assert not missing, f"viewer honours lens keys KERNEL never mentions: {sorted(missing)}"
