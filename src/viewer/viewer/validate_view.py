"""Validate that a named view compiles to a deterministic, renderable result.

Validation is not semantic endorsement. It proves that a recipe resolves the
same way every time, that its structure can actually be drawn, and that its
recorded dependencies still match. Nothing here rewrites a view, a module, or
a lock: a lock is written only when a caller explicitly asks for one, and only
after a clean result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml

from .compile import CompileError, CompiledViewPlan, compile_view
from .load import Canon, View, ViewLoadError, lock_path_for
from .modules import ModuleError, ModuleIndex, load_module_index
from .project import project_view


LOCK_SCHEMA = "wb.view-lock/v1"

#: Structural findings that a validated, reusable view may not retain.
STRUCTURAL_ERRORS = {
    "structure.multiple-nest-parents",
    "structure.containment-cycle",
    "structure.invalid-direction",
    "structure.nest-not-whole",
}

ASSERT_KEYS = frozenset({"nonempty", "contains_types", "no_structural_conflicts"})


@dataclass
class ValidationResult:
    """The outcome of validating one named view."""

    view_path: str
    view_name: str
    ok: bool
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    style_rules: list[dict[str, Any]] = field(default_factory=list)
    fingerprint: str | None = None
    lock_state: str = "absent"
    lock_changes: list[str] = field(default_factory=list)
    plan: CompiledViewPlan | None = None
    projection: Mapping[str, Any] | None = None

    def as_json(self) -> dict[str, Any]:
        return {
            "view": {"name": self.view_name, "path": self.view_path},
            "ok": self.ok,
            "errors": self.errors,
            "warnings": self.warnings,
            "counts": self.counts,
            "style_rules": self.style_rules,
            "fingerprint": self.fingerprint,
            "lock": {"state": self.lock_state, "changes": self.lock_changes},
        }

    def as_text(self) -> str:
        lines = [f"view: {self.view_name} ({self.view_path})"]
        lines.append(f"result: {'VALID' if self.ok else 'INVALID'}")
        if self.counts:
            lines.append(
                f"projected: {self.counts.get('nodes', 0)} node(s), "
                f"{self.counts.get('edges', 0)} edge(s)"
            )
        if self.style_rules:
            lines.append(f"style rules ({len(self.style_rules)}):")
            for rule in self.style_rules:
                match = ", ".join(
                    f"{key}: {value}" for key, value in sorted(rule["match"].items())
                )
                lines.append(
                    f"  {rule['source']}: {rule['matched_count']} match(es) for "
                    f"{{{match}}}"
                )
        if self.fingerprint:
            lines.append(f"fingerprint: {self.fingerprint[:16]}…")
        lines.append(f"lock: {self.lock_state}")
        for change in self.lock_changes:
            lines.append(f"  changed: {change}")
        if self.errors:
            lines.append("")
            lines.append(f"errors ({len(self.errors)}):")
            for item in self.errors:
                lines.append(f"  [{item['code']}] {item['message']}")
        if self.warnings:
            lines.append("")
            lines.append(f"warnings ({len(self.warnings)}):")
            for item in self.warnings:
                lines.append(f"  [{item['code']}] {item['message']}")
        return "\n".join(lines) + "\n"


def _entry(code: str, message: str, **detail: Any) -> dict[str, Any]:
    record = {"code": code, "message": message}
    if detail:
        record["detail"] = detail
    return record


def _style_rule_records(canon: Canon, plan: CompiledViewPlan) -> list[dict[str, Any]]:
    """Describe each style selector against the exact cascade input scope.

    This is deliberately observational. A literal ``place`` remains distinct
    from ``place/*``; the report only makes that narrowness visible before an
    author mistakes a valid recipe for a fully styled type family.
    """
    artifacts = [
        canon.artifacts[artifact_id]
        for artifact_id in sorted(plan.base_ids | plan.relation_ids)
        if artifact_id in canon.artifacts
    ]
    records: list[dict[str, Any]] = []
    for rule in plan.style_rules:
        matched = [artifact for artifact in artifacts if rule.matches(artifact)]
        record: dict[str, Any] = {
            "source": rule.source,
            "match": dict(rule.match),
            "set": dict(rule.set),
            "matched_count": len(matched),
        }

        pattern = rule.match.get("type")
        if pattern is not None and not any(character in pattern for character in "*?["):
            kind = rule.match.get("kind")
            descendants = [
                artifact
                for artifact in artifacts
                if (kind is None or artifact.kind == kind)
                and artifact.type is not None
                and artifact.type.startswith(f"{pattern}/")
            ]
            if descendants:
                record["descendant_count"] = len(descendants)
                record["descendant_types"] = sorted(
                    {artifact.type for artifact in descendants if artifact.type is not None}
                )
        records.append(record)
    return records


def _style_rule_warnings(view: View, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return non-failing notices for inert or accidentally narrow styles."""
    warnings: list[dict[str, Any]] = []
    for record in records:
        descendants = record.get("descendant_count", 0)
        if descendants:
            pattern = record["match"]["type"]
            types = ", ".join(record["descendant_types"])
            warnings.append(
                _entry(
                    "style.exact-type-descendants",
                    f"{view.relative_path}: {record['source']}: exact type {pattern!r} "
                    f"matches {record['matched_count']} selected artifact(s), but "
                    f"{descendants} selected descendant artifact(s) use {types} and are "
                    f"not matched; add a separate rule with type {pattern + '/*'!r} "
                    "if descendants should share this style",
                    **record,
                )
            )
        elif record["matched_count"] == 0:
            warnings.append(
                _entry(
                    "style.rule-unmatched",
                    f"{view.relative_path}: {record['source']}: style rule matches "
                    "0 selected artifact(s)",
                    **record,
                )
            )
    return warnings


def _validate_assertions(
    view: View,
    plan: CompiledViewPlan,
    projection: Mapping[str, Any],
    canon: Canon,
    errors: list[dict[str, Any]],
) -> None:
    raw = view.data.get("assert")
    if raw is None:
        return
    if not isinstance(raw, dict):
        errors.append(_entry("assert.malformed", f"{view.relative_path}: 'assert' must be a mapping"))
        return
    unknown = sorted(set(raw) - ASSERT_KEYS)
    if unknown:
        errors.append(
            _entry(
                "assert.unknown",
                f"{view.relative_path}: unknown assertion(s) "
                f"{', '.join(repr(key) for key in unknown)}; "
                f"supported: {', '.join(sorted(ASSERT_KEYS))}",
            )
        )
        return

    if raw.get("nonempty") is True and not projection["nodes"]:
        errors.append(
            _entry("assert.nonempty", f"{view.relative_path}: assert.nonempty failed; no nodes")
        )

    expected_types = raw.get("contains_types")
    if expected_types is not None:
        if not isinstance(expected_types, list) or not all(
            isinstance(item, str) for item in expected_types
        ):
            errors.append(
                _entry(
                    "assert.malformed",
                    f"{view.relative_path}: assert.contains_types must be a list of strings",
                )
            )
        else:
            present = {node["type"] for node in projection["nodes"] if node["type"]}
            missing = [
                expected
                for expected in expected_types
                if not any(
                    actual == expected or actual.startswith(f"{expected}/")
                    for actual in present
                )
            ]
            if missing:
                errors.append(
                    _entry(
                        "assert.contains_types",
                        f"{view.relative_path}: assert.contains_types failed; "
                        f"no artifacts of type {', '.join(missing)}",
                        missing=missing,
                    )
                )

    if raw.get("no_structural_conflicts") is True:
        conflicts = [
            item for item in plan.diagnostics if item.code == "lens.structural-conflict"
        ]
        if conflicts:
            errors.append(
                _entry(
                    "assert.no_structural_conflicts",
                    f"{view.relative_path}: assert.no_structural_conflicts failed; "
                    f"{len(conflicts)} unresolved conflict(s)",
                )
            )


def read_lock(view: View) -> dict[str, Any] | None:
    """Return the parsed lock beside one view, if it exists."""
    path = lock_path_for(view.path)
    if not path.is_file():
        return None
    try:
        parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ViewLoadError(f"cannot read lock {path}: {exc}") from exc
    return parsed if isinstance(parsed, dict) else None


def _lock_changes(stored: Mapping[str, Any], current: Mapping[str, Any]) -> list[str]:
    """Name what moved between a recorded and a current provenance record."""
    changes: list[str] = []
    for key in ("compiler_schema", "kernel_version", "type_fingerprint"):
        if stored.get(key) != current.get(key):
            changes.append(key.replace("_", " "))

    stored_view = stored.get("view") or {}
    current_view = current.get("view") or {}
    if stored_view.get("content_hash") != current_view.get("content_hash"):
        changes.append(f"view recipe {current_view.get('path', '')}".strip())

    stored_modules = {item["id"]: item for item in stored.get("modules", [])}
    current_modules = {item["id"]: item for item in current.get("modules", [])}
    for module_id in sorted(set(stored_modules) | set(current_modules)):
        if module_id not in current_modules:
            changes.append(f"module '{module_id}' is no longer referenced")
        elif module_id not in stored_modules:
            changes.append(f"module '{module_id}' is newly referenced")
        elif stored_modules[module_id]["content_hash"] != current_modules[module_id]["content_hash"]:
            changes.append(f"module '{module_id}'")
        elif stored_modules[module_id]["version"] != current_modules[module_id]["version"]:
            changes.append(f"module '{module_id}' version")
    return changes


def write_lock(view: View, plan: CompiledViewPlan) -> Path:
    """Write the adjacent lock for one validated view and return its path."""
    path = lock_path_for(view.path)
    document = {
        "schema": LOCK_SCHEMA,
        "view": view.relative_path,
        "name": view.name,
        "fingerprint": plan.fingerprint(),
        "dependencies": dict(plan.provenance),
    }
    path.write_text(
        yaml.safe_dump(document, sort_keys=True, allow_unicode=True),
        encoding="utf-8",
        newline="\n",
    )
    return path


def validate_view(
    canon: Canon,
    view: View,
    *,
    index: ModuleIndex | None = None,
    write_lock_file: bool = False,
) -> ValidationResult:
    """Compile, project, and check one named view without rendering HTML."""
    result = ValidationResult(view_path=view.relative_path, view_name=view.name, ok=False)

    if index is None:
        index = load_module_index(canon.root)

    try:
        plan = compile_view(canon, view, index=index)
    except (CompileError, ModuleError) as exc:
        result.errors.append(_entry("compose.invalid", str(exc)))
        return result

    result.plan = plan
    result.fingerprint = plan.fingerprint()
    result.style_rules = _style_rule_records(canon, plan)
    result.warnings.extend(_style_rule_warnings(view, result.style_rules))

    for item in plan.diagnostics:
        record = _entry(item.code, item.message, **dict(item.detail))
        (result.errors if item.severity == "error" else result.warnings).append(record)

    findings: list[dict[str, Any]] = []
    projection = project_view(canon, view, plan=plan, findings=findings)
    result.projection = projection
    result.counts = {"nodes": len(projection["nodes"]), "edges": len(projection["edges"])}

    for finding in findings:
        record = _entry(finding["code"], finding["message"])
        # Losing an endpoint to the selector is routine filtering for a legacy
        # view and for a relation admitted by the implicit default. But an
        # explicit include is a decision to draw that relationship, and
        # endpoint completion has already supplied every renderable endpoint
        # for it, so one still not whole is a real defect.
        explicit_incompleteness = (
            finding["code"] == "structure.relation-not-whole"
            and finding.get("relation") in plan.explicit_relation_ids
        )
        if finding["code"] in STRUCTURAL_ERRORS or explicit_incompleteness:
            result.errors.append(record)
        else:
            result.warnings.append(record)

    _validate_assertions(view, plan, projection, canon, result.errors)

    stored = read_lock(view)
    if stored is None:
        result.lock_state = "absent"
    elif stored.get("fingerprint") == result.fingerprint:
        result.lock_state = "current"
    else:
        result.lock_state = "stale"
        result.lock_changes = _lock_changes(
            stored.get("dependencies") or {}, plan.provenance
        ) or ["recorded fingerprint no longer matches"]

    result.ok = not result.errors

    if write_lock_file:
        if not result.ok:
            # A fallback or a failed check must never produce a valid lock.
            result.warnings.append(
                _entry(
                    "lock.refused",
                    f"{view.relative_path}: lock not written because validation failed",
                )
            )
        else:
            write_lock(view, plan)
            result.lock_state = "written"
            result.lock_changes = []

    return result
