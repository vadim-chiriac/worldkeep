"""Deterministic structural reporting for a successful ``wb capture``.

This module deliberately reads only frontmatter.  It reports what the writer
put on disk; it does not decide whether any classification is semantically
correct.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable

from .context import CanonReader
from .delegate import CaptureBundle


REPORT_SCHEMA = "wb.capture-report/v1"


@dataclass(frozen=True)
class ArtifactState:
    kind: str
    type: str


def snapshot(reader: CanonReader, artifact_ids: Iterable[str]) -> dict[str, ArtifactState]:
    """Read the submitted IDs only, so unrelated canon changes never leak in."""
    by_id = reader.by_id()
    return {
        artifact_id: ArtifactState(
            kind=(by_id[artifact_id][2].get("kind") or ""),
            type=(by_id[artifact_id][2].get("type") or ""),
        )
        for artifact_id in artifact_ids
        if artifact_id in by_id
    }


def build_report(
    before: dict[str, ArtifactState],
    after: dict[str, ArtifactState],
    bundles: tuple[CaptureBundle, ...] | None,
    post_frontmatter: dict[str, dict[str, Any]],
    canon_frontmatter: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Produce a stable, compact report from pre- and post-write state."""
    artifact_ids = sorted(after)
    grouped: dict[tuple[str, str], Counter[str]] = {}
    for artifact_id in artifact_ids:
        state = after[artifact_id]
        counts = grouped.setdefault((state.kind, state.type), Counter())
        counts["updated" if artifact_id in before else "created"] += 1

    by_kind_type = [
        {
            "kind": kind,
            "type": artifact_type,
            "created": counts["created"],
            "updated": counts["updated"],
        }
        for (kind, artifact_type), counts in sorted(grouped.items())
    ]
    relations = [
        _relation_shape(artifact_id, post_frontmatter[artifact_id])
        for artifact_id in artifact_ids
        if after[artifact_id].kind == "relation"
    ]
    reclassified = [
        {
            "id": artifact_id,
            "before": {"kind": before[artifact_id].kind, "type": before[artifact_id].type},
            "after": {"kind": after[artifact_id].kind, "type": after[artifact_id].type},
        }
        for artifact_id in artifact_ids
        if artifact_id in before and before[artifact_id] != after[artifact_id]
    ]
    return {
        "schema": REPORT_SCHEMA,
        "artifacts": {
            "written": len(artifact_ids),
            "created": sum(artifact_id not in before for artifact_id in artifact_ids),
            "updated": sum(artifact_id in before for artifact_id in artifact_ids),
            "by_kind_type": by_kind_type,
        },
        "bundles": (
            [
                {
                    "id": bundle.id,
                    "headline": bundle.headline,
                    "artifacts": len(bundle.artifact_ids),
                }
                for bundle in bundles
            ]
            if bundles is not None
            else []
        ),
        "new_type_ids": [
            artifact_id
            for artifact_id in artifact_ids
            if artifact_id not in before and after[artifact_id].kind == "type"
        ],
        "unlinked_created_ids": _unlinked_created_ids(
            before, after, canon_frontmatter
        ),
        "relations": relations,
        "reclassified": reclassified,
    }


def _unlinked_created_ids(
    before: dict[str, ArtifactState],
    after: dict[str, ArtifactState],
    canon_frontmatter: dict[str, dict[str, Any]],
) -> list[str]:
    """New non-structural artifacts that are not members of any relation.

    This is deliberately a non-failing observation.  Standalone artifacts are
    valid canon, but newly captured ones are worth reviewing before approval.
    The whole post-write canon is considered so an existing or updated relation
    can connect a newly created artifact too.
    """
    connected: set[str] = set()
    for frontmatter in canon_frontmatter.values():
        if (frontmatter.get("kind") or "") != "relation":
            continue
        members = frontmatter.get("members") or []
        if not isinstance(members, list):
            continue
        for member in members:
            if isinstance(member, dict) and isinstance(member.get("id"), str):
                connected.add(member["id"])

    return [
        artifact_id
        for artifact_id in sorted(after)
        if artifact_id not in before
        and after[artifact_id].kind not in {"relation", "type"}
        and artifact_id not in connected
    ]


def _relation_shape(artifact_id: str, frontmatter: dict[str, Any]) -> dict[str, Any]:
    members = frontmatter.get("members") or []
    roles: Counter[str] = Counter()
    if isinstance(members, list):
        for member in members:
            if isinstance(member, dict) and isinstance(member.get("role"), str):
                roles[member["role"]] += 1
    return {
        "id": artifact_id,
        "type": frontmatter.get("type") or "",
        "members": len(members) if isinstance(members, list) else 0,
        "roles": dict(sorted(roles.items())),
    }


def format_report(report: dict[str, Any]) -> str:
    """Human form mirrors the JSON report without exposing per-file plumbing."""
    artifacts = report["artifacts"]
    lines = [
        "Capture structure: "
        f"{artifacts['written']} written ({artifacts['created']} new, {artifacts['updated']} updated)"
    ]
    for group in artifacts["by_kind_type"]:
        label = group["kind"] + (f"/{group['type']}" if group["type"] else "")
        portions = []
        if group["created"]:
            portions.append(f"{group['created']} new")
        if group["updated"]:
            portions.append(f"{group['updated']} updated")
        lines.append(f"  {label}: {', '.join(portions)}")
    if report["bundles"]:
        lines.append(
            "Bundles: "
            + "; ".join(f"{bundle['id']} {bundle['artifacts']}" for bundle in report["bundles"])
        )
    lines.append(
        "New type IDs: " + (", ".join(report["new_type_ids"]) or "none")
    )
    if report["unlinked_created_ids"]:
        lines.append(
            "Notice (non-blocking): newly created artifacts without a relation: "
            + ", ".join(report["unlinked_created_ids"])
            + ". Review before approval; standalone artifacts may be intentional."
        )
    if report["relations"]:
        relation_parts = []
        for relation in report["relations"]:
            roles = ", ".join(
                f"{role} {count}" for role, count in relation["roles"].items()
            )
            detail = f"{relation['members']} members" + (f": {roles}" if roles else "")
            typed = f"{relation['type']}; " if relation["type"] else ""
            relation_parts.append(f"{relation['id']} [{typed}{detail}]")
        lines.append("Relations: " + "; ".join(relation_parts))
    else:
        lines.append("Relations: none")
    if report["reclassified"]:
        lines.append(
            "Reclassified: "
            + "; ".join(
                f"{item['id']} [{item['before']['kind']}/{item['before']['type']} -> "
                f"{item['after']['kind']}/{item['after']['type']}]"
                for item in report["reclassified"]
            )
        )
    else:
        lines.append("Reclassified: none")
    return "\n".join(lines) + "\n"
