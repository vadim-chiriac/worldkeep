"""Compile a named view recipe and its modules into one normalized plan.

Composition happens here, once, before projection. The compiler resolves typed
module references, runs the selection and relation algebra, records provenance
for every decision, and hands ``project_view`` a :class:`CompiledViewPlan`.
Projection stays focused on turning selected artifacts into the stable Viewer
v0 document; it never loads or interprets modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from typing import Any, Iterable, Mapping, Sequence

from .load import Artifact, Canon, View
from .modules import (
    ANCHOR_KEYS,
    STRUCTURAL_KEYS,
    ModuleError,
    ModuleIndex,
    ViewModule,
    _normalized_hash,
    load_module_index,
    validate_lens_rules,
    validate_style_rules,
)
from .project import (
    _mapping,
    _roles_and_members,
    _string_list,
    _type_ancestors,
    _type_matches,
    apply_anchor_policy,
    select_candidates,
)


COMPILER_SCHEMA = "wb.view-compiler/v1"

COMPOSE_KEYS = frozenset({"selection", "relations", "styles", "lenses"})
#: The layouts a renderer knows. Kept here rather than only in the renderer so
#: a misspelling is reported when a view is validated, not swallowed when it is
#: drawn. Must stay in step with the allowed list in render_graph.py.
LAYOUTS = frozenset({"fcose", "dagre", "concentric", "preset"})
COMPOSE_SELECTION_KEYS = frozenset({"any_of", "all_of", "exclude"})
COMPOSE_RELATION_KEYS = frozenset({"include", "exclude"})

#: Compose sections, in the order they are resolved, with their module kind.
COMPOSE_SECTION_KINDS = {
    "selection": "selection",
    "relations": "relation",
    "styles": "style",
    "lenses": "lens",
}


class CompileError(ValueError):
    """A view recipe cannot be compiled into a deterministic plan."""


@dataclass(frozen=True)
class Diagnostic:
    """One structured compiler finding, carried alongside its flat message."""

    severity: str
    code: str
    message: str
    detail: Mapping[str, Any] = field(default_factory=dict)

    def as_json(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "detail": dict(self.detail),
        }


@dataclass(frozen=True)
class AnchorPolicy:
    """The single connected-anchor policy that survived composition."""

    kinds: tuple[str, ...] | None
    types: tuple[str, ...] | None
    sources: tuple[str, ...]

    @property
    def signature(self) -> tuple[tuple[str, ...] | None, tuple[str, ...] | None]:
        return (self.kinds, self.types)

    def as_select(self) -> dict[str, Any]:
        select: dict[str, Any] = {}
        if self.kinds is not None:
            select["connected_to_kinds"] = list(self.kinds)
        if self.types is not None:
            select["connected_to_types"] = list(self.types)
        return select

    def describe(self) -> str:
        parts = []
        if self.kinds is not None:
            parts.append(f"connected_to_kinds={list(self.kinds)}")
        if self.types is not None:
            parts.append(f"connected_to_types={list(self.types)}")
        return ", ".join(parts) or "none"


@dataclass(frozen=True)
class CompiledRule:
    """One style or lens rule, carrying where it came from."""

    match: Mapping[str, str]
    set: Mapping[str, Any]
    source: str
    local: bool
    layer: str

    def matches(self, artifact: Artifact) -> bool:
        kind = self.match.get("kind")
        if kind is not None and artifact.kind != kind:
            return False
        pattern = self.match.get("type")
        if pattern is not None and not _type_matches(artifact.type, [pattern]):
            return False
        return True

    def is_exact_for(self, artifact: Artifact) -> bool:
        """True when a view-local rule names this exact type, not a wildcard.

        Only such a rule may resolve a structural conflict; a broad wildcard
        deliberately does not count as an explicit decision.
        """
        pattern = self.match.get("type")
        if not self.local or pattern is None:
            return False
        if any(character in pattern for character in "*?["):
            return False
        return pattern == artifact.type


@dataclass(frozen=True)
class CompiledViewPlan:
    """Normalized, provenance-bearing input to projection."""

    view_name: str
    render: str
    layout: str
    composed: bool
    #: Every artifact the projection must draw, semantic selection plus the
    #: endpoints added only to keep a selected relation whole.
    base_ids: frozenset[str]
    relation_ids: frozenset[str]
    emphasis: Mapping[str, Any]
    anchor: AnchorPolicy | None
    relation_policy: Mapping[str, Any]
    selection_sources: Mapping[str, Mapping[str, frozenset[str]]]
    endpoint_completions: frozenset[str]
    diagnostics: tuple[Diagnostic, ...]
    provenance: Mapping[str, Any]
    warnings: tuple[str, ...] = ()
    #: The positive artifact-selection result, before any projection-integrity
    #: completion. This is what "did the recipe choose it?" means.
    semantic_base_ids: frozenset[str] = frozenset()
    #: Relations admitted by an explicit include rather than the implicit
    #: default. Only these are independent of artifact selection and may
    #: complete endpoints.
    explicit_relation_ids: frozenset[str] = frozenset()
    style_rules: tuple[CompiledRule, ...] = ()
    lens_rules: tuple[CompiledRule, ...] = ()
    lens_overrides: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    style_overrides: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    property_sources: Mapping[str, Mapping[str, str]] = field(default_factory=dict)

    def overrides_for(self, artifact_id: str) -> dict[str, Any]:
        """Return the composed lens-then-style overlay for one artifact.

        Lenses resolve first and own structure; the style cascade then settles
        presentation properties on top of them.
        """
        merged = dict(self.lens_overrides.get(artifact_id, {}))
        merged.update(self.style_overrides.get(artifact_id, {}))
        return merged

    @property
    def errors(self) -> tuple[Diagnostic, ...]:
        return tuple(item for item in self.diagnostics if item.severity == "error")

    def messages(self) -> list[str]:
        """Return diagnostics as flat strings for the existing warning channel.

        Errors lead so that a fallback stays prominent wherever warnings are
        shown, including the renderer's warning tooltip.
        """
        return [item.message for item in self.diagnostics if item.severity == "error"] + [
            item.message for item in self.diagnostics if item.severity != "error"
        ]

    def fingerprint(self) -> str:
        """Return the dependency fingerprint a lock records."""
        return _normalized_hash(self.provenance)


def _require_mapping(value: Any, *, where: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise CompileError(f"{where} must be a mapping")
    for key in value:
        if not isinstance(key, str):
            raise CompileError(f"{where} has a non-string key {key!r}")
    return value


def _reject_unknown(value: Mapping[str, Any], allowed: frozenset[str], *, where: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise CompileError(
            f"{where}: unknown field(s) {', '.join(repr(key) for key in unknown)}; "
            f"allowed: {', '.join(sorted(allowed))}"
        )


def _reference_list(value: Any, *, where: str) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, str) or not isinstance(value, list):
        raise CompileError(f"{where} must be a list of module ids")
    return list(value)


def _resolve_section(
    index: ModuleIndex,
    references: Sequence[Any],
    *,
    kind: str,
    where: str,
) -> list[ViewModule]:
    resolved: list[ViewModule] = []
    seen: set[str] = set()
    for position, reference in enumerate(references, start=1):
        context = f"{where}[{position}]"
        try:
            module = index.resolve(reference, kind=kind, context=context)
        except ModuleError as exc:
            raise CompileError(str(exc)) from exc
        if module.id in seen:
            raise CompileError(f"{context}: module '{module.id}' is referenced twice")
        seen.add(module.id)
        resolved.append(module)
    return resolved


@dataclass(frozen=True)
class _ComposeSpec:
    """The validated ``compose`` block of one view recipe."""

    any_of: tuple[ViewModule, ...] = ()
    all_of: tuple[ViewModule, ...] = ()
    exclude: tuple[ViewModule, ...] = ()
    relations_include: tuple[ViewModule, ...] = ()
    relations_exclude: tuple[ViewModule, ...] = ()
    styles: tuple[ViewModule, ...] = ()
    lenses: tuple[ViewModule, ...] = ()
    declared_any_of: bool = False

    def modules(self) -> Iterable[ViewModule]:
        yield from self.any_of
        yield from self.all_of
        yield from self.exclude
        yield from self.relations_include
        yield from self.relations_exclude
        yield from self.styles
        yield from self.lenses


def _parse_compose(raw: Any, index: ModuleIndex) -> _ComposeSpec:
    compose = _require_mapping(raw, where="compose")
    _reject_unknown(compose, COMPOSE_KEYS, where="compose")

    selection = _require_mapping(compose.get("selection", {}), where="compose.selection")
    _reject_unknown(selection, COMPOSE_SELECTION_KEYS, where="compose.selection")
    relations = _require_mapping(compose.get("relations", {}), where="compose.relations")
    _reject_unknown(relations, COMPOSE_RELATION_KEYS, where="compose.relations")

    declared_any_of = "any_of" in selection
    any_of_refs = _reference_list(selection.get("any_of"), where="compose.selection.any_of")
    if declared_any_of and not any_of_refs:
        raise CompileError(
            "compose.selection.any_of is present but empty; remove it to select the "
            "ordinary candidate set, or name at least one selection module"
        )

    return _ComposeSpec(
        any_of=tuple(
            _resolve_section(index, any_of_refs, kind="selection", where="compose.selection.any_of")
        ),
        all_of=tuple(
            _resolve_section(
                index,
                _reference_list(selection.get("all_of"), where="compose.selection.all_of"),
                kind="selection",
                where="compose.selection.all_of",
            )
        ),
        exclude=tuple(
            _resolve_section(
                index,
                _reference_list(selection.get("exclude"), where="compose.selection.exclude"),
                kind="selection",
                where="compose.selection.exclude",
            )
        ),
        relations_include=tuple(
            _resolve_section(
                index,
                _reference_list(relations.get("include"), where="compose.relations.include"),
                kind="relation",
                where="compose.relations.include",
            )
        ),
        relations_exclude=tuple(
            _resolve_section(
                index,
                _reference_list(relations.get("exclude"), where="compose.relations.exclude"),
                kind="relation",
                where="compose.relations.exclude",
            )
        ),
        styles=tuple(
            _resolve_section(
                index,
                _reference_list(compose.get("styles"), where="compose.styles"),
                kind="style",
                where="compose.styles",
            )
        ),
        lenses=tuple(
            _resolve_section(
                index,
                _reference_list(compose.get("lenses"), where="compose.lenses"),
                kind="lens",
                where="compose.lenses",
            )
        ),
        declared_any_of=declared_any_of,
    )


def _anchor_signature(
    select: Mapping[str, Any],
) -> tuple[tuple[str, ...] | None, tuple[str, ...] | None] | None:
    """Return a normalized anchor signature, or ``None`` when none is declared."""
    kinds = select.get("connected_to_kinds")
    types = select.get("connected_to_types")
    if kinds is None and types is None:
        return None
    # An explicitly empty list is meaningful (no matching anchors) and must not
    # be normalized away into "absent".
    return (
        tuple(kinds) if isinstance(kinds, list) else None,
        tuple(types) if isinstance(types, list) else None,
    )


def _collect_anchor(
    sources: Sequence[tuple[str, Mapping[str, Any]]],
) -> AnchorPolicy | None:
    """Return the one anchor policy that survives, or raise on disagreement."""
    found: dict[tuple[Any, Any], list[str]] = {}
    for label, select in sources:
        signature = _anchor_signature(select)
        if signature is None:
            continue
        found.setdefault(signature, []).append(label)

    if not found:
        return None
    if len(found) > 1:
        described = "; ".join(
            f"{', '.join(labels)} declares "
            + ", ".join(
                f"{key}={list(value) if value is not None else 'unset'}"
                for key, value in zip(ANCHOR_KEYS, signature)
            )
            for signature, labels in sorted(found.items(), key=lambda item: item[1])
        )
        raise CompileError(
            "compose: incompatible connected-anchor policies; at most one may "
            f"survive composition ({described}). Reconcile them in one selection "
            "module rather than relying on the compiler to guess union or "
            "intersection."
        )

    signature, labels = next(iter(found.items()))
    return AnchorPolicy(kinds=signature[0], types=signature[1], sources=tuple(labels))


def _evaluate(
    canon: Canon,
    select: Mapping[str, Any],
    warnings: list[str],
) -> frozenset[str]:
    """Return every artifact id one selector chooses, relations included."""
    base, relations = select_candidates(canon, select, {}, warnings=warnings)
    return frozenset(base) | frozenset(relations)


def _relevant_type_fingerprint(canon: Canon, artifact_ids: Iterable[str]) -> str:
    """Fingerprint only the type files whose ancestry or lens shaped this plan."""
    relevant: dict[str, Any] = {}
    for artifact_id in artifact_ids:
        artifact = canon.artifacts.get(artifact_id)
        if artifact is None:
            continue
        for ancestor in _type_ancestors(artifact.type):
            type_artifact = canon.types.get(ancestor)
            if type_artifact is None or type_artifact.relative_path in relevant:
                continue
            relevant[type_artifact.relative_path] = {
                "id": type_artifact.id,
                "type": type_artifact.type,
                "lens": type_artifact.frontmatter.get("lens"),
            }
    return _normalized_hash(relevant)


def _relation_passes(
    artifact: Artifact,
    policy: Mapping[str, Any],
) -> bool:
    """Apply composed and view-local relation policy; exclusion always wins."""
    excludes = policy["exclude"]
    if excludes and _type_matches(artifact.type, list(excludes)):
        return False
    composed_include = policy["composed_include"]
    if composed_include and not _type_matches(artifact.type, list(composed_include)):
        return False
    local_include = policy["local_include"]
    if local_include is not None and not _type_matches(artifact.type, list(local_include)):
        return False
    return True


def _collect_rules(
    modules: Sequence[ViewModule],
    local: Any,
    *,
    layer: str,
    view_path: str,
    validate,
) -> list[CompiledRule]:
    """Return imported rules in declared order, then view-local rules."""
    rules: list[CompiledRule] = []
    for module in modules:
        for position, rule in enumerate(module.payload, start=1):
            rules.append(
                CompiledRule(
                    match=rule["match"],
                    set=rule["set"],
                    source=f"module '{module.id}' {layer}[{position}]",
                    local=False,
                    layer=layer,
                )
            )
    if local is None:
        return rules
    try:
        validated = validate(local, where=f"{view_path}: {layer}")
    except ModuleError as exc:
        raise CompileError(str(exc)) from exc
    for position, rule in enumerate(validated, start=1):
        rules.append(
            CompiledRule(
                match=rule["match"],
                set=rule["set"],
                source=f"{view_path}: {layer}[{position}]",
                local=True,
                layer=layer,
            )
        )
    return rules


def _resolve_cascade(
    canon: Canon,
    artifact_ids: Iterable[str],
    lens_rules: Sequence[CompiledRule],
    style_rules: Sequence[CompiledRule],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, str]],
    list[Diagnostic],
]:
    """Resolve every property independently, recording who won and who lost."""
    lens_overrides: dict[str, dict[str, Any]] = {}
    style_overrides: dict[str, dict[str, Any]] = {}
    property_sources: dict[str, dict[str, str]] = {}
    diagnostics: list[Diagnostic] = []

    for artifact_id in sorted(artifact_ids):
        artifact = canon.artifacts.get(artifact_id)
        if artifact is None:
            continue

        # One effective table per artifact. Every property is resolved
        # independently, so a later rule replaces only what it actually sets.
        effective: dict[str, tuple[Any, CompiledRule]] = {}
        structural: dict[str, list[tuple[Any, CompiledRule]]] = {}

        for rules in (lens_rules, style_rules):
            for rule in rules:
                if not rule.matches(artifact):
                    continue
                for prop, value in rule.set.items():
                    if prop in STRUCTURAL_KEYS:
                        structural.setdefault(prop, []).append((value, rule))
                    previous = effective.get(prop)
                    if (
                        previous is not None
                        and prop not in STRUCTURAL_KEYS
                        and previous[1].source != rule.source
                        and previous[0] != value
                    ):
                        diagnostics.append(
                            Diagnostic(
                                severity="warning",
                                code="style.overlap",
                                message=(
                                    f"{artifact.relative_path}: '{prop}' set to "
                                    f"{value!r} by {rule.source}, overriding "
                                    f"{previous[0]!r} from {previous[1].source}"
                                ),
                                detail={
                                    "artifact": artifact_id,
                                    "property": prop,
                                    "winning_value": value,
                                    "winning_source": rule.source,
                                    "losing_value": previous[0],
                                    "losing_source": previous[1].source,
                                },
                            )
                        )
                    effective[prop] = (value, rule)

        for prop, (value, rule) in effective.items():
            target = lens_overrides if rule.layer == "lenses" else style_overrides
            target.setdefault(artifact_id, {})[prop] = value
        winners = {prop: rule.source for prop, (_, rule) in effective.items()}

        for prop, declarations in structural.items():
            distinct = {_hashable(value) for value, _ in declarations}
            if len(distinct) < 2:
                continue
            resolver = next(
                (
                    rule
                    for value, rule in reversed(declarations)
                    if rule.is_exact_for(artifact)
                ),
                None,
            )
            if resolver is not None:
                resolved_value = next(
                    value for value, rule in reversed(declarations) if rule is resolver
                )
                lens_overrides.setdefault(artifact_id, {})[prop] = resolved_value
                winners[prop] = resolver.source
                diagnostics.append(
                    Diagnostic(
                        severity="warning",
                        code="lens.structural-resolved",
                        message=(
                            f"{artifact.relative_path}: conflicting '{prop}' "
                            f"declarations resolved to {resolved_value!r} by the "
                            f"exact view-local rule {resolver.source}"
                        ),
                        detail={
                            "artifact": artifact_id,
                            "property": prop,
                            "resolved_by": resolver.source,
                            "value": resolved_value,
                        },
                    )
                )
                continue
            # Fallback is a runtime safety mechanism, never a decision: drop the
            # disputed structural override so the artifact keeps its ordinary,
            # visibly inspectable representation, and say so loudly.
            lens_overrides.get(artifact_id, {}).pop(prop, None)
            winners.pop(prop, None)
            diagnostics.append(
                Diagnostic(
                    severity="error",
                    code="lens.structural-conflict",
                    message=(
                        f"UNVALIDATED FALLBACK: {artifact.relative_path}: "
                        f"conflicting '{prop}' declarations "
                        + " and ".join(
                            f"{value!r} from {rule.source}" for value, rule in declarations
                        )
                        + f"; add a view-local lens rule matching type "
                        f"'{artifact.type}' exactly to resolve it"
                    ),
                    detail={
                        "artifact": artifact_id,
                        "property": prop,
                        "declarations": [
                            {"value": value, "source": rule.source}
                            for value, rule in declarations
                        ],
                    },
                )
            )

        if winners:
            property_sources[artifact_id] = winners

    return lens_overrides, style_overrides, property_sources, diagnostics


def _hashable(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_hashable(item) for item in value)
    if isinstance(value, dict):
        return tuple(sorted((key, _hashable(item)) for key, item in value.items()))
    return value


def compile_view(
    canon: Canon,
    view: View,
    *,
    index: ModuleIndex | None = None,
) -> CompiledViewPlan:
    """Compile one named view into a normalized, provenance-bearing plan."""
    data = view.data
    raw_compose = data.get("compose")
    composed = raw_compose is not None

    if index is None:
        index = load_module_index(canon.root) if composed else ModuleIndex(
            root=canon.root, relative_root="view-modules", modules={}
        )

    warnings: list[str] = [*view.warnings, *index.warnings]
    diagnostics: list[Diagnostic] = []

    # These three keys predate composition. Malformed values keep their
    # established warn-and-default behaviour; strictness applies to module and
    # compose fields, which are new surface.
    local_select = _mapping(data.get("select"), field="select", warnings=warnings)
    edges_config = _mapping(data.get("edges"), field="edges", warnings=warnings)
    emphasis = _mapping(data.get("emphasis"), field="emphasis", warnings=warnings)

    # The renderer silently falls back to fcose for anything it does not know,
    # so a misspelt layout produced a picture with no explanation and a view
    # that validated clean. Name it here, where someone is asking.
    layout = data.get("layout", "fcose")
    if not isinstance(layout, str):
        warnings.append("view: 'layout' must be a string; using fcose")
        layout = "fcose"
    elif layout not in LAYOUTS:
        diagnostics.append(
            Diagnostic(
                severity="warning",
                code="view.unknown-layout",
                message=(
                    f"{view.relative_path}: unknown layout '{layout}'; using "
                    f"fcose (known: {', '.join(sorted(LAYOUTS))})"
                ),
                detail={"layout": layout},
            )
        )
        layout = "fcose"

    spec = _parse_compose(raw_compose, index) if composed else _ComposeSpec()

    selection_sources: dict[str, dict[str, frozenset[str]]] = {
        "any_of": {},
        "all_of": {},
        "exclude": {},
    }

    if not composed:
        # Compatibility path: one selector, exactly as before composition existed.
        base_map, relation_map = select_candidates(
            canon, local_select, edges_config, warnings=warnings
        )
        anchor_sources = [(f"{view.relative_path}: select", local_select)]
        anchor = _collect_anchor(anchor_sources)
        base_map, relation_map = apply_anchor_policy(
            canon, base_map, relation_map, local_select, warnings=warnings
        )
        relation_policy = {
            "composed_include": (),
            "local_include": None,
            "exclude": (),
            "explicit": False,
        }
        # The compatibility path keeps today's behaviour exactly: a relation
        # whose endpoints were filtered out is still dropped with a warning,
        # and nothing is ever completed.
        semantic_base_ids = frozenset(base_map)
        endpoint_completions: frozenset[str] = frozenset()
        explicit_relation_ids: frozenset[str] = frozenset()
    else:
        anchor_sources = [
            (f"module '{module.id}'", module.payload)
            for module in (*spec.any_of, *spec.all_of, *spec.exclude)
        ]
        if local_select:
            anchor_sources.append((f"{view.relative_path}: select", local_select))
        anchor = _collect_anchor(anchor_sources)

        # 1-2. any_of unions its modules; absent, it is the ordinary candidate set.
        if spec.any_of:
            selected = frozenset()
            for module in spec.any_of:
                chosen = _evaluate(canon, module.payload, warnings)
                selection_sources["any_of"][module.id] = chosen
                selected |= chosen
        else:
            selected = _evaluate(canon, {}, warnings)

        # 3. all_of intersects its modules, then narrows the any_of result.
        for module in spec.all_of:
            chosen = _evaluate(canon, module.payload, warnings)
            selection_sources["all_of"][module.id] = chosen
            selected &= chosen

        # 4. exclude unions and subtracts. Nothing later resurrects these.
        excluded = frozenset()
        for module in spec.exclude:
            chosen = _evaluate(canon, module.payload, warnings)
            selection_sources["exclude"][module.id] = chosen
            excluded |= chosen
        selected -= excluded

        # 5. The view-local select narrows last and can only remove.
        if local_select:
            local_ids = _evaluate(canon, local_select, warnings)
            resurrected = sorted((local_ids & excluded) - selected)
            if resurrected:
                diagnostics.append(
                    Diagnostic(
                        severity="warning",
                        code="selection.no-resurrection",
                        message=(
                            f"{view.relative_path}: select matches "
                            f"{len(resurrected)} artifact(s) already removed by "
                            f"compose.selection.exclude; they stay excluded "
                            f"(first: {resurrected[0]})"
                        ),
                        detail={"artifacts": resurrected},
                    )
                )
            selected &= local_ids

        base_map = {
            artifact_id: canon.artifacts[artifact_id]
            for artifact_id in selected
            if artifact_id in canon.artifacts
            and canon.artifacts[artifact_id].kind != "relation"
        }
        # Relation policy is compiled separately from artifact selection, so a
        # selection module scoped to entities cannot silently suppress the
        # relation modules a recipe explicitly composed. Candidates are every
        # relation passing the view-local scope filters; the include/exclude
        # policy below decides which survive, and projection still drops any
        # whose endpoints are not visible.
        relation_scope = {
            key: value for key, value in local_select.items() if key != "kinds"
        }
        _, relation_candidates = select_candidates(
            canon, relation_scope, {}, warnings=warnings
        )

        composed_include: tuple[str, ...] = ()
        composed_exclude: list[str] = []
        for module in spec.relations_include:
            composed_include += tuple(module.payload.get("include", ()))
            composed_exclude.extend(module.payload.get("exclude", ()))
        for module in spec.relations_exclude:
            # A module named under compose.relations.exclude subtracts whatever
            # it describes, whichever payload key carries it.
            composed_exclude.extend(module.payload.get("include", ()))
            composed_exclude.extend(module.payload.get("exclude", ()))

        local_include = _string_list(
            edges_config.get("include"), field="edges.include", warnings=warnings
        )
        local_exclude = (
            _string_list(edges_config.get("exclude"), field="edges.exclude", warnings=warnings)
            or []
        )

        # An explicit include is a decision: "draw these relationships, whoever
        # they touch". Without one the relation set is only a default, and a
        # default must not quietly drag the rest of the world back in through
        # artifacts the selection deliberately left out.
        explicit_relations = bool(spec.relations_include) or bool(local_include)

        relation_policy = {
            "composed_include": composed_include,
            "local_include": tuple(local_include) if local_include is not None else None,
            "exclude": tuple(composed_exclude) + tuple(local_exclude),
            "explicit": explicit_relations,
        }
        # Exclusions are applied first and always win, explicit or not.
        policy_passing = {
            relation_id: artifact
            for relation_id, artifact in relation_candidates.items()
            if _relation_passes(artifact, relation_policy)
        }

        if explicit_relations:
            relation_map = policy_passing
        else:
            # Implicit default: the induced subgraph. Keep only relations whose
            # every member is already semantically selected, so a style-only
            # composition still shows the whole graph while a narrowing
            # selection shows exactly its own artifacts.
            #
            # This is one pass, not a fixed point: a relation targeting another
            # relation is admitted whenever that target is a candidate. Deciding
            # whether a reified relation can actually stand is projection's job,
            # and project_view already prunes to a stable visible set and warns.
            # Keeping the two checks separate avoids duplicating reification
            # rules here.
            reachable = frozenset(base_map) | frozenset(policy_passing)
            relation_map = {
                relation_id: artifact
                for relation_id, artifact in policy_passing.items()
                if all(
                    member_id in reachable
                    for member_id, _role in _roles_and_members(artifact)
                )
            }
        explicit_relation_ids = frozenset(relation_map) if explicit_relations else frozenset()

        base_map, relation_map = apply_anchor_policy(
            canon, base_map, relation_map, anchor.as_select() if anchor else {}, warnings=warnings
        )
        # Anchor narrowing is still selection: it decides which artifacts the
        # recipe positively chose. Everything an anchor policy merely kept
        # around is projection support, settled below.
        if anchor is not None:
            semantic_base_ids = frozenset(
                artifact_id
                for artifact_id in base_map
                if _matches_anchor(canon.artifacts[artifact_id], anchor)
            )
        else:
            semantic_base_ids = frozenset(base_map)

        # Endpoint completion is projection integrity, never selection
        # widening. A relation this recipe selected has to be drawable, so its
        # existing renderable endpoints join the projection-support set even
        # when selection excluded them. They never become positive selection
        # results and never touch selection provenance.
        #
        # This reads only the already-selected relations, so it cannot expand
        # through ordinary graph neighbours and needs no recursion: every
        # relation that can become visible is already in relation_map.
        # Only explicitly included relations may add support endpoints. A
        # relation admitted by the implicit default was already induced over
        # the selection, so it has nothing to complete.
        support: dict[str, Artifact] = dict(base_map)
        for relation_id, relation in relation_map.items():
            if relation_id not in explicit_relation_ids:
                continue
            for member_id, _role in _roles_and_members(relation):
                if member_id in support:
                    continue
                endpoint = canon.artifacts.get(member_id)
                if endpoint is None:
                    # Never invent an endpoint. A genuinely missing member keeps
                    # the existing not-whole warning and relation omission.
                    continue
                if endpoint.kind in {"relation", "type"}:
                    # Relation exclusions still win: a relation endpoint becomes
                    # visible only by passing relation policy itself, and type
                    # vocabulary is never a graph node.
                    continue
                support[member_id] = endpoint

        base_map = {
            artifact_id: artifact
            for artifact_id, artifact in canon.artifacts.items()
            if artifact_id in support
        }
        endpoint_completions = frozenset(base_map) - semantic_base_ids
        if endpoint_completions:
            diagnostics.append(
                Diagnostic(
                    severity="warning",
                    code="selection.endpoint-completion",
                    message=(
                        f"{view.relative_path}: {len(endpoint_completions)} "
                        "artifact(s) kept only to leave a selected relation "
                        f"whole (first: {sorted(endpoint_completions)[0]})"
                    ),
                    detail={"artifacts": sorted(endpoint_completions)},
                )
            )

    # Stage 3/4: lenses resolve first and own structure; the style cascade then
    # settles presentation properties on top of them. Both accept view-local
    # rules even without a compose block.
    lens_rules = _collect_rules(
        spec.lenses,
        data.get("lenses"),
        layer="lenses",
        view_path=view.relative_path,
        validate=validate_lens_rules,
    )
    style_rules = _collect_rules(
        spec.styles,
        data.get("styles"),
        layer="styles",
        view_path=view.relative_path,
        validate=validate_style_rules,
    )
    lens_overrides, style_overrides, property_sources, cascade_diagnostics = _resolve_cascade(
        canon, frozenset(base_map) | frozenset(relation_map), lens_rules, style_rules
    )
    diagnostics.extend(cascade_diagnostics)

    if not base_map and not relation_map:
        diagnostics.append(
            Diagnostic(
                severity="warning",
                code="selection.empty",
                message=f"{view.relative_path}: the effective selection is empty",
                detail={},
            )
        )

    provenance = {
        "compiler_schema": COMPILER_SCHEMA,
        "kernel_version": str(canon.world.get("kernel_version", "")),
        "view": {
            "name": view.name,
            "path": view.relative_path,
            "content_hash": _normalized_hash(dict(data)),
            "composed": composed,
        },
        "modules": [module.provenance() for module in spec.modules()],
        "type_fingerprint": _relevant_type_fingerprint(
            canon, frozenset(base_map) | frozenset(relation_map)
        ),
    }

    return CompiledViewPlan(
        view_name=view.name,
        render=view.render,
        layout=layout,
        composed=composed,
        base_ids=frozenset(base_map),
        relation_ids=frozenset(relation_map),
        emphasis=emphasis,
        anchor=anchor,
        relation_policy=relation_policy,
        selection_sources={
            role: dict(entries) for role, entries in selection_sources.items()
        },
        endpoint_completions=endpoint_completions,
        diagnostics=tuple(diagnostics),
        provenance=provenance,
        warnings=tuple(warnings),
        semantic_base_ids=semantic_base_ids,
        explicit_relation_ids=explicit_relation_ids & frozenset(relation_map),
        style_rules=tuple(style_rules),
        lens_rules=tuple(lens_rules),
        lens_overrides=lens_overrides,
        style_overrides=style_overrides,
        property_sources=property_sources,
    )


def _matches_anchor(artifact: Artifact, anchor: AnchorPolicy) -> bool:
    """Mirror the anchor test projection applies, for provenance only.

    An explicitly empty anchor list matches nothing, unlike an omitted one.
    """
    if anchor.kinds is not None and artifact.kind not in anchor.kinds:
        return False
    if anchor.types is not None:
        return any(
            fnmatchcase(artifact.type, pattern)
            if artifact.type is not None
            else pattern in {"*", "<untyped>"}
            for pattern in anchor.types
        )
    return True
