"""Resolve which canon a session is about, without searching the filesystem.

Two shapes are accepted: a canon folder itself, or a bounded root that directly
contains canon folders. The scan never leaves the path it was given, never
recurses arbitrarily deep, and never picks between several worlds on its own.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


WORLD_MANIFEST = "world.yaml"

#: How far below a bounded root a canon folder may sit: children and their
#: children, matching the "look one or two levels down" rule the scribe skill
#: already documents. Anything deeper would be a search of the user's
#: filesystem rather than inspection of a bounded root, so it is not supported.
MAX_DEPTH = 2

#: Directories never treated as candidate worlds or descended into.
SKIP_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    "dist",
    "site-packages",
}


class DiscoveryError(ValueError):
    """The requested path is not a canon and does not bound exactly one."""


@dataclass
class Candidate:
    path: Path
    name: str
    relative: str


@dataclass
class Resolution:
    world: Path
    name: str
    manifest: dict
    warnings: list[str] = field(default_factory=list)


def _read_manifest(world: Path) -> tuple[dict, list[str]]:
    warnings: list[str] = []
    path = world / WORLD_MANIFEST
    try:
        parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        warnings.append(f"{WORLD_MANIFEST}: cannot be read ({exc})")
        return {}, warnings
    if parsed is None:
        warnings.append(f"{WORLD_MANIFEST}: empty manifest")
        return {}, warnings
    if not isinstance(parsed, dict):
        warnings.append(f"{WORLD_MANIFEST}: not a mapping")
        return {}, warnings
    return parsed, warnings


def world_display_name(world: Path, manifest: dict) -> str:
    raw = manifest.get("name")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return world.name


def is_canon(path: Path) -> bool:
    return (path / WORLD_MANIFEST).is_file()


def find_candidates(root: Path) -> list[Candidate]:
    """Return every canon folder at or just below a bounded root, in path order."""
    root = Path(root)
    found: list[Candidate] = []

    def walk(directory: Path, depth: int) -> None:
        if depth > MAX_DEPTH:
            return
        try:
            entries = sorted(directory.iterdir(), key=lambda item: item.name.lower())
        except OSError:
            return
        for entry in entries:
            if not entry.is_dir() or entry.name in SKIP_NAMES or entry.name.startswith("."):
                continue
            if is_canon(entry):
                manifest, _ = _read_manifest(entry)
                found.append(
                    Candidate(
                        path=entry.resolve(),
                        name=world_display_name(entry, manifest),
                        relative=entry.relative_to(root).as_posix(),
                    )
                )
                # A world inside a world is not a thing; do not descend.
                continue
            walk(entry, depth + 1)

    walk(root, 1)
    return found


def resolve_canon(target: str | Path) -> Resolution:
    """Return the one canon a session is about, or raise with the candidates."""
    path = Path(target).expanduser()
    if not path.exists():
        raise DiscoveryError(f"path does not exist: {path}")
    if not path.is_dir():
        raise DiscoveryError(f"not a folder: {path}")
    path = path.resolve()

    if is_canon(path):
        manifest, warnings = _read_manifest(path)
        return Resolution(
            world=path,
            name=world_display_name(path, manifest),
            manifest=manifest,
            warnings=warnings,
        )

    candidates = find_candidates(path)
    if not candidates:
        raise DiscoveryError(
            f"no canon folder found in {path}; a canon folder is one containing "
            f"{WORLD_MANIFEST}"
        )
    if len(candidates) > 1:
        listing = "\n".join(
            f"  {candidate.relative}\t{candidate.name}" for candidate in candidates
        )
        raise DiscoveryError(
            f"{len(candidates)} canon folders under {path}; name one of them:\n{listing}"
        )

    only = candidates[0]
    manifest, warnings = _read_manifest(only.path)
    return Resolution(
        world=only.path,
        name=only.name,
        manifest=manifest,
        warnings=warnings,
    )
