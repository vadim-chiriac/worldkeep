"""Project loaded canon artifacts into the stable Viewer v0 JSON contract."""

from __future__ import annotations

from fnmatch import fnmatchcase
from typing import Any, Iterable, Mapping

from .load import Artifact, Canon, ProjectionPolicy, View


# Actions used to be a kind and got a hexagon from here. They are a type now,
# and `types/action` declares its own shape and colour, which is where a
# world-specific visual belongs.
KIND_SHAPES = {
    "entity": "roundrectangle",
    "idea": "ellipse",
    "relation": "diamond",
}
VALENCE_COLORS = {
    "positive": "#78a96b",
    "negative": "#c86b6b",
    "neutral": "#999999",
    "ambivalent": "#a884c6",
}
LENS_KEYS = {
    "as",
    "collapse_default",
    "color",
    "direction",
    "label",
    "line",
    "shape",
    "width",
}
BEHAVIORS = {"edge", "nest", "chip", "hide"}
STD_LENSES: dict[str, dict[str, Any]] = {
    # Custom views retain containment nesting, so this direction is visible
    # only where the relation is explicitly rendered (notably Everything).
    "part_of": {"as": "nest", "direction": ["part", "whole"]},
    "part_of/membership": {"as": "edge", "direction": ["part", "whole"]},
    "subordinate_to": {"as": "edge", "direction": ["subordinate", "superior"]},
    "holds": {"as": "edge", "width": "weight", "direction": ["holder", "held"]},
    "opposes": {"as": "edge", "color": "#c86b6b"},
    "participates": {"as": "edge"},
    "state": {"as": "chip"},
    "precedes": {"as": "hide", "direction": ["earlier", "later"]},
}


def _warn(warnings: list[str], message: str) -> None:
    if message not in warnings:
        warnings.append(message)


def _mapping(
    value: Any,
    *,
    field: str,
    warnings: list[str],
) -> Mapping[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    _warn(warnings, f"view: '{field}' must be a mapping; using defaults")
    return {}


def _string_list(
    value: Any,
    *,
    field: str,
    warnings: list[str],
) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    _warn(warnings, f"view: '{field}' must be a list of strings; using defaults")
    return None


def _type_ancestors(type_path: str | None) -> Iterable[str]:
    if not type_path:
        return ()
    parts = type_path.split("/")
    return ("/".join(parts[:size]) for size in range(len(parts), 0, -1))


def _type_matches(type_path: str | None, patterns: list[str] | None) -> bool:
    if patterns is None or not patterns:
        return True
    if type_path is None:
        return any(pattern in {"*", "<untyped>"} for pattern in patterns)
    return any(fnmatchcase(type_path, pattern) for pattern in patterns)


def _artifact_status(artifact: Artifact) -> str:
    status = artifact.frontmatter.get("status", "canon")
    return status if isinstance(status, str) else "canon"


def _roles_and_members(artifact: Artifact) -> list[tuple[str, str | None]]:
    raw_members = artifact.frontmatter.get("members")
    if not isinstance(raw_members, list):
        return []
    members: list[tuple[str, str | None]] = []
    for member in raw_members:
        if isinstance(member, str):
            members.append((member, None))
        elif isinstance(member, dict) and isinstance(member.get("id"), str):
            role = member.get("role")
            members.append((member["id"], role if isinstance(role, str) else None))
    return members


def _canon_nest_lens(canon_lens: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """Return the lens only if the canon itself declares this a containment.

    Containment is a structural claim about the world, so only the world may
    make it. A view module may still flip `as` to `nest` for some other
    relation — that keeps working — but it does not get to reinterpret that
    relation's role names as inside/outside. Letting it would put the shape of
    the graph in the hands of whoever drew it, which is precisely why KERNEL
    v0.13 removed the renderer-dependent `group` behavior.
    """
    return canon_lens if canon_lens.get("as") == "nest" else None


def _nest_roles(lens: Mapping[str, Any] | None) -> tuple[str, str]:
    """Return the (contained, container) role names a nest lens declares.

    A nest needs to know which member is inside which. The lens already carries
    that as `direction`, in the same [source, target] form edges use — for
    containment the source is the contained member and the target is the
    container, which is why the standard `part_of` lens declares
    ["part", "whole"].

    Reading it here is what lets a world nest by its own vocabulary: a
    `seat_of` declaring `as: nest` with `direction: [seat, territory]` nests
    seats inside territories. The default keeps every canon written before this
    unchanged.
    """
    if lens is not None:
        declared = _direction(lens.get("direction"))
        if declared is not None:
            return declared
    return "part", "whole"


def _nest_parts_and_whole(
    members: list[tuple[str, str | None]],
    lens: Mapping[str, Any] | None = None,
) -> tuple[list[tuple[int, str]], str] | None:
    """Return indexed parts and one whole for a valid containment statement."""
    part_role, whole_role = _nest_roles(lens)
    parts = [
        (index, member_id)
        for index, (member_id, role) in enumerate(members, start=1)
        if role == part_role
    ]
    wholes = [member_id for member_id, role in members if role == whole_role]
    if not parts or len(wholes) != 1:
        return None
    return parts, wholes[0]


def _direction(value: Any) -> tuple[str, str] | None:
    """Return a valid [source_role, target_role] lens declaration."""
    if (
        isinstance(value, list)
        and len(value) == 2
        and all(isinstance(role, str) and role for role in value)
        and value[0] != value[1]
    ):
        return value[0], value[1]
    return None


def _entertained_ideas(canon: Canon, held: set[str]) -> set[str]:
    """Widen the held set to ideas held only as part of a larger doctrine.

    `dormant` means nobody in the world entertains this — an unread book. A
    verse of a creed somebody holds is not that: the doctrine is in somebody's
    head, and the verse came with it. Holding a whole still does not commit a
    holder to every part, which is why a sect can hold turn three and reject
    turn five (§7); this only decides whether the concept is live at all.
    """
    wholes: dict[str, set[str]] = {}
    for artifact in canon.artifacts.values():
        if artifact.kind != "relation" or not artifact.type:
            continue
        if not any(ancestor == "part_of" for ancestor in _type_ancestors(artifact.type)):
            continue
        members = _roles_and_members(artifact)
        containers = {member_id for member_id, role in members if role == "whole"}
        for member_id, role in members:
            if role == "part":
                wholes.setdefault(member_id, set()).update(containers)

    entertained = set(held)
    for artifact in canon.artifacts.values():
        if artifact.kind != "idea" or artifact.id in entertained:
            continue
        seen: set[str] = set()
        frontier = set(wholes.get(artifact.id, ()))
        while frontier:
            current = frontier.pop()
            if current in seen:
                continue
            seen.add(current)
            if current in held:
                entertained.add(artifact.id)
                break
            frontier |= wholes.get(current, set())
    return entertained


def _part_of_parents(canon: Canon, warnings: list[str]) -> dict[str, set[str]]:
    parents: dict[str, set[str]] = {}
    for artifact in canon.artifacts.values():
        if artifact.kind != "relation":
            continue
        lens = _resolve_lens(artifact, canon, warnings)
        if lens.get("as") != "nest":
            continue
        containment = _nest_parts_and_whole(_roles_and_members(artifact), lens)
        if containment is None:
            continue
        parts, whole = containment
        for _, part in parts:
            parents.setdefault(part, set()).add(whole)
    return parents


def _descendants(root_id: str, parents: Mapping[str, set[str]]) -> set[str]:
    result = {root_id}
    changed = True
    while changed:
        changed = False
        for child, possible_parents in parents.items():
            if possible_parents.intersection(result) and child not in result:
                result.add(child)
                changed = True
    return result


def _passes_scope_filters(
    artifact: Artifact,
    *,
    select: Mapping[str, Any],
    allowed_statuses: list[str],
    allowed_places: set[str] | None,
    warnings: list[str],
) -> bool:
    if _artifact_status(artifact) not in allowed_statuses:
        return False

    tags = _string_list(select.get("tags"), field="select.tags", warnings=warnings)
    if tags:
        artifact_tags = artifact.frontmatter.get("tags")
        if not isinstance(artifact_tags, list) or not set(tags).intersection(artifact_tags):
            return False

    if allowed_places is not None:
        anchors = artifact.frontmatter.get("where")
        if isinstance(anchors, str):
            anchors = [anchors]
        if artifact.id not in allowed_places and not (
            isinstance(anchors, list) and any(anchor in allowed_places for anchor in anchors)
        ):
            return False

    when_range = select.get("when_range")
    if when_range is not None:
        if not isinstance(when_range, dict):
            _warn(warnings, "view: 'select.when_range' must be a mapping; ignored")
        else:
            when = artifact.frontmatter.get("when")
            sort_value = when.get("sort") if isinstance(when, dict) else None
            if not isinstance(sort_value, (int, float)):
                return False
            start = when_range.get("from")
            end = when_range.get("to")
            if isinstance(start, (int, float)) and sort_value < start:
                return False
            if isinstance(end, (int, float)) and sort_value > end:
                return False

    return True


def _resolve_lens(artifact: Artifact, canon: Canon, warnings: list[str]) -> dict[str, Any]:
    lens: dict[str, Any] = {"as": "edge"} if artifact.kind == "relation" else {}

    direction_path: str | None = None
    for ancestor in _type_ancestors(artifact.type):
        if ancestor in STD_LENSES:
            lens.update(STD_LENSES[ancestor])
            break

    found_definition = canon.resolve_type(artifact.type)
    for ancestor in _type_ancestors(artifact.type):
        type_artifact = canon.types.get(ancestor)
        if type_artifact is None:
            continue
        candidate = type_artifact.frontmatter.get("lens")
        if candidate is None:
            continue
        if not isinstance(candidate, dict):
            _warn(warnings, f"{type_artifact.relative_path}: lens is not a mapping; ignored")
            break
        for key in candidate:
            if key not in LENS_KEYS:
                _warn(warnings, f"{type_artifact.relative_path}: unknown lens key '{key}'")
        lens.update({key: value for key, value in candidate.items() if key in LENS_KEYS})
        if "direction" in candidate:
            direction_path = type_artifact.relative_path
        break

    if artifact.type and found_definition is None:
        fallback = "built-in lens" if any(
            ancestor in STD_LENSES for ancestor in _type_ancestors(artifact.type)
        ) else "kind default"
        _warn(
            warnings,
            f"{artifact.relative_path}: type '{artifact.type}' is undefined; using {fallback}",
        )

    behavior = lens.get("as", "edge")
    if behavior not in BEHAVIORS:
        _warn(
            warnings,
            f"{artifact.relative_path}: unknown lens behavior '{behavior}'; using edge",
        )
        lens["as"] = "edge"
    if "direction" in lens and _direction(lens["direction"]) is None:
        _warn(
            warnings,
            f"{direction_path or artifact.relative_path}: lens.direction must be [source_role, target_role]; ignored",
        )
        lens.pop("direction")
    return lens


def _facet_color(artifact: Artifact, facet: Any) -> str | None:
    if facet == "valence":
        value = artifact.frontmatter.get("valence")
        return VALENCE_COLORS.get(value) if isinstance(value, str) else None
    if isinstance(facet, str) and facet.startswith("#"):
        return facet
    return None


def _label(artifact: Artifact, lens: Mapping[str, Any]) -> str:
    field = lens.get("label", "name")
    if field == "none":
        return ""
    if field == "name":
        return artifact.name
    if isinstance(field, str):
        value = artifact.frontmatter.get(field)
        if value is not None:
            return str(value)
    return artifact.name


def _weight_width(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 2.0
    bounded = min(1.0, max(0.0, float(value)))
    return round(1.0 + bounded * 4.0, 3)


def _style(
    artifact: Artifact,
    lens: Mapping[str, Any],
    emphasis: Mapping[str, Any],
    *,
    node: bool,
) -> dict[str, Any]:
    explicit_color = _facet_color(artifact, lens.get("color"))
    emphasis_color = _facet_color(artifact, emphasis.get("color_by"))
    color = explicit_color or emphasis_color
    if node:
        opacity = 1.0
        status = _artifact_status(artifact)
        if status == "draft":
            opacity = 0.5
        elif status == "deprecated":
            opacity = 0.3
        shape = lens.get("shape")
        if not isinstance(shape, str):
            shape = KIND_SHAPES.get(artifact.kind or "", "roundrectangle")
        return {"shape": shape, "color": color, "opacity": opacity}

    width_rule = lens.get("width")
    if isinstance(width_rule, (int, float)) and not isinstance(width_rule, bool):
        width = float(width_rule)
    elif width_rule == "weight" or emphasis.get("size_by") == "weight":
        width = _weight_width(artifact.frontmatter.get("weight"))
    else:
        width = 2.0
    line = lens.get("line") if isinstance(lens.get("line"), str) else "solid"
    return {"width": width, "color": color or "#999999", "line": line}


def _node(
    artifact: Artifact,
    canon: Canon,
    emphasis: Mapping[str, Any],
    warnings: list[str],
    *,
    held_ideas: set[str],
    overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    lens = _resolve_lens(artifact, canon, warnings)
    if overrides:
        lens.update(overrides)
    badges: list[str] = []
    if artifact.frontmatter.get("fiat") is True:
        badges.append("fiat")
    if artifact.kind == "idea" and artifact.id not in held_ideas:
        badges.append("dormant")
    # A practice is now a type path rather than a kind plus a type, so the
    # badge follows the path: `action/practice` and anything beneath it.
    if artifact.type and any(
        ancestor == "action/practice" for ancestor in _type_ancestors(artifact.type)
    ):
        badges.append("practice")
    return {
        "id": artifact.id,
        "kind": artifact.kind,
        "type": artifact.type,
        "label": _label(artifact, lens),
        "parent": None,
        "style": _style(artifact, lens, emphasis, node=True),
        "badges": badges,
        "chips": [],
    }


def _relation_edge(
    artifact: Artifact,
    *,
    edge_id: str,
    source: str,
    target: str,
    source_role: str | None,
    target_role: str | None,
    directed: bool,
    behavior: str,
    lens: Mapping[str, Any],
    emphasis: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "id": edge_id,
        "type": artifact.type,
        "source": source,
        "target": target,
        "directed": directed,
        "behavior": behavior,
        "roles": {"source": source_role, "target": target_role},
        "style": _style(artifact, lens, emphasis, node=False),
    }


def _binary_direction(
    members: list[tuple[str, str | None]],
    direction: tuple[str, str] | None,
) -> tuple[tuple[str, str | None], tuple[str, str | None]] | None:
    if direction is None:
        return None
    source_role, target_role = direction
    sources = [member for member in members if member[1] == source_role]
    targets = [member for member in members if member[1] == target_role]
    if len(sources) == len(targets) == 1:
        return sources[0], targets[0]
    return None


def _would_cycle(child: str, parent: str, parents: Mapping[str, str]) -> bool:
    cursor = parent
    visited = {child}
    while cursor in parents:
        if cursor in visited:
            return True
        visited.add(cursor)
        cursor = parents[cursor]
    return cursor in visited


def _audit_style(artifact: Artifact, *, node: bool) -> dict[str, Any]:
    """Neutral viewer-owned marks. This deliberately reads no lens or emphasis."""
    if node:
        return {
            "shape": KIND_SHAPES.get(artifact.kind or "", "roundrectangle"),
            "color": None,
            "opacity": 0.5 if _artifact_status(artifact) == "draft" else 1.0,
        }
    return {"width": 2.0, "color": "#999999", "line": "solid"}


def _audit_node(artifact: Artifact, held_ideas: set[str]) -> dict[str, Any]:
    badges: list[str] = []
    if artifact.frontmatter.get("fiat") is True:
        badges.append("fiat")
    if artifact.kind == "idea" and artifact.id not in held_ideas:
        badges.append("dormant")
    # A practice is now a type path rather than a kind plus a type, so the
    # badge follows the path: `action/practice` and anything beneath it.
    if artifact.type and any(
        ancestor == "action/practice" for ancestor in _type_ancestors(artifact.type)
    ):
        badges.append("practice")
    return {
        "id": artifact.id, "kind": artifact.kind, "type": artifact.type,
        "label": artifact.name, "parent": None, "style": _audit_style(artifact, node=True),
        "badges": badges, "chips": [],
    }


def _audit_direction(artifact: Artifact) -> tuple[str, str] | None:
    """Only viewer-owned standard directions are allowed in the audit graph."""
    for ancestor in _type_ancestors(artifact.type):
        standard = STD_LENSES.get(ancestor)
        if standard is not None:
            return _direction(standard.get("direction"))
    return None


def _project_audit_general(canon: Canon, view: View) -> dict[str, Any]:
    """Project the full active world graph without consuming user presentation rules."""
    warnings = [*canon.warnings, *view.warnings]
    active = {
        artifact_id: artifact for artifact_id, artifact in canon.artifacts.items()
        if artifact.kind != "type" and _artifact_status(artifact) in {"canon", "draft"}
    }
    held_ideas = {
        member_id for relation in active.values()
        if relation.kind == "relation" and relation.type
        and any(ancestor == "holds" for ancestor in _type_ancestors(relation.type))
        for member_id, role in _roles_and_members(relation) if role == "held"
    }
    held_ideas = _entertained_ideas(canon, held_ideas)
    nodes = {
        artifact_id: _audit_node(artifact, held_ideas)
        for artifact_id, artifact in active.items() if artifact.kind != "relation"
    }
    relations = [artifact for artifact in active.values() if artifact.kind == "relation"]
    relation_ids = {artifact.id for artifact in relations}
    authored_members = {relation.id: _roles_and_members(relation) for relation in relations}
    targeted_relations = {
        member_id for members in authored_members.values()
        for member_id, _ in members if member_id in relation_ids
    }
    reified: set[str] = set()
    for relation in relations:
        members = authored_members[relation.id]
        active_members = [member for member in members if member[0] in active]
        direction = _audit_direction(relation)
        # Use authored cardinality, not only surviving endpoints. Otherwise a
        # formerly n-ary statement could become a misleading binary edge.
        if (
            len(members) != 2
            or len(active_members) != len(members)
            or relation.id in targeted_relations
            or any(member_id in relation_ids for member_id, _ in members)
            or (direction is not None and _binary_direction(active_members, direction) is None)
        ):
            reified.add(relation.id)
    edges: list[dict[str, Any]] = []
    for relation in relations:
        authored = authored_members[relation.id]
        members = [member for member in authored if member[0] in active]
        skipped = [member_id for member_id, _ in authored if member_id not in active]
        if skipped:
            _warn(warnings, f"{relation.relative_path}: inactive or missing member(s) {skipped}; omitted from audit relation")
        # Relations are generic edges only when exactly two ordinary active endpoints
        # form one safe binary statement. Every other shape stays inspectable.
        if relation.id in reified:
            nodes[relation.id] = _audit_node(relation, held_ideas)
            direction = _audit_direction(relation)
            if len(authored) == 2 and direction is not None and _binary_direction(members, direction) is None:
                _warn(warnings, f"{relation.relative_path}: standard direction {direction[0]} -> {direction[1]} cannot be resolved unambiguously; reified with undirected spokes")
            resolved = direction is not None and any(role == direction[0] for _, role in members) and any(role == direction[1] for _, role in members)
            for index, (member_id, role) in enumerate(members, start=1):
                if resolved and role == direction[0]:
                    source, target, source_role, target_role, directed = member_id, relation.id, role, "relation", True
                elif resolved and role == direction[1]:
                    source, target, source_role, target_role, directed = relation.id, member_id, "relation", role, True
                else:
                    source, target, source_role, target_role, directed = relation.id, member_id, "relation", role, False
                edges.append(_relation_edge(relation, edge_id=f"{relation.id}::member:{index}", source=source, target=target, source_role=source_role, target_role=target_role, directed=directed, behavior="edge", lens={}, emphasis={}))
            continue
        direction = _audit_direction(relation)
        oriented = _binary_direction(members, direction)
        source, target = oriented or (members[0], members[1])
        edges.append(_relation_edge(relation, edge_id=relation.id, source=source[0], target=target[0], source_role=source[1], target_role=target[1], directed=oriented is not None, behavior="edge", lens={}, emphasis={}))
    # _relation_edge calls the ordinary style function; overwrite it to keep this
    # policy immune to current and future lens/emphasis fields.
    for edge in edges:
        edge["style"] = {"width": 2.0, "color": "#999999", "line": "solid"}
    return {
        "view": {"name": view.name, "layout": "fcose", "render": view.render},
        "nodes": list(nodes.values()), "edges": edges,
        "warnings": list(dict.fromkeys(warnings)),
    }


def select_candidates(
    canon: Canon,
    select: Mapping[str, Any],
    edges_config: Mapping[str, Any],
    *,
    warnings: list[str],
) -> tuple[dict[str, Artifact], dict[str, Artifact]]:
    """Return the base artifacts and relation candidates one selector chooses.

    This is the single selection evaluator. ``project_view`` uses it for a
    view-local ``select``; the composition compiler uses it to evaluate each
    selection module independently against the same canon. Anchor expansion is
    deliberately not part of it: at most one anchor policy survives composition
    and is applied once, afterwards, by :func:`apply_anchor_policy`.
    """
    kinds = _string_list(select.get("kinds"), field="select.kinds", warnings=warnings)
    type_patterns = _string_list(
        select.get("types"), field="select.types", warnings=warnings
    )
    statuses = _string_list(
        select.get("status"), field="select.status", warnings=warnings
    ) or ["canon", "draft"]

    allowed_places: set[str] | None = None
    where_under = select.get("where_under")
    if where_under is not None:
        if isinstance(where_under, str):
            allowed_places = _descendants(where_under, _part_of_parents(canon, warnings))
        else:
            _warn(warnings, "view: 'select.where_under' must be an artifact id; ignored")

    base_artifacts: dict[str, Artifact] = {}
    for artifact in canon.artifacts.values():
        if artifact.kind in {"type", "relation"}:
            continue
        if kinds is not None and artifact.kind not in kinds:
            continue
        if not _type_matches(artifact.type, type_patterns):
            continue
        if not _passes_scope_filters(
            artifact,
            select=select,
            allowed_statuses=statuses,
            allowed_places=allowed_places,
            warnings=warnings,
        ):
            continue
        base_artifacts[artifact.id] = artifact

    relation_kind_allowed = kinds is None or "relation" in kinds
    include = _string_list(
        edges_config.get("include"), field="edges.include", warnings=warnings
    )
    exclude = _string_list(
        edges_config.get("exclude"), field="edges.exclude", warnings=warnings
    ) or []
    relation_artifacts: dict[str, Artifact] = {}
    if relation_kind_allowed:
        for artifact in canon.artifacts.values():
            if artifact.kind != "relation":
                continue
            if include is not None and not _type_matches(artifact.type, include):
                continue
            if exclude and _type_matches(artifact.type, exclude):
                continue
            if not _passes_scope_filters(
                artifact,
                select=select,
                allowed_statuses=statuses,
                # Spatial selection chooses visible artifacts. Relations then
                # survive or disappear according to whether their endpoints
                # are visible; the relation file itself need not repeat where.
                allowed_places=None,
                warnings=warnings,
            ):
                continue
            relation_artifacts[artifact.id] = artifact

    return base_artifacts, relation_artifacts


def apply_anchor_policy(
    canon: Canon,
    base_artifacts: dict[str, Artifact],
    relation_artifacts: dict[str, Artifact],
    select: Mapping[str, Any],
    *,
    warnings: list[str],
) -> tuple[dict[str, Artifact], dict[str, Artifact]]:
    """Narrow a selection to the artifacts connected to its declared anchors."""
    connected_to_kinds = _string_list(
        select.get("connected_to_kinds"),
        field="select.connected_to_kinds",
        warnings=warnings,
    )
    connected_to_types = _string_list(
        select.get("connected_to_types"),
        field="select.connected_to_types",
        warnings=warnings,
    )
    # Preserve the established empty-kind-list behaviour (no anchor mode)
    # while an explicitly supplied typed-anchor list remains meaningful.
    if connected_to_kinds or connected_to_types is not None:
        # Keep the requested anchor kinds even when they are isolated. Other
        # artifacts survive only when an included relation directly connects
        # them to an anchor. Follow relation-to-relation dependencies solely
        # far enough to keep reified relations renderable; do not expand the
        # entire connected component through non-anchor nodes.
        anchor_ids = {
            artifact_id
            for artifact_id, artifact in base_artifacts.items()
            if (connected_to_kinds is None or artifact.kind in connected_to_kinds)
            # Unlike an omitted candidate type filter, an explicitly empty
            # anchor list has no matching anchors.
            and (
                connected_to_types is None
                or any(
                    fnmatchcase(artifact.type, pattern)
                    if artifact.type is not None
                    else pattern in {"*", "<untyped>"}
                    for pattern in connected_to_types
                )
            )
        }
        members_by_candidate = {
            artifact.id: _roles_and_members(artifact)
            for artifact in relation_artifacts.values()
        }
        kept_relation_ids = {
            relation_id
            for relation_id, members in members_by_candidate.items()
            if any(member_id in anchor_ids for member_id, _ in members)
        }

        changed = True
        while changed:
            dependencies = {
                member_id
                for relation_id in kept_relation_ids
                for member_id, _ in members_by_candidate[relation_id]
                if member_id in relation_artifacts
            }
            expanded = kept_relation_ids | dependencies
            changed = expanded != kept_relation_ids
            kept_relation_ids = expanded

        kept_base_ids = anchor_ids | {
            member_id
            for relation_id in kept_relation_ids
            for member_id, _ in members_by_candidate[relation_id]
            if member_id in base_artifacts
        }
        base_artifacts = {
            artifact_id: artifact
            for artifact_id, artifact in base_artifacts.items()
            if artifact_id in kept_base_ids
        }
        relation_artifacts = {
            artifact_id: artifact
            for artifact_id, artifact in relation_artifacts.items()
            if artifact_id in kept_relation_ids
        }

    return base_artifacts, relation_artifacts


def project_views(
    canon: Canon,
    views: Iterable[View],
    *,
    index: Any | None = None,
) -> list[dict[str, Any]]:
    """Project several views while reusing one canon load and one module index.

    Built-in Everything keeps its independent audit policy and never consults
    the module index. Only the views actually requested are generated.
    """
    from .compile import compile_view
    from .modules import load_module_index

    view_list = list(views)
    if index is None and any(
        view.policy is not ProjectionPolicy.AUDIT_GENERAL
        and view.data.get("compose") is not None
        for view in view_list
    ):
        index = load_module_index(canon.root)

    projections: list[dict[str, Any]] = []
    for view in view_list:
        if view.policy is ProjectionPolicy.AUDIT_GENERAL:
            projections.append(project_view(canon, view))
        else:
            projections.append(
                project_view(canon, view, plan=compile_view(canon, view, index=index))
            )
    return projections


def _finding(
    findings: list[dict[str, Any]] | None,
    code: str,
    message: str,
    **detail: Any,
) -> None:
    """Record a structured structural finding for validation, if one is wanted."""
    if findings is not None:
        findings.append({"code": code, "message": message, **detail})


def project_view(
    canon: Canon,
    view: View,
    *,
    plan: Any | None = None,
    findings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return the exact Viewer v0 projection shape for one loaded view.

    Composition is already finished by the time this runs: ``plan`` is a
    :class:`~viewer.compile.CompiledViewPlan` carrying normalized selection,
    relation policy, and resolved style and lens tables. One is compiled here
    when a caller does not supply it, so projection never loads modules itself.
    """
    if view.policy is ProjectionPolicy.AUDIT_GENERAL:
        return _project_audit_general(canon, view)

    from .compile import compile_view

    warnings = [*canon.warnings, *view.warnings]
    if plan is None:
        plan = compile_view(canon, view)
    for message in (*plan.warnings, *plan.messages()):
        _warn(warnings, message)

    emphasis = plan.emphasis
    # Rebuild in canon order so node and edge order stays deterministic.
    base_artifacts = {
        artifact_id: artifact
        for artifact_id, artifact in canon.artifacts.items()
        if artifact_id in plan.base_ids
    }
    relation_artifacts = {
        artifact_id: artifact
        for artifact_id, artifact in canon.artifacts.items()
        if artifact_id in plan.relation_ids
    }

    relation_ids = set(relation_artifacts)
    members_by_relation = {
        artifact.id: _roles_and_members(artifact)
        for artifact in relation_artifacts.values()
    }
    targeted_relations = {
        member_id
        for members in members_by_relation.values()
        for member_id, _ in members
        if member_id in relation_ids
    }
    canon_lenses_by_relation = {
        relation_id: _resolve_lens(artifact, canon, warnings)
        for relation_id, artifact in relation_artifacts.items()
    }
    lenses_by_relation = {
        relation_id: {
            **canon_lens,
            **plan.overrides_for(relation_id),
        }
        for relation_id, canon_lens in canon_lenses_by_relation.items()
    }
    containments_by_relation = {
        relation_id: (
            _nest_parts_and_whole(
                members, _canon_nest_lens(canon_lenses_by_relation[relation_id])
            )
            if lenses_by_relation[relation_id].get("as") == "nest"
            else None
        )
        for relation_id, members in members_by_relation.items()
    }
    reified = {
        relation_id
        for relation_id, members in members_by_relation.items()
        if relation_id in targeted_relations
        or (
            lenses_by_relation[relation_id].get("as") == "nest"
            and containments_by_relation[relation_id] is None
        )
        or (len(members) >= 3 and containments_by_relation[relation_id] is None)
    }

    # A reified relation is a node, so invalid reified endpoints can invalidate
    # other relations that target it. Prune until the visible-node set stabilizes.
    changed = True
    while changed:
        changed = False
        visible = set(base_artifacts) | reified
        for relation_id in list(reified):
            members = members_by_relation[relation_id]
            if not members or any(member_id not in visible for member_id, _ in members):
                reified.remove(relation_id)
                changed = True

    visible_nodes = set(base_artifacts) | reified
    valid_relations: dict[str, Artifact] = {}
    for relation_id, artifact in relation_artifacts.items():
        members = members_by_relation[relation_id]
        if not members:
            _warn(warnings, f"{artifact.relative_path}: relation has no valid members; omitted")
            continue
        missing = [member_id for member_id, _ in members if member_id not in visible_nodes]
        if missing:
            message = (
                f"{artifact.relative_path}: filtered or missing member(s) {missing}; "
                "relation omitted"
            )
            _warn(warnings, message)
            _finding(
                findings,
                "structure.relation-not-whole",
                message,
                relation=relation_id,
                missing=missing,
            )
            continue
        valid_relations[relation_id] = artifact

    held_ideas = {
        member_id
        for relation in canon.artifacts.values()
        if relation.kind == "relation"
        and relation.type
        and any(ancestor == "holds" for ancestor in _type_ancestors(relation.type))
        for member_id, role in _roles_and_members(relation)
        if role == "held"
    }
    held_ideas = _entertained_ideas(canon, held_ideas)

    nodes = {
        artifact.id: _node(
            artifact,
            canon,
            emphasis,
            warnings,
            held_ideas=held_ideas,
            overrides=plan.overrides_for(artifact.id),
        )
        for artifact in base_artifacts.values()
    }
    for relation_id in sorted(reified):
        if relation_id in valid_relations:
            artifact = valid_relations[relation_id]
            nodes[relation_id] = _node(
                artifact,
                canon,
                emphasis,
                warnings,
                held_ideas=held_ideas,
                overrides=plan.overrides_for(relation_id),
            )

    projected_edges: list[dict[str, Any]] = []
    parents: dict[str, str] = {}
    for relation_id, artifact in valid_relations.items():
        members = members_by_relation[relation_id]
        lens = lenses_by_relation[relation_id]
        behavior = str(lens.get("as", "edge"))
        containment = containments_by_relation[relation_id]
        direction = _direction(lens.get("direction")) if "direction" in lens else None

        if behavior == "nest":
            if containment is None:
                part_role, whole_role = _nest_roles(
                    _canon_nest_lens(canon_lenses_by_relation[relation_id])
                )
                message = (
                    f"{artifact.relative_path}: nest requires exactly one "
                    f"'{whole_role}' and one or more '{part_role}'"
                )
                _warn(warnings, message)
                _finding(
                    findings,
                    "structure.nest-not-whole",
                    message,
                    relation=relation_id,
                )
            else:
                parts, parent = containment
                for _, child in parts:
                    if child in parents:
                        message = (
                            f"{artifact.relative_path}: '{child}' already has a nest parent"
                        )
                        _warn(warnings, message)
                        _finding(
                            findings,
                            "structure.multiple-nest-parents",
                            message,
                            relation=relation_id,
                            artifact=child,
                            existing_parent=parents[child],
                            rejected_parent=parent,
                        )
                    elif _would_cycle(child, parent, parents):
                        message = f"{artifact.relative_path}: nest cycle ignored"
                        _warn(warnings, message)
                        _finding(
                            findings,
                            "structure.containment-cycle",
                            message,
                            relation=relation_id,
                            artifact=child,
                            parent=parent,
                        )
                    else:
                        parents[child] = parent

        # A one-member state remains a chip even when another relation targets
        # it. Invalid containment is the exception: it must stay inspectable
        # as generic reification rather than become a misleading state chip.
        if relation_id in reified and (len(members) != 1 or behavior == "nest"):
            directed_roles_resolved = (
                direction is not None
                and any(role == direction[0] for _, role in members)
                and any(role == direction[1] for _, role in members)
            )
            if direction is not None and not directed_roles_resolved:
                message = (
                    f"{artifact.relative_path}: direction {direction[0]} -> {direction[1]}"
                    " cannot be resolved from members; using undirected edge"
                )
                _warn(warnings, message)
                _finding(
                    findings,
                    "structure.invalid-direction",
                    message,
                    relation=relation_id,
                    direction=list(direction),
                )
            for index, (member_id, role) in enumerate(members, start=1):
                if directed_roles_resolved and role == direction[0]:
                    source, target = member_id, artifact.id
                    source_role, target_role, directed = role, "relation", True
                elif directed_roles_resolved and role == direction[1]:
                    source, target = artifact.id, member_id
                    source_role, target_role, directed = "relation", role, True
                else:
                    source, target = artifact.id, member_id
                    source_role, target_role, directed = "relation", role, False
                projected_edges.append(
                    _relation_edge(
                        artifact,
                        edge_id=f"{artifact.id}::member:{index}",
                        source=source,
                        target=target,
                        source_role=source_role,
                        target_role=target_role,
                        directed=directed,
                        behavior="edge",
                        lens=lens,
                        emphasis=emphasis,
                    )
                )
            continue

        if len(members) == 1:
            subject_id, _ = members[0]
            nodes[subject_id]["chips"].append(
                {
                    "source": artifact.id,
                    "type": artifact.type,
                    "when": artifact.frontmatter.get("when"),
                    "amount": artifact.frontmatter.get("amount"),
                }
            )
            continue

        if behavior == "nest" and containment is not None and len(members) > 2:
            parts, parent = containment
            for index, child in parts:
                projected_edges.append(
                    _relation_edge(
                        artifact,
                        edge_id=f"{artifact.id}::member:{index}",
                        source=child,
                        target=parent,
                        source_role="part",
                        target_role="whole",
                        directed=False,
                        behavior="nest",
                        lens=lens,
                        emphasis=emphasis,
                    )
                )
            continue

        oriented = _binary_direction(members, direction)
        if direction is not None and oriented is None:
            message = (
                f"{artifact.relative_path}: direction {direction[0]} -> {direction[1]}"
                " cannot be resolved from members; using undirected edge"
            )
            _warn(warnings, message)
            _finding(
                findings,
                "structure.invalid-direction",
                message,
                relation=relation_id,
                direction=list(direction),
            )
        source, target = oriented or (members[0], members[1])
        projected_edges.append(
            _relation_edge(
                artifact,
                edge_id=artifact.id,
                source=source[0],
                target=target[0],
                source_role=source[1],
                target_role=target[1],
                # Nesting encodes containment through compound-node parentage;
                # keep its structural endpoint order but never draw an arrow.
                directed=oriented is not None and behavior != "nest",
                behavior=behavior,
                lens=lens,
                emphasis=emphasis,
            )
        )
    for child, parent in parents.items():
        if child in nodes and parent in nodes:
            nodes[child]["parent"] = parent

    return {
        "view": {"name": view.name, "layout": plan.layout, "render": view.render},
        "nodes": list(nodes.values()),
        "edges": projected_edges,
        "warnings": list(dict.fromkeys(warnings)),
    }
