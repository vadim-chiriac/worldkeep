from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import textwrap
import unittest

from viewer.compile import CompileError, compile_view
from viewer.load import load_canon, load_view
from viewer.modules import MODULE_SCHEMA, load_module_index


def _artifact(kind: str, artifact_id: str, *, type_: str | None = None, **extra: object) -> str:
    lines = [f"id: {artifact_id}", f"kind: {kind}"]
    if type_:
        lines.append(f"type: {type_}")
    for key, value in extra.items():
        lines.append(f"{key}: {value}")
    body = "\n".join(lines)
    return f"---\n{body}\n---\n\nBody text.\n"


class CompositionWorld:
    """A small world with overlapping membership, built once per test."""

    def __init__(self, directory: Path) -> None:
        self.root = directory / "world"
        (self.root / "entities").mkdir(parents=True)
        (self.root / "relations").mkdir(parents=True)
        (self.root / "types").mkdir(parents=True)
        (self.root / "views").mkdir(parents=True)
        (self.root / "view-modules").mkdir(parents=True)
        (self.root / "world.yaml").write_text(
            'kernel_version: "0.11"\nname: "Composition World"\n', encoding="utf-8"
        )

        # Tomas is both a person and a merchant: overlapping membership.
        self.write("entities/tomas.md", _artifact("entity", "entities/tomas", type_="person"))
        self.write("entities/mara.md", _artifact("entity", "entities/mara", type_="person"))
        self.write(
            "entities/guild.md",
            _artifact("entity", "entities/guild", type_="community/polity"),
        )
        self.write(
            "entities/port.md",
            _artifact("entity", "entities/port", type_="place/settlement"),
        )
        self.write(
            "entities/secret.md",
            _artifact("entity", "entities/secret", type_="person", tags="[private]"),
        )
        self.write(
            "types/leads.md",
            "---\nid: types/leads\nkind: type\napplies_to_kind: relation\n"
            "lens:\n  as: edge\n  direction: [leader, body]\n---\n\nLeads.\n",
        )
        self.write(
            "relations/tomas-leads-guild.md",
            "---\nid: relations/tomas-leads-guild\nkind: relation\ntype: leads\n"
            "members:\n  - {id: entities/tomas, role: leader}\n"
            "  - {id: entities/guild, role: body}\n---\n\nLeads.\n",
        )
        self.write(
            "relations/mara-member-guild.md",
            "---\nid: relations/mara-member-guild\nkind: relation\n"
            "type: part_of/membership\n"
            "members:\n  - {id: entities/mara, role: part}\n"
            "  - {id: entities/guild, role: whole}\n---\n\nMember.\n",
        )
        self.write(
            "relations/guild-in-port.md",
            "---\nid: relations/guild-in-port\nkind: relation\ntype: part_of\n"
            "members:\n  - {id: entities/guild, role: part}\n"
            "  - {id: entities/port, role: whole}\n---\n\nIn port.\n",
        )

        self.module(
            "people",
            "selection",
            "select:\n  kinds: [entity]\n  types: [person]\n",
        )
        self.module(
            "organizations",
            "selection",
            "select:\n  kinds: [entity]\n  types: [community/polity]\n",
        )
        self.module(
            "settlements",
            "selection",
            "select:\n  kinds: [entity]\n  types: [place/*]\n",
        )
        self.module(
            "private-notes",
            "selection",
            "select:\n  tags: [private]\n",
        )
        self.module(
            "named-people",
            "selection",
            "select:\n  kinds: [entity]\n  types: [person, community/polity]\n",
        )
        self.module(
            "leadership",
            "relation",
            "edges:\n  include: [leads]\n",
        )
        self.module(
            "affiliations",
            "relation",
            "edges:\n  include: [part_of/membership]\n",
        )
        self.module(
            "containment",
            "relation",
            "edges:\n  include: [part_of]\n",
        )
        self.module(
            "no-relations",
            "relation",
            "edges:\n  exclude: ['*']\n",
        )
        self.module(
            "anchored-people",
            "selection",
            "select:\n  kinds: [entity]\n  types: [person]\n"
            "  connected_to_types: [community/polity]\n",
        )
        self.module(
            "anchored-places",
            "selection",
            "select:\n  kinds: [entity]\n  types: [place/*]\n"
            "  connected_to_types: [place/*]\n",
        )
        self.module(
            "anchored-graph",
            "selection",
            "select:\n  kinds: [entity, relation]\n"
            "  connected_to_types: [community/polity]\n",
        )
        self.module(
            "anchored-people-twin",
            "selection",
            "select:\n  kinds: [entity]\n  types: [person, community/polity]\n"
            "  connected_to_types: [community/polity]\n",
        )

    def write(self, relative: str, text: str) -> None:
        (self.root / relative).write_text(text, encoding="utf-8")

    def module(self, module_id: str, kind: str, payload: str) -> None:
        text = textwrap.dedent(
            f"""\
            schema: {MODULE_SCHEMA}
            id: {module_id}
            version: 1
            kind: {kind}
            """
        ) + payload
        self.write(f"view-modules/{module_id}.yaml", text)

    def view(self, name: str, text: str) -> str:
        self.write(f"views/{name}.yaml", textwrap.dedent(text))
        return f"views/{name}.yaml"


class CompositionTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._directory = TemporaryDirectory()
        self.world = CompositionWorld(Path(self._directory.name))
        self.root = self.world.root

    def tearDown(self) -> None:
        self._directory.cleanup()

    def compile(self, relative_view: str):
        canon = load_canon(self.root)
        view = load_view(self.root, relative_view)
        return compile_view(canon, view, index=load_module_index(self.root))


class SelectionAlgebraTests(CompositionTestCase):
    def test_any_of_unions_its_modules(self) -> None:
        path = self.world.view(
            "union",
            """\
            name: Union
            compose:
              selection:
                any_of: [people, organizations]
            """,
        )

        plan = self.compile(path)

        self.assertEqual(
            plan.semantic_base_ids,
            frozenset(
                {"entities/tomas", "entities/mara", "entities/secret", "entities/guild"}
            ),
        )

    def test_all_of_intersects_after_any_of(self) -> None:
        path = self.world.view(
            "intersection",
            """\
            name: Intersection
            compose:
              selection:
                any_of: [people, organizations]
                all_of: [named-people, people]
            """,
        )

        plan = self.compile(path)

        self.assertEqual(
            plan.semantic_base_ids,
            frozenset({"entities/tomas", "entities/mara", "entities/secret"}),
        )

    def test_exclude_subtracts_and_local_select_cannot_resurrect(self) -> None:
        path = self.world.view(
            "excluded",
            """\
            name: Excluded
            compose:
              selection:
                any_of: [people]
                exclude: [private-notes]
            select:
              tags: [private]
            """,
        )

        plan = self.compile(path)

        self.assertNotIn("entities/secret", plan.base_ids)
        self.assertEqual(plan.base_ids, frozenset())
        codes = {item.code for item in plan.diagnostics}
        self.assertIn("selection.no-resurrection", codes)
        self.assertIn("selection.empty", codes)

    def test_local_select_narrows_without_widening(self) -> None:
        path = self.world.view(
            "narrowed",
            """\
            name: Narrowed
            compose:
              selection:
                any_of: [people, organizations]
            select:
              types: [community/polity]
            """,
        )

        plan = self.compile(path)

        self.assertEqual(plan.semantic_base_ids, frozenset({"entities/guild"}))

    def test_absent_any_of_uses_the_ordinary_candidate_set(self) -> None:
        path = self.world.view(
            "everything-styled",
            """\
            name: Whole world with styles
            compose:
              selection:
                exclude: [private-notes]
            """,
        )

        plan = self.compile(path)

        self.assertIn("entities/tomas", plan.base_ids)
        self.assertIn("entities/port", plan.base_ids)
        self.assertNotIn("entities/secret", plan.base_ids)

    def test_empty_any_of_is_rejected(self) -> None:
        path = self.world.view(
            "empty-any-of",
            """\
            name: Empty
            compose:
              selection:
                any_of: []
            """,
        )

        with self.assertRaisesRegex(CompileError, "any_of is present but empty"):
            self.compile(path)

    def test_selection_sources_record_each_contributing_module(self) -> None:
        path = self.world.view(
            "traced",
            """\
            name: Traced
            compose:
              selection:
                any_of: [people, organizations]
                exclude: [private-notes]
            """,
        )

        plan = self.compile(path)

        self.assertEqual(set(plan.selection_sources["any_of"]), {"people", "organizations"})
        self.assertIn("entities/tomas", plan.selection_sources["any_of"]["people"])
        self.assertIn("entities/secret", plan.selection_sources["exclude"]["private-notes"])


class AnchorPolicyTests(CompositionTestCase):
    def test_identical_anchor_policies_coalesce(self) -> None:
        path = self.world.view(
            "coalesced",
            """\
            name: Coalesced
            compose:
              selection:
                any_of: [anchored-people, anchored-people-twin]
            """,
        )

        plan = self.compile(path)

        self.assertIsNotNone(plan.anchor)
        self.assertEqual(plan.anchor.types, ("community/polity",))
        self.assertEqual(len(plan.anchor.sources), 2)

    def test_different_anchor_policies_are_a_compile_error(self) -> None:
        path = self.world.view(
            "conflicting",
            """\
            name: Conflicting
            compose:
              selection:
                any_of: [anchored-people, anchored-places]
            """,
        )

        with self.assertRaisesRegex(CompileError, "incompatible connected-anchor policies"):
            self.compile(path)

    def test_endpoint_completion_is_reported_not_hidden(self) -> None:
        path = self.world.view(
            "anchored",
            """\
            name: Anchored
            compose:
              selection:
                any_of: [anchored-graph]
            """,
        )

        plan = self.compile(path)

        # Only the guild matches the anchor. Everything else survives solely as
        # an endpoint of a selected relation, and that must stay visible.
        self.assertIn("entities/guild", plan.base_ids)
        self.assertEqual(
            plan.endpoint_completions,
            frozenset({"entities/tomas", "entities/mara", "entities/port"}),
        )
        self.assertIn(
            "selection.endpoint-completion",
            {item.code for item in plan.diagnostics},
        )


class RelationAlgebraTests(CompositionTestCase):
    def test_relation_includes_union(self) -> None:
        path = self.world.view(
            "both-relations",
            """\
            name: Both
            compose:
              relations:
                include: [leadership, affiliations]
            """,
        )

        plan = self.compile(path)

        self.assertEqual(
            plan.relation_ids,
            frozenset({"relations/tomas-leads-guild", "relations/mara-member-guild"}),
        )

    def test_module_excludes_subtract_and_win(self) -> None:
        path = self.world.view(
            "subtracted",
            """\
            name: Subtracted
            compose:
              relations:
                include: [leadership, affiliations]
                exclude: [leadership]
            """,
        )

        plan = self.compile(path)

        self.assertEqual(plan.relation_ids, frozenset({"relations/mara-member-guild"}))

    def test_local_include_narrows_the_composed_include(self) -> None:
        path = self.world.view(
            "narrowed-relations",
            """\
            name: Narrowed relations
            compose:
              relations:
                include: [leadership, affiliations]
            edges:
              include: [leads]
            """,
        )

        plan = self.compile(path)

        self.assertEqual(plan.relation_ids, frozenset({"relations/tomas-leads-guild"}))

    def test_local_exclude_adds_to_the_exclusion_set(self) -> None:
        path = self.world.view(
            "locally-excluded",
            """\
            name: Locally excluded
            compose:
              relations:
                include: [leadership, affiliations]
            edges:
              exclude: [leads]
            """,
        )

        plan = self.compile(path)

        self.assertEqual(plan.relation_ids, frozenset({"relations/mara-member-guild"}))

    def test_local_include_cannot_resurrect_an_excluded_relation(self) -> None:
        path = self.world.view(
            "no-relation-resurrection",
            """\
            name: No resurrection
            compose:
              relations:
                include: [leadership, affiliations]
                exclude: [leadership]
            edges:
              include: [leads]
            """,
        )

        plan = self.compile(path)

        self.assertEqual(plan.relation_ids, frozenset())


class ModuleReferenceTests(CompositionTestCase):
    def test_kind_mismatch_in_a_compose_section_fails(self) -> None:
        path = self.world.view(
            "mismatch",
            """\
            name: Mismatch
            compose:
              selection:
                any_of: [leadership]
            """,
        )

        with self.assertRaisesRegex(CompileError, "requires kind 'selection'"):
            self.compile(path)

    def test_missing_module_fails(self) -> None:
        path = self.world.view(
            "missing",
            """\
            name: Missing
            compose:
              selection:
                any_of: [ghosts]
            """,
        )

        with self.assertRaisesRegex(CompileError, "no module with id 'ghosts'"):
            self.compile(path)

    def test_unknown_compose_field_fails(self) -> None:
        path = self.world.view(
            "unknown-field",
            """\
            name: Unknown
            compose:
              selection:
                any_of: [people]
              emphasis: [something]
            """,
        )

        with self.assertRaisesRegex(CompileError, "unknown field.*'emphasis'"):
            self.compile(path)

    def test_duplicate_reference_in_one_section_fails(self) -> None:
        path = self.world.view(
            "duplicate-ref",
            """\
            name: Duplicate
            compose:
              selection:
                any_of: [people, people]
            """,
        )

        with self.assertRaisesRegex(CompileError, "referenced twice"):
            self.compile(path)

    def test_path_reference_is_rejected(self) -> None:
        path = self.world.view(
            "path-ref",
            """\
            name: Path
            compose:
              selection:
                any_of: ["../people"]
            """,
        )

        with self.assertRaisesRegex(CompileError, "must be a bare module id"):
            self.compile(path)


class ProvenanceTests(CompositionTestCase):
    def test_provenance_records_modules_view_and_schema_versions(self) -> None:
        path = self.world.view(
            "provenance",
            """\
            name: Provenance
            compose:
              selection:
                any_of: [people]
              relations:
                include: [leadership]
            """,
        )

        plan = self.compile(path)
        provenance = plan.provenance

        self.assertEqual(provenance["compiler_schema"], "wb.view-compiler/v1")
        self.assertEqual(provenance["kernel_version"], "0.11")
        self.assertEqual(provenance["view"]["path"], path)
        self.assertTrue(provenance["view"]["composed"])
        self.assertEqual(
            [module["id"] for module in provenance["modules"]], ["people", "leadership"]
        )
        for module in provenance["modules"]:
            self.assertEqual(module["schema"], MODULE_SCHEMA)
            self.assertTrue(module["path"].startswith("view-modules/"))
            self.assertEqual(len(module["content_hash"]), 64)

    def test_fingerprint_changes_when_a_module_changes(self) -> None:
        path = self.world.view(
            "fingerprint",
            """\
            name: Fingerprint
            compose:
              selection:
                any_of: [people]
            """,
        )
        before = self.compile(path).fingerprint()

        self.world.module(
            "people", "selection", "select:\n  kinds: [entity]\n  types: [person, person/*]\n"
        )
        after = self.compile(path).fingerprint()

        self.assertNotEqual(before, after)

    def test_fingerprint_ignores_canon_body_changes(self) -> None:
        path = self.world.view(
            "body-stable",
            """\
            name: Body stable
            compose:
              selection:
                any_of: [people]
            """,
        )
        before = self.compile(path).fingerprint()

        self.world.write(
            "entities/tomas.md",
            "---\nid: entities/tomas\nkind: entity\ntype: person\n---\n\nCompletely new prose.\n",
        )
        after = self.compile(path).fingerprint()

        self.assertEqual(before, after)


class LegacyCompatibilityTests(CompositionTestCase):
    def test_view_without_compose_uses_the_plain_selector(self) -> None:
        path = self.world.view(
            "legacy",
            """\
            name: Legacy
            select:
              kinds: [entity]
              types: [person]
            """,
        )

        plan = self.compile(path)

        self.assertFalse(plan.composed)
        self.assertEqual(plan.provenance["modules"], [])
        self.assertEqual(
            plan.base_ids,
            frozenset({"entities/tomas", "entities/mara", "entities/secret"}),
        )

    def test_legacy_status_selection_is_not_narrowed_by_a_default_candidate_set(self) -> None:
        self.world.write(
            "entities/old.md",
            "---\nid: entities/old\nkind: entity\ntype: person\nstatus: deprecated\n---\n\nOld.\n",
        )
        path = self.world.view(
            "deprecated-only",
            """\
            name: Deprecated only
            select:
              kinds: [entity]
              status: [deprecated]
            """,
        )

        plan = self.compile(path)

        self.assertEqual(plan.base_ids, frozenset({"entities/old"}))


if __name__ == "__main__":
    unittest.main()
