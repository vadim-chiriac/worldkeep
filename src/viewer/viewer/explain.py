"""Explain why one artifact or relation ended up the way it did.

Explanation reads a finished :class:`~viewer.compile.CompiledViewPlan` and the
projection it produced. It never recompiles or reinterprets anything, so a
trace always describes the same run the user is looking at.
"""

from __future__ import annotations

from typing import Any, Mapping

from .compile import CompiledViewPlan
from .load import Canon


def explain_artifact(
    canon: Canon,
    plan: CompiledViewPlan,
    projection: Mapping[str, Any],
    artifact_id: str,
) -> dict[str, Any]:
    """Return a stable JSON-shaped trace for one artifact or relation."""
    artifact = canon.artifacts.get(artifact_id)
    trace: dict[str, Any] = {
        "artifact": artifact_id,
        "view": plan.view_name,
        "known": artifact is not None,
    }
    if artifact is None:
        trace["reason"] = "no artifact with this id exists in the canon"
        return trace

    trace["kind"] = artifact.kind
    trace["type"] = artifact.type
    trace["path"] = artifact.relative_path

    trace["selection"] = _selection_trace(plan, artifact_id)
    trace["relation_policy"] = _relation_trace(plan, artifact)
    trace["style"] = _property_trace(plan.style_overrides.get(artifact_id, {}), plan, artifact_id)
    trace["lens"] = _property_trace(plan.lens_overrides.get(artifact_id, {}), plan, artifact_id)
    trace["projection"] = _projection_trace(projection, artifact_id)
    trace["diagnostics"] = [
        item.as_json()
        for item in plan.diagnostics
        if item.detail.get("artifact") == artifact_id
        or item.detail.get("relation") == artifact_id
        or artifact_id in item.detail.get("artifacts", ())
    ]
    trace["fallback"] = any(
        item["code"] == "lens.structural-conflict" for item in trace["diagnostics"]
    )
    return trace


def _selection_trace(plan: CompiledViewPlan, artifact_id: str) -> dict[str, Any]:
    """Separate what the recipe chose from what the projection had to draw."""
    sources = plan.selection_sources
    contributing = {
        role: sorted(
            module_id
            for module_id, chosen in modules.items()
            if artifact_id in chosen
        )
        for role, modules in sources.items()
    }
    is_relation = artifact_id in plan.relation_ids
    selected = artifact_id in plan.semantic_base_ids or is_relation
    completed = artifact_id in plan.endpoint_completions
    displayed = artifact_id in plan.base_ids or is_relation

    detail: dict[str, Any] = {
        "included": selected,
        "displayed": displayed,
        "endpoint_completion": completed,
        "any_of": contributing.get("any_of", []),
        "all_of": contributing.get("all_of", []),
        "excluded_by": contributing.get("exclude", []),
    }
    if plan.anchor is not None:
        detail["anchor"] = {
            "policy": plan.anchor.describe(),
            "sources": list(plan.anchor.sources),
        }

    if selected:
        detail["semantic_outcome"] = "selected"
    elif detail["excluded_by"]:
        detail["semantic_outcome"] = (
            "excluded by compose.selection.exclude: "
            + ", ".join(detail["excluded_by"])
        )
    else:
        detail["semantic_outcome"] = "not selected"

    if not plan.composed:
        detail["path"] = "legacy view-local select (no compose block)"
        if not selected:
            detail["reason"] = "not chosen by the view-local select"
        return detail

    if completed:
        detail["reason"] = (
            f"{detail['semantic_outcome']}, but displayed only because an "
            "independently selected relation requires it; projection completion "
            "is not selection resurrection"
        )
    elif detail["excluded_by"]:
        detail["reason"] = (
            "removed by compose.selection.exclude; nothing later can resurrect it"
        )
    elif not selected:
        detail["reason"] = (
            "not chosen by any_of/all_of, or narrowed away by the view-local select"
        )
    return detail


def _relation_trace(plan: CompiledViewPlan, artifact) -> dict[str, Any] | None:
    if artifact.kind != "relation":
        return None
    policy = plan.relation_policy
    explicit = artifact.id in plan.explicit_relation_ids
    detail = {
        "included": artifact.id in plan.relation_ids,
        "explicit": explicit,
        "composed_include": list(policy.get("composed_include", ())),
        "local_include": (
            list(policy["local_include"]) if policy.get("local_include") is not None else None
        ),
        "exclude": list(policy.get("exclude", ())),
    }
    if detail["included"]:
        detail["admitted_by"] = (
            "an explicit relation include, so it is independent of artifact "
            "selection and may complete its endpoints"
            if explicit
            else "the implicit default: induced from the selected artifacts, so "
            "it never adds endpoints of its own"
        )
    return detail


def _property_trace(
    values: Mapping[str, Any],
    plan: CompiledViewPlan,
    artifact_id: str,
) -> dict[str, Any]:
    sources = plan.property_sources.get(artifact_id, {})
    return {
        prop: {"value": value, "source": sources.get(prop, "resolved lens or viewer default")}
        for prop, value in sorted(values.items())
    }


def _projection_trace(projection: Mapping[str, Any], artifact_id: str) -> dict[str, Any]:
    node = next(
        (item for item in projection.get("nodes", ()) if item["id"] == artifact_id), None
    )
    edges = [
        item
        for item in projection.get("edges", ())
        if item["id"] == artifact_id or item["id"].startswith(f"{artifact_id}::member:")
    ]
    detail: dict[str, Any] = {
        "is_node": node is not None,
        "edge_count": len(edges),
    }
    if node is not None:
        detail["parent"] = node.get("parent")
        detail["style"] = node.get("style")
        detail["reified"] = node.get("kind") == "relation"
        if detail["reified"]:
            detail["reification_reason"] = (
                "shown as an inspectable node because it is targeted by another "
                "relation, is not binary, or cannot be represented whole"
            )
    if edges:
        detail["behaviors"] = sorted({edge["behavior"] for edge in edges})
        detail["directed"] = sorted({edge["directed"] for edge in edges})
    return detail


def format_explanation(trace: Mapping[str, Any]) -> str:
    """Render one trace as readable text."""
    lines: list[str] = []
    lines.append(f"artifact: {trace['artifact']}")
    if not trace.get("known"):
        lines.append(f"  {trace.get('reason', 'unknown artifact')}")
        return "\n".join(lines) + "\n"

    lines.append(f"view: {trace['view']}")
    lines.append(f"kind/type: {trace.get('kind')} / {trace.get('type')}")

    selection = trace["selection"]
    lines.append("")
    lines.append("selection:")
    lines.append(f"  semantically selected: {'yes' if selection['included'] else 'no'}")
    lines.append(f"  shown in the projection: {'yes' if selection.get('displayed') else 'no'}")
    if selection.get("semantic_outcome"):
        lines.append(f"  selection outcome: {selection['semantic_outcome']}")
    for label, key in (
        ("matched any_of module(s)", "any_of"),
        ("matched all_of module(s)", "all_of"),
        ("excluded by module(s)", "excluded_by"),
    ):
        if selection.get(key):
            lines.append(f"  {label}: {', '.join(selection[key])}")
    if selection.get("anchor"):
        lines.append(f"  anchor policy: {selection['anchor']['policy']}")
        lines.append(f"    declared by: {', '.join(selection['anchor']['sources'])}")
    if selection.get("endpoint_completion"):
        lines.append("  endpoint completion: kept only to leave a selected relation whole")
    if selection.get("reason"):
        lines.append(f"  reason: {selection['reason']}")
    if selection.get("path"):
        lines.append(f"  path: {selection['path']}")

    relation = trace.get("relation_policy")
    if relation is not None:
        lines.append("")
        lines.append("relation policy:")
        lines.append(f"  included: {'yes' if relation['included'] else 'no'}")
        if relation.get("admitted_by"):
            lines.append(f"  admitted by: {relation['admitted_by']}")
        if relation["composed_include"]:
            lines.append(f"  composed include: {', '.join(relation['composed_include'])}")
        if relation["local_include"] is not None:
            lines.append(f"  local include: {', '.join(relation['local_include'])}")
        if relation["exclude"]:
            lines.append(f"  exclude: {', '.join(relation['exclude'])}")

    for label, key in (("lens", "lens"), ("style", "style")):
        entries = trace.get(key) or {}
        if entries:
            lines.append("")
            lines.append(f"{label}:")
            for prop, detail in entries.items():
                lines.append(f"  {prop} = {detail['value']!r}  <- {detail['source']}")

    projection = trace["projection"]
    lines.append("")
    lines.append("projection:")
    lines.append(f"  drawn as node: {'yes' if projection['is_node'] else 'no'}")
    if projection.get("parent"):
        lines.append(f"  nest parent: {projection['parent']}")
    if projection.get("reification_reason"):
        lines.append(f"  reified: {projection['reification_reason']}")
    if projection.get("edge_count"):
        lines.append(f"  edges: {projection['edge_count']} ({', '.join(projection.get('behaviors', []))})")

    if trace["diagnostics"]:
        lines.append("")
        lines.append("diagnostics:")
        for item in trace["diagnostics"]:
            lines.append(f"  [{item['severity']}] {item['message']}")
    if trace.get("fallback"):
        lines.append("")
        lines.append("this artifact is rendered through an UNVALIDATED FALLBACK")

    return "\n".join(lines) + "\n"
