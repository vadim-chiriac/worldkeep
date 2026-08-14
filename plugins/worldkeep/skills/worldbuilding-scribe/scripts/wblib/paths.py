"""Locate the canonical tools and references relative to where wb is installed.

``wb`` ships inside both skill bundles from one canonical source, and it must
find `apply.py`, `validate.py`, the viewer, and the reference documents without
depending on the caller's working directory. Three layouts are supported:

* the source tree, where wb lives at ``src/wb/``;
* the ``worldbuilding-scribe`` bundle, where the viewer is a sibling skill; and
* the ``canon-viewer`` bundle, where the scribe scripts are a sibling skill.

Every lookup is a probe of known relative locations. Nothing is searched for,
and a missing tool is reported rather than guessed at.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent.parent

#: Bumped when the JSON documents wb emits change shape.
TOOL_VERSION = "0.2"


def _ensure_vendored_yaml() -> None:
    """Make the bundled PyYAML importable, exactly as the other entrypoints do."""
    candidates = (
        # Installed bundle: _vendor sits beside wb.py in either skill.
        SCRIPT_DIR / "_vendor",
        # Source tree: src/wb -> repository root -> the one vendored copy.
        SCRIPT_DIR.parents[1] / "src" / "runtime" / "_vendor",
        # Installed bundle with only the sibling skill carrying _vendor.
        SCRIPT_DIR.parent.parent / "worldbuilding-scribe" / "scripts" / "_vendor",
    )
    for candidate in candidates:
        if candidate.is_dir():
            sys.path.insert(0, str(candidate))
            return


_ensure_vendored_yaml()


class ToolPaths:
    """Resolved locations of everything wb delegates to or reads."""

    def __init__(self, script_dir: Path | None = None) -> None:
        self.script_dir = Path(script_dir).resolve() if script_dir else SCRIPT_DIR
        self._cache: dict[str, Path | None] = {}

    # -- candidate tables -------------------------------------------------
    def _candidates(self, name: str) -> tuple[Path, ...]:
        here = self.script_dir
        # Source tree: src/wb -> repository root.
        root = here.parent.parent
        # Installed bundle: skills/<skill>/scripts -> skills/
        skills = here.parent.parent

        table: dict[str, tuple[Path, ...]] = {
            "apply": (
                here / "apply.py",
                root / "src" / "skills" / "worldbuilding-scribe" / "scripts" / "apply.py",
                skills / "worldbuilding-scribe" / "scripts" / "apply.py",
            ),
            "validate": (
                here / "validate.py",
                root / "src" / "skills" / "worldbuilding-scribe" / "scripts" / "validate.py",
                skills / "worldbuilding-scribe" / "scripts" / "validate.py",
            ),
            "view": (
                here / "view.py",
                root / "src" / "viewer" / "view.py",
                skills / "canon-viewer" / "scripts" / "view.py",
            ),
            "kernel": (
                here.parent / "references" / "KERNEL.md",
                root / "Specification" / "KERNEL.md",
                skills / "worldbuilding-scribe" / "references" / "KERNEL.md",
            ),
            "scribe": (
                here.parent / "references" / "SCRIBE.md",
                root / "Specification" / "SCRIBE.md",
                skills / "worldbuilding-scribe" / "references" / "SCRIBE.md",
            ),
            "seed_world": (
                here.parent / "assets" / "seed-world",
                root / "src" / "skills" / "worldbuilding-scribe" / "assets" / "seed-world",
                skills / "worldbuilding-scribe" / "assets" / "seed-world",
            ),
            "views_library": (
                here.parent / "assets" / "views-library",
                root / "src" / "skills" / "canon-viewer" / "assets" / "views-library",
                skills / "canon-viewer" / "assets" / "views-library",
            ),
        }
        return table.get(name, ())

    def find(self, name: str) -> Path | None:
        """Return the first existing candidate for one tool or reference."""
        if name in self._cache:
            return self._cache[name]
        resolved: Path | None = None
        for candidate in self._candidates(name):
            if candidate.exists():
                resolved = candidate.resolve()
                break
        self._cache[name] = resolved
        return resolved

    def require(self, name: str) -> Path:
        found = self.find(name)
        if found is None:
            raise ToolNotFound(
                f"cannot find '{name}' relative to {self.script_dir}; "
                "run 'wb doctor' for details"
            )
        return found

    def describe(self) -> dict[str, str | None]:
        """Return every known location, for doctor and diagnostics."""
        return {
            name: (str(self.find(name)) if self.find(name) else None)
            for name in (
                "apply",
                "validate",
                "view",
                "kernel",
                "scribe",
                "seed_world",
                "views_library",
            )
        }


class ToolNotFound(RuntimeError):
    """A packaged tool wb depends on is not present beside this installation."""


def parse_document_version(path: Path | None) -> str:
    """Return the version in a reference document's first heading.

    Mirrors the build's own heading parser; a sync test pins the two together
    so this never drifts from the packaging view of the same files.
    """
    if path is None or not path.is_file():
        return "unknown"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return "unknown"
    first_line = text.splitlines()[0] if text else ""
    import re

    match = re.search(r"\(v[0-9][^)]*\)", first_line)
    if match:
        return match.group(0).strip("()")
    match = re.search(r"v[0-9][\w.]*", first_line)
    return match.group(0) if match else "unknown"


def import_apply(paths: ToolPaths):
    """Import the canonical apply.py as a module, without running its CLI.

    apply.py is plain module-level definitions plus a ``main()`` that is only
    called under ``__main__``, so importing it is safe and avoids duplicating
    the loader, index, and search behaviour it already owns.
    """
    import importlib.util

    apply_path = paths.require("apply")
    spec = importlib.util.spec_from_file_location("wb_vendored_apply", apply_path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ToolNotFound(f"cannot load {apply_path}")
    module = importlib.util.module_from_spec(spec)
    saved_argv = sys.argv
    sys.argv = [str(apply_path)]
    try:
        spec.loader.exec_module(module)
    finally:
        sys.argv = saved_argv
    return module


def relative_to_cwd(path: Path) -> str:
    """Render a path relative to the working directory when that is shorter."""
    try:
        relative = os.path.relpath(path, Path.cwd())
    except (OSError, ValueError):
        return str(path)
    return relative if len(relative) < len(str(path)) else str(path)
