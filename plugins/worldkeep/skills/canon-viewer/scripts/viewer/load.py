"""Load a KERNEL canon folder without applying view or rendering logic."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

import yaml


KINDS = {"entity", "idea", "relation", "type"}
NON_ARTIFACT_NAMES = {"friction-log.md", "index.md", "manifest.md", "readme.md"}
STANDARD_ID_NAMESPACES = {"actions", "entities", "ideas", "relations", "types"}
VIEW_KEYS = {
    "assert",
    "compose",
    "edges",
    "emphasis",
    "layout",
    "lenses",
    "name",
    "render",
    "resolution",
    "select",
    "styles",
}

_FRONTMATTER = re.compile(
    r"\A\ufeff?---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)",
    re.DOTALL,
)


class CanonLoadError(ValueError):
    """The requested canon folder cannot be loaded at all."""


class ViewLoadError(ValueError):
    """A view file is missing or malformed."""


class ProjectionPolicy(str, Enum):
    """The viewer policy that owns a projection's selection and presentation."""

    CUSTOM_NAMED = "custom_named"
    AUDIT_GENERAL = "audit_general"


@dataclass(frozen=True)
class Artifact:
    id: str
    kind: str | None
    type: str | None
    name: str
    frontmatter: Mapping[str, Any]
    body: str
    path: Path
    relative_path: str


@dataclass
class Canon:
    root: Path
    world: Mapping[str, Any]
    artifacts: dict[str, Artifact]
    types: dict[str, Artifact]
    warnings: list[str]

    def resolve_type(self, type_path: str | None) -> Artifact | None:
        """Return the nearest defined type, checking the leaf before ancestors."""
        if not type_path:
            return None
        parts = type_path.split("/")
        for size in range(len(parts), 0, -1):
            candidate = "/".join(parts[:size])
            if candidate in self.types:
                return self.types[candidate]
        return None


@dataclass(frozen=True)
class View:
    name: str
    render: str
    data: Mapping[str, Any]
    path: Path
    relative_path: str
    warnings: tuple[str, ...]
    policy: ProjectionPolicy = ProjectionPolicy.CUSTOM_NAMED


_RESERVED_EVERYTHING_MESSAGE = (
    "Everything is now built in and cannot be shadowed; move durable rules "
    "to a differently named custom view"
)


def builtin_everything() -> View:
    """Return the viewer-owned audit projection, never a world-local recipe."""
    return View(
        name="Everything",
        render="graph",
        data={},
        path=Path("<built-in:everything>"),
        relative_path="<built-in:everything>",
        warnings=(),
        policy=ProjectionPolicy.AUDIT_GENERAL,
    )


#: Validation locks sit beside their view but are never themselves views.
LOCK_SUFFIX = ".view.lock.yaml"


def is_lock_path(path: Path) -> bool:
    """True when a file under ``views/`` is a validation lock, not a recipe."""
    return path.name.casefold().endswith(LOCK_SUFFIX)


def lock_path_for(view_path: Path) -> Path:
    """Return the adjacent lock path for one view file."""
    stem = view_path.name
    for suffix in (".yaml", ".yml"):
        if stem.casefold().endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    return view_path.with_name(f"{stem}{LOCK_SUFFIX}")


def _relative_id(path: Path, root: Path) -> str:
    return path.relative_to(root).with_suffix("").as_posix()


def _read_yaml_mapping(path: Path, *, error_type: type[ValueError]) -> dict[str, Any]:
    try:
        parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as exc:
        raise error_type(f"cannot read {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise error_type(f"malformed YAML in {path}: {exc}") from exc

    if parsed is None:
        return {}
    if not isinstance(parsed, dict):
        raise error_type(f"expected a YAML mapping in {path}")
    return parsed


def _load_world(root: Path, warnings: list[str]) -> Mapping[str, Any]:
    path = root / "world.yaml"
    if not path.is_file():
        warnings.append("world.yaml: missing world manifest")
        return {}
    try:
        return _read_yaml_mapping(path, error_type=CanonLoadError)
    except CanonLoadError as exc:
        warnings.append(f"world.yaml: {exc}")
        return {}


def _parse_artifact(path: Path, root: Path, warnings: list[str]) -> Artifact | None:
    relative_path = path.relative_to(root).as_posix()
    try:
        with path.open("r", encoding="utf-8", newline="") as source:
            text = source.read()
    except (OSError, UnicodeError) as exc:
        warnings.append(f"{relative_path}: cannot read artifact: {exc}")
        return None

    match = _FRONTMATTER.match(text)
    if not match:
        warnings.append(f"{relative_path}: no YAML frontmatter; skipped")
        return None

    try:
        frontmatter = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        warnings.append(f"{relative_path}: malformed YAML frontmatter: {exc}; skipped")
        return None
    if not isinstance(frontmatter, dict):
        warnings.append(f"{relative_path}: frontmatter is not a mapping; skipped")
        return None

    conventional_id = _relative_id(path, root)
    raw_id = frontmatter.get("id")
    if raw_id is None:
        warnings.append(f"{relative_path}: missing id; using '{conventional_id}'")
        artifact_id = conventional_id
    elif not isinstance(raw_id, str) or not raw_id.strip():
        warnings.append(f"{relative_path}: invalid id; skipped")
        return None
    else:
        artifact_id = raw_id.strip()

    if artifact_id != conventional_id:
        warnings.append(
            f"{relative_path}: id '{artifact_id}' does not match path '{conventional_id}'"
        )

    raw_kind = frontmatter.get("kind")
    kind = raw_kind if isinstance(raw_kind, str) else None
    if kind is None:
        warnings.append(f"{relative_path}: missing or invalid kind")
    elif kind not in KINDS:
        warnings.append(f"{relative_path}: unknown kind '{kind}'")

    raw_type = frontmatter.get("type")
    artifact_type = raw_type if isinstance(raw_type, str) and raw_type else None
    raw_name = frontmatter.get("name")
    name = raw_name if isinstance(raw_name, str) and raw_name else artifact_id

    return Artifact(
        id=artifact_id,
        kind=kind,
        type=artifact_type,
        name=name,
        frontmatter=frontmatter,
        body=text[match.end() :],
        path=path,
        relative_path=relative_path,
    )


def _member_references(artifact: Artifact, warnings: list[str]) -> Iterable[str]:
    members = artifact.frontmatter.get("members")
    if members is None:
        return ()
    if not isinstance(members, list):
        warnings.append(f"{artifact.relative_path}: members is not a list")
        return ()

    references: list[str] = []
    for index, member in enumerate(members):
        if isinstance(member, str):
            references.append(member)
        elif isinstance(member, dict) and isinstance(member.get("id"), str):
            references.append(member["id"])
        else:
            warnings.append(
                f"{artifact.relative_path}: member {index + 1} has no valid id"
            )
    return references


def _facet_references(
    artifact: Artifact,
    known_namespaces: set[str],
) -> Iterable[str]:
    references: list[str] = []

    where = artifact.frontmatter.get("where")
    if isinstance(where, str):
        references.append(where)
    elif isinstance(where, list):
        references.extend(value for value in where if isinstance(value, str))

    when = artifact.frontmatter.get("when")
    if isinstance(when, str) and "/" in when:
        namespace = when.split("/", 1)[0]
        if namespace in known_namespaces:
            references.append(when)

    return references


def _check_references(canon: Canon) -> None:
    namespaces = STANDARD_ID_NAMESPACES | {
        artifact_id.split("/", 1)[0]
        for artifact_id in canon.artifacts
        if "/" in artifact_id
    }
    for artifact in canon.artifacts.values():
        references = list(_member_references(artifact, canon.warnings))
        references.extend(_facet_references(artifact, namespaces))
        for reference in references:
            if reference not in canon.artifacts:
                canon.warnings.append(
                    f"{artifact.relative_path}: dangling reference '{reference}'"
                )


def load_canon(root: str | Path) -> Canon:
    """Load a canon folder; artifact problems become warnings, not exceptions."""
    root_path = Path(root).expanduser().resolve()
    if not root_path.is_dir():
        raise CanonLoadError(f"canon folder does not exist: {root_path}")

    warnings: list[str] = []
    world = _load_world(root_path, warnings)
    artifacts: dict[str, Artifact] = {}

    for path in sorted(root_path.rglob("*.md"), key=lambda value: value.as_posix().lower()):
        if path.name.lower() in NON_ARTIFACT_NAMES:
            continue
        artifact = _parse_artifact(path, root_path, warnings)
        if artifact is None:
            continue
        if artifact.id in artifacts:
            warnings.append(
                f"{artifact.relative_path}: duplicate id '{artifact.id}'; first file kept"
            )
            continue
        artifacts[artifact.id] = artifact

    types = {
        artifact.id.removeprefix("types/"): artifact
        for artifact in artifacts.values()
        if artifact.kind == "type" and artifact.id.startswith("types/")
    }
    canon = Canon(
        root=root_path,
        world=world,
        artifacts=artifacts,
        types=types,
        warnings=warnings,
    )
    _check_references(canon)
    return canon


def resolve_view_path(root: str | Path, view: str | Path) -> Path:
    """Resolve a view relative to the canon while rejecting path traversal."""
    root_path = Path(root).expanduser().resolve()
    raw = Path(view)
    candidate = raw.resolve() if raw.is_absolute() else (root_path / raw).resolve()
    views_root = (root_path / "views").resolve()
    try:
        candidate.relative_to(views_root)
    except ValueError as exc:
        raise ViewLoadError(f"view must be inside {views_root}: {candidate}") from exc
    if candidate.suffix.lower() not in {".yaml", ".yml"}:
        raise ViewLoadError(f"view must be a YAML file: {candidate}")
    if not candidate.is_file():
        raise ViewLoadError(f"view file does not exist: {candidate}")
    return candidate


def load_view(root: str | Path, view: str | Path) -> View:
    """Load one view file. Unlike artifact issues, malformed views are fatal."""
    root_path = Path(root).expanduser().resolve()
    path = resolve_view_path(root_path, view)
    if is_lock_path(path):
        raise ViewLoadError(
            f"{path}: this is a validation lock, not a view recipe"
        )
    if path.stem.casefold() == "everything":
        raise ViewLoadError(f"{path}: {_RESERVED_EVERYTHING_MESSAGE}")
    data = _read_yaml_mapping(path, error_type=ViewLoadError)
    warnings = [
        f"{path.name}: unknown view key '{key}'"
        for key in data
        if key not in VIEW_KEYS
    ]

    raw_name = data.get("name", path.stem)
    if not isinstance(raw_name, str) or not raw_name.strip():
        raise ViewLoadError(f"view name must be a non-empty string: {path}")
    if raw_name.strip().casefold() == "everything":
        raise ViewLoadError(f"{path}: {_RESERVED_EVERYTHING_MESSAGE}")
    raw_render = data.get("render", "graph")
    if not isinstance(raw_render, str) or not raw_render.strip():
        raise ViewLoadError(f"view render must be a non-empty string: {path}")
    if raw_render != "graph":
        warnings.append(f"{path.name}: unknown renderer '{raw_render}'; using generically")

    return View(
        name=raw_name.strip(),
        render=raw_render.strip(),
        data=data,
        path=path,
        relative_path=path.relative_to(root_path).as_posix(),
        warnings=tuple(warnings),
    )


def list_views(root: str | Path) -> list[View]:
    """Return built-in Everything followed by YAML views in path order."""
    root_path = Path(root).expanduser().resolve()
    if not root_path.is_dir():
        raise CanonLoadError(f"canon folder does not exist: {root_path}")
    views_root = root_path / "views"
    if not views_root.is_dir():
        return [builtin_everything()]
    paths = sorted(
        (
            path
            for path in views_root.rglob("*")
            if path.is_file()
            and path.suffix.lower() in {".yaml", ".yml"}
            and not is_lock_path(path)
        ),
        key=lambda value: value.as_posix().lower(),
    )
    return [builtin_everything(), *(load_view(root_path, path) for path in paths)]
