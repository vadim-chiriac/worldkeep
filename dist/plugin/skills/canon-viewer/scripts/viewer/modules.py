"""Strict, world-local view-module manifests and a safe module index.

A view module is one flat, typed YAML unit directly under ``view-modules/``.
Modules never import other modules, never reach outside their folder, and never
carry executable expressions. This module owns parsing, path safety, duplicate
detection, kind-aware reference resolution, and normalized content hashes; it
deliberately knows nothing about composition, projection, or rendering.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .load import _read_yaml_mapping
from .project import BEHAVIORS, LENS_KEYS


MODULE_SCHEMA = "wb.view-module/v1"

#: Every module declares exactly one kind and carries exactly one payload key.
MODULE_PAYLOAD_KEYS: dict[str, str] = {
    "selection": "select",
    "relation": "edges",
    "style": "rules",
    "lens": "overlays",
}
MODULE_KINDS = frozenset(MODULE_PAYLOAD_KEYS)

MANIFEST_KEYS = frozenset({"schema", "id", "version", "kind"})

#: Selector keys a selection module may use. Deliberately the same vocabulary a
#: view-local ``select`` block already understands, so one evaluator serves both.
SELECTION_KEYS = frozenset(
    {
        "kinds",
        "types",
        "status",
        "tags",
        "where_under",
        "when_range",
        "connected_to_kinds",
        "connected_to_types",
    }
)

#: Anchor keys that may survive composition only once (brief section 5.4).
ANCHOR_KEYS = ("connected_to_kinds", "connected_to_types")

RELATION_KEYS = frozenset({"include", "exclude"})

#: Structural lens keys. Conflicts between these are errors, not warnings.
STRUCTURAL_KEYS = frozenset({"as", "direction"})

#: Presentation properties a style rule may set: the nonstructural lens keys.
STYLE_SET_KEYS = frozenset({"color", "label", "line", "shape", "width"})

#: A lens overlay may set any known lens key, structural ones included.
LENS_SET_KEYS = frozenset(LENS_KEYS)

#: V1 match selectors are narrow on purpose: no arbitrary expressions.
MATCH_KEYS = frozenset({"kind", "type"})

RULE_KEYS = frozenset({"match", "set"})

#: Keys that would reintroduce recursion, inheritance, or remote composition.
_FORBIDDEN_MANIFEST_KEYS = {
    "compose": "modules cannot compose other modules",
    "import": "modules cannot import",
    "imports": "modules cannot import",
    "include": "modules cannot include other modules",
    "includes": "modules cannot include other modules",
    "extends": "modules cannot inherit",
    "inherit": "modules cannot inherit",
    "inherits": "modules cannot inherit",
    "modules": "modules cannot reference other modules",
    "source": "modules cannot load remote or external sources",
    "url": "modules cannot load remote or external sources",
    "path": "modules cannot reference arbitrary paths",
}

_ID_FIRST = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
_ID_REST = _ID_FIRST | set("._-")

MODULES_DIRNAME = "view-modules"


class ModuleError(ValueError):
    """A view module is missing, malformed, unsafe, or wrongly referenced."""


@dataclass(frozen=True)
class ViewModule:
    """One validated, normalized module manifest."""

    id: str
    kind: str
    version: int
    schema: str
    payload: Mapping[str, Any]
    path: Path
    relative_path: str
    content_hash: str

    def provenance(self) -> dict[str, Any]:
        """Return the stable provenance record recorded in a compiled plan."""
        return {
            "id": self.id,
            "kind": self.kind,
            "schema": self.schema,
            "version": self.version,
            "path": self.relative_path,
            "content_hash": self.content_hash,
        }


@dataclass(frozen=True)
class ModuleIndex:
    """Every module found directly under one world's ``view-modules/``."""

    root: Path
    relative_root: str
    modules: Mapping[str, ViewModule]
    warnings: tuple[str, ...] = ()

    def get(self, module_id: str) -> ViewModule | None:
        return self.modules.get(module_id)

    def resolve(self, reference: Any, *, kind: str, context: str) -> ViewModule:
        """Resolve one reference to a module of the required ``kind``."""
        if kind not in MODULE_KINDS:  # pragma: no cover - internal misuse
            raise ModuleError(f"unknown module kind requested: {kind!r}")
        module_id = _validated_reference(reference, context=context)
        module = self.modules.get(module_id)
        if module is None:
            known = ", ".join(sorted(self.modules)) or "none"
            raise ModuleError(
                f"{context}: no module with id '{module_id}' in "
                f"{self.relative_root}/ (known ids: {known})"
            )
        if module.kind != kind:
            raise ModuleError(
                f"{context}: module '{module_id}' has kind '{module.kind}', "
                f"but this section requires kind '{kind}' "
                f"({module.relative_path})"
            )
        return module

    def fingerprint(self) -> str:
        """Return a hash of the whole index, for lock and cache keys."""
        return _normalized_hash(
            {module_id: module.content_hash for module_id, module in sorted(self.modules.items())}
        )


def _normalized_hash(value: Any) -> str:
    """Hash parsed content, not bytes, so formatting and line endings cannot matter."""
    canonical = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validated_reference(reference: Any, *, context: str) -> str:
    """Reject anything that is not a bare, world-local module id."""
    if not isinstance(reference, str) or not reference.strip():
        raise ModuleError(f"{context}: module reference must be a non-empty string")
    candidate = reference.strip()
    if candidate != reference:
        raise ModuleError(
            f"{context}: module reference '{reference}' has surrounding whitespace"
        )
    lowered = candidate.lower()
    if "://" in candidate or lowered.startswith(("http:", "https:", "file:")):
        raise ModuleError(
            f"{context}: remote module reference '{candidate}' is not supported"
        )
    if "/" in candidate or "\\" in candidate or candidate.startswith("."):
        raise ModuleError(
            f"{context}: module reference '{candidate}' must be a bare module id, "
            "not a path"
        )
    if not _is_safe_id(candidate):
        raise ModuleError(
            f"{context}: module reference '{candidate}' is not a valid module id"
        )
    return candidate


def _is_safe_id(value: str) -> bool:
    return bool(value) and value[0] in _ID_FIRST and all(char in _ID_REST for char in value)


def _require_mapping(value: Any, *, where: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ModuleError(f"{where} must be a mapping")
    for key in value:
        if not isinstance(key, str):
            raise ModuleError(f"{where} has a non-string key {key!r}")
    return value


def _reject_unknown(value: Mapping[str, Any], allowed: frozenset[str], *, where: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ModuleError(
            f"{where}: unknown field(s) {', '.join(repr(key) for key in unknown)}; "
            f"allowed: {', '.join(sorted(allowed))}"
        )


def _string_list(value: Any, *, where: str) -> list[str]:
    if isinstance(value, str):
        raise ModuleError(f"{where} must be a list of strings, not a bare string")
    if not isinstance(value, list):
        raise ModuleError(f"{where} must be a list of strings")
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ModuleError(f"{where} must contain only non-empty strings")
    return [item.strip() for item in value]


def _validate_selection_payload(payload: Any, *, where: str) -> dict[str, Any]:
    select = _require_mapping(payload, where=where)
    _reject_unknown(select, SELECTION_KEYS, where=where)
    if not select:
        raise ModuleError(f"{where} must select something")
    normalized: dict[str, Any] = {}
    for key, value in select.items():
        if key == "when_range":
            window = _require_mapping(value, where=f"{where}.when_range")
            _reject_unknown(window, frozenset({"from", "to"}), where=f"{where}.when_range")
            for bound, bound_value in window.items():
                if not isinstance(bound_value, (int, float)) or isinstance(bound_value, bool):
                    raise ModuleError(
                        f"{where}.when_range.{bound} must be a number"
                    )
            normalized[key] = dict(window)
        else:
            normalized[key] = _string_list(value, where=f"{where}.{key}")
    return normalized


def _validate_relation_payload(payload: Any, *, where: str) -> dict[str, Any]:
    edges = _require_mapping(payload, where=where)
    _reject_unknown(edges, RELATION_KEYS, where=where)
    normalized: dict[str, Any] = {}
    for key in ("include", "exclude"):
        if key in edges:
            normalized[key] = _string_list(edges[key], where=f"{where}.{key}")
    if not normalized:
        raise ModuleError(f"{where} must declare 'include' or 'exclude'")
    return normalized


def _validate_match(value: Any, *, where: str) -> dict[str, str]:
    match = _require_mapping(value, where=where)
    _reject_unknown(match, MATCH_KEYS, where=where)
    if not match:
        raise ModuleError(f"{where} must constrain 'kind' or 'type'")
    normalized: dict[str, str] = {}
    for key, item in match.items():
        if not isinstance(item, str) or not item.strip():
            raise ModuleError(f"{where}.{key} must be a non-empty string")
        normalized[key] = item.strip()
    return normalized


def _validate_set(value: Any, *, allowed: frozenset[str], where: str) -> dict[str, Any]:
    properties = _require_mapping(value, where=where)
    _reject_unknown(properties, allowed, where=where)
    if not properties:
        raise ModuleError(f"{where} must set at least one property")
    normalized: dict[str, Any] = {}
    for key, item in properties.items():
        normalized[key] = _validate_property(key, item, where=f"{where}.{key}")
    return normalized


def _validate_property(key: str, value: Any, *, where: str) -> Any:
    if key == "as":
        if not isinstance(value, str) or value not in BEHAVIORS:
            raise ModuleError(
                f"{where} must be one of {', '.join(sorted(BEHAVIORS))}"
            )
        return value
    if key == "direction":
        if isinstance(value, str) or not isinstance(value, list) or len(value) != 2:
            raise ModuleError(f"{where} must be [source_role, target_role]")
        roles = [item.strip() if isinstance(item, str) else item for item in value]
        if any(not isinstance(role, str) or not role for role in roles):
            raise ModuleError(f"{where} roles must be non-empty strings")
        if roles[0] == roles[1]:
            raise ModuleError(f"{where} roles must differ")
        return roles
    if key == "width":
        if isinstance(value, bool):
            raise ModuleError(f"{where} must be a number or 'weight'")
        if isinstance(value, (int, float)):
            return float(value)
        if value == "weight":
            return value
        raise ModuleError(f"{where} must be a number or 'weight'")
    if key == "collapse_default":
        if not isinstance(value, bool):
            raise ModuleError(f"{where} must be true or false")
        return value
    if not isinstance(value, str) or not value.strip():
        raise ModuleError(f"{where} must be a non-empty string")
    return value.strip()


def _validate_rules(payload: Any, *, allowed: frozenset[str], where: str) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise ModuleError(f"{where} must be a list of rules")
    if not payload:
        raise ModuleError(f"{where} must contain at least one rule")
    rules: list[dict[str, Any]] = []
    for index, raw in enumerate(payload, start=1):
        label = f"{where}[{index}]"
        rule = _require_mapping(raw, where=label)
        _reject_unknown(rule, RULE_KEYS, where=label)
        if "match" not in rule or "set" not in rule:
            raise ModuleError(f"{label} must have both 'match' and 'set'")
        rules.append(
            {
                "match": _validate_match(rule["match"], where=f"{label}.match"),
                "set": _validate_set(rule["set"], allowed=allowed, where=f"{label}.set"),
            }
        )
    return rules


def validate_style_rules(payload: Any, *, where: str) -> list[dict[str, Any]]:
    """Validate view-local ``styles`` with the same strictness as a style module."""
    return _validate_rules(payload, allowed=STYLE_SET_KEYS, where=where)


def validate_lens_rules(payload: Any, *, where: str) -> list[dict[str, Any]]:
    """Validate view-local ``lenses`` with the same strictness as a lens module."""
    return _validate_rules(payload, allowed=LENS_SET_KEYS, where=where)


def _validate_payload(kind: str, payload: Any, *, where: str) -> Any:
    if kind == "selection":
        return _validate_selection_payload(payload, where=where)
    if kind == "relation":
        return _validate_relation_payload(payload, where=where)
    if kind == "style":
        return _validate_rules(payload, allowed=STYLE_SET_KEYS, where=where)
    return _validate_rules(payload, allowed=LENS_SET_KEYS, where=where)


def parse_module(data: Mapping[str, Any], *, relative_path: str, path: Path) -> ViewModule:
    """Validate one parsed manifest into a normalized :class:`ViewModule`."""
    manifest = _require_mapping(data, where=f"{relative_path}: module")

    for key, reason in _FORBIDDEN_MANIFEST_KEYS.items():
        if key in manifest:
            raise ModuleError(f"{relative_path}: '{key}' is not allowed; {reason}")

    schema = manifest.get("schema")
    if schema != MODULE_SCHEMA:
        raise ModuleError(
            f"{relative_path}: schema must be '{MODULE_SCHEMA}', got {schema!r}"
        )

    kind = manifest.get("kind")
    if not isinstance(kind, str) or kind not in MODULE_KINDS:
        raise ModuleError(
            f"{relative_path}: kind must be one of {', '.join(sorted(MODULE_KINDS))}, "
            f"got {kind!r}"
        )

    raw_id = manifest.get("id")
    if not isinstance(raw_id, str) or not raw_id.strip():
        raise ModuleError(f"{relative_path}: id must be a non-empty string")
    module_id = raw_id.strip()
    if not _is_safe_id(module_id):
        raise ModuleError(
            f"{relative_path}: id '{module_id}' must start with a letter or digit and "
            "use only letters, digits, '.', '_', or '-'"
        )

    version = manifest.get("version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ModuleError(f"{relative_path}: version must be a positive integer")

    payload_key = MODULE_PAYLOAD_KEYS[kind]
    for other_kind, other_key in MODULE_PAYLOAD_KEYS.items():
        if other_key != payload_key and other_key in manifest:
            raise ModuleError(
                f"{relative_path}: kind '{kind}' must carry '{payload_key}', "
                f"not the '{other_key}' payload of kind '{other_kind}'"
            )
    allowed = MANIFEST_KEYS | {payload_key}
    _reject_unknown(manifest, frozenset(allowed), where=f"{relative_path}: module")
    if payload_key not in manifest:
        raise ModuleError(f"{relative_path}: kind '{kind}' requires a '{payload_key}' payload")

    payload = _validate_payload(
        kind, manifest[payload_key], where=f"{relative_path}: {payload_key}"
    )

    return ViewModule(
        id=module_id,
        kind=kind,
        version=version,
        schema=schema,
        payload=payload,
        path=path,
        relative_path=relative_path,
        content_hash=_normalized_hash(
            {
                "schema": schema,
                "id": module_id,
                "version": version,
                "kind": kind,
                payload_key: payload,
            }
        ),
    )


def load_module_index(root: str | Path) -> ModuleIndex:
    """Index only the direct YAML children of ``<root>/view-modules``."""
    root_path = Path(root).expanduser().resolve()
    modules_root = (root_path / MODULES_DIRNAME).resolve()
    relative_root = MODULES_DIRNAME

    if not modules_root.is_dir():
        return ModuleIndex(
            root=modules_root, relative_root=relative_root, modules={}, warnings=()
        )

    warnings: list[str] = []
    modules: dict[str, ViewModule] = {}
    origins: dict[str, str] = {}

    for entry in sorted(modules_root.iterdir(), key=lambda value: value.name.lower()):
        if entry.is_dir():
            warnings.append(
                f"{relative_root}/{entry.name}/: nested module folders are ignored; "
                "modules must be direct children"
            )
            continue
        if entry.suffix.lower() not in {".yaml", ".yml"}:
            continue

        relative_path = f"{relative_root}/{entry.name}"
        resolved = entry.resolve()
        if resolved.parent != modules_root:
            raise ModuleError(
                f"{relative_path}: resolves outside {relative_root}/ "
                f"({resolved}); links out of the module folder are not allowed"
            )

        data = _read_yaml_mapping(resolved, error_type=ModuleError)
        module = parse_module(data, relative_path=relative_path, path=resolved)
        if module.id in modules:
            raise ModuleError(
                f"{relative_path}: duplicate module id '{module.id}'; "
                f"already defined by {origins[module.id]}"
            )
        modules[module.id] = module
        origins[module.id] = relative_path

    return ModuleIndex(
        root=modules_root,
        relative_root=relative_root,
        modules=modules,
        warnings=tuple(warnings),
    )
