"""Implicit relation defaults induce; explicit includes stay independent.

Without an explicit include the relation set is only a default, so it must not
drag artifacts the selection deliberately left out back in through the world's
other relationships. Naming a relation module — or a view-local
``edges.include`` — is the deliberate opt-in to that expansion.
"""

from __future__ import annotations

import unittest

from tests.test_compile import CompositionTestCase
from viewer.compile import compile_view
from viewer.explain import explain_artifact, format_explanation
from viewer.load import builtin_everything, load_canon, load_view
from viewer.modules import load_module_index
from viewer.project import project_view
from viewer.validate_view import validate_view


class RelationDefaultTestCase(CompositionTestCase):
    def build(self, relative_view: str):
        canon = load_canon(self.root)
        view = load_view(self.root, relative_view)
        plan = compile_view(canon, view, index=load_module_index(self.root))
        findings: list[dict] = []
        projection = project_view(canon, view, plan=plan, findings=findings)
        return canon, view, plan, projection, findings

    def node_ids(self, projection) -> set[str]:
        return {node["id"] for node in projection["nodes"]}

    def edge_ids(self, projection) -> set[str]:
        return {edge["id"] for edge in projection["edges"]}


class StyleOnlyCompositionTests(RelationDefaultTestCase):
    def test_a_style_only_composition_still_shows_the_whole_graph(self) -> None:
        self.world.module(
            "palette",
            "style",
            'rules:\n  - match: {kind: entity, type: person}\n    set: {color: "#5d78a6"}\n',
        )
        path = self.world.view(
            "style-only",
            """\
            name: Style only
            compose:
              styles: [palette]
            """,
        )

        _, _, plan, projection, _ = self.build(path)

        self.assertEqual(
            self.node_ids(projection),
            {
                "entities/tomas",
                "entities/mara",
                "entities/guild",
                "entities/port",
                "entities/secret",
            },
        )
        self.assertEqual(
            self.edge_ids(projection),
            {
                "relations/tomas-leads-guild",
                "relations/mara-member-guild",
                "relations/guild-in-port",
            },
        )
        # Nothing was completed, because nothing was missing.
        self.assertEqual(plan.endpoint_completions, frozenset())
        self.assertEqual(plan.explicit_relation_ids, frozenset())


class InducedSubgraphTests(RelationDefaultTestCase):
    def test_selection_only_composition_induces_and_never_expands(self) -> None:
        path = self.world.view(
            "selection-only",
            """\
            name: Selection only
            compose:
              selection:
                any_of: [people]
            """,
        )

        _, _, plan, projection, _ = self.build(path)

        self.assertEqual(
            self.node_ids(projection),
            {"entities/tomas", "entities/mara", "entities/secret"},
        )
        # No relation lies wholly inside the selection, so none is drawn and
        # nothing is pulled back in to make one whole.
        self.assertEqual(self.edge_ids(projection), set())
        self.assertEqual(plan.relation_ids, frozenset())
        self.assertEqual(plan.endpoint_completions, frozenset())
        self.assertNotIn("entities/guild", plan.base_ids)
        self.assertNotIn("entities/port", plan.base_ids)

    def test_induced_relations_appear_when_both_endpoints_are_selected(self) -> None:
        path = self.world.view(
            "induced",
            """\
            name: Induced
            compose:
              selection:
                any_of: [people, organizations]
            """,
        )

        _, _, plan, projection, _ = self.build(path)

        self.assertEqual(
            self.edge_ids(projection),
            {"relations/tomas-leads-guild", "relations/mara-member-guild"},
        )
        # The guild is in the port, but the port was never selected, so that
        # containment is simply not part of the induced subgraph.
        self.assertNotIn("relations/guild-in-port", plan.relation_ids)
        self.assertNotIn("entities/port", plan.base_ids)
        self.assertEqual(plan.endpoint_completions, frozenset())

    def test_an_induced_relation_is_explained_as_an_implicit_default(self) -> None:
        path = self.world.view(
            "induced-explained",
            """\
            name: Induced explained
            compose:
              selection:
                any_of: [people, organizations]
            """,
        )

        canon, _, plan, projection, _ = self.build(path)
        trace = explain_artifact(
            canon, plan, projection, "relations/tomas-leads-guild"
        )

        self.assertTrue(trace["relation_policy"]["included"])
        self.assertFalse(trace["relation_policy"]["explicit"])
        self.assertIn("implicit default", trace["relation_policy"]["admitted_by"])
        self.assertIn("implicit default", format_explanation(trace))

    def test_an_incomplete_induced_relation_does_not_fail_validation(self) -> None:
        canon, view, _, _, _ = self.build(
            self.world.view(
                "induced-valid",
                """\
                name: Induced valid
                compose:
                  selection:
                    any_of: [people]
                """,
            )
        )

        result = validate_view(canon, view, index=load_module_index(self.root))

        self.assertTrue(result.ok, result.errors)


class ExplicitIncludeTests(RelationDefaultTestCase):
    def test_an_explicit_module_include_adds_required_support_endpoints(self) -> None:
        path = self.world.view(
            "explicit-module",
            """\
            name: Explicit module
            compose:
              selection:
                any_of: [people]
              relations:
                include: [leadership]
            """,
        )

        canon, _, plan, projection, _ = self.build(path)

        self.assertIn("relations/tomas-leads-guild", self.edge_ids(projection))
        self.assertIn("entities/guild", self.node_ids(projection))
        self.assertEqual(plan.endpoint_completions, frozenset({"entities/guild"}))
        self.assertEqual(
            plan.explicit_relation_ids, frozenset({"relations/tomas-leads-guild"})
        )

        trace = explain_artifact(canon, plan, projection, "relations/tomas-leads-guild")
        self.assertTrue(trace["relation_policy"]["explicit"])
        self.assertIn("explicit relation include", trace["relation_policy"]["admitted_by"])

    def test_local_edges_include_behaves_as_an_explicit_include(self) -> None:
        path = self.world.view(
            "explicit-local",
            """\
            name: Explicit local
            compose:
              selection:
                any_of: [people]
            edges:
              include: [leads]
            """,
        )

        _, _, plan, projection, _ = self.build(path)

        self.assertIn("relations/tomas-leads-guild", self.edge_ids(projection))
        self.assertIn("entities/guild", self.node_ids(projection))
        self.assertEqual(plan.endpoint_completions, frozenset({"entities/guild"}))
        self.assertEqual(
            plan.explicit_relation_ids, frozenset({"relations/tomas-leads-guild"})
        )

    def test_an_empty_local_include_is_not_an_explicit_decision(self) -> None:
        path = self.world.view(
            "empty-include",
            """\
            name: Empty include
            compose:
              selection:
                any_of: [people]
            edges:
              include: []
            """,
        )

        _, _, plan, projection, _ = self.build(path)

        self.assertEqual(plan.explicit_relation_ids, frozenset())
        self.assertEqual(plan.endpoint_completions, frozenset())
        self.assertNotIn("entities/guild", plan.base_ids)


class ExclusionStillWinsTests(RelationDefaultTestCase):
    def test_exclusion_wins_over_an_explicit_include(self) -> None:
        path = self.world.view(
            "excluded-explicit",
            """\
            name: Excluded explicit
            compose:
              selection:
                any_of: [people]
              relations:
                include: [leadership]
                exclude: [leadership]
            """,
        )

        _, _, plan, projection, _ = self.build(path)

        self.assertEqual(plan.relation_ids, frozenset())
        self.assertEqual(plan.explicit_relation_ids, frozenset())
        self.assertEqual(plan.endpoint_completions, frozenset())
        self.assertNotIn("entities/guild", self.node_ids(projection))

    def test_exclusion_wins_over_the_implicit_default(self) -> None:
        path = self.world.view(
            "excluded-implicit",
            """\
            name: Excluded implicit
            compose:
              selection:
                any_of: [people, organizations]
              relations:
                exclude: [leadership]
            """,
        )

        _, _, plan, projection, _ = self.build(path)

        self.assertNotIn("relations/tomas-leads-guild", plan.relation_ids)
        self.assertIn("relations/mara-member-guild", plan.relation_ids)

    def test_local_exclude_wins_over_a_local_include(self) -> None:
        path = self.world.view(
            "local-both",
            """\
            name: Local both
            compose:
              selection:
                any_of: [people]
            edges:
              include: [leads]
              exclude: [leads]
            """,
        )

        _, _, plan, _, _ = self.build(path)

        self.assertEqual(plan.relation_ids, frozenset())
        self.assertEqual(plan.endpoint_completions, frozenset())


class PreservedBehaviourTests(RelationDefaultTestCase):
    def test_semantic_selection_is_unaffected_by_the_relation_default(self) -> None:
        for body, expected in (
            ("compose:\n  selection:\n    any_of: [people]\n", None),
            (
                "compose:\n  selection:\n    any_of: [people]\n"
                "  relations:\n    include: [leadership]\n",
                None,
            ),
        ):
            with self.subTest(body=body):
                path = self.world.view("semantic", f"name: Semantic\n{body}")
                _, _, plan, _, _ = self.build(path)

                self.assertEqual(
                    plan.semantic_base_ids,
                    frozenset(
                        {"entities/tomas", "entities/mara", "entities/secret"}
                    ),
                )
                self.assertFalse(plan.semantic_base_ids & plan.endpoint_completions)

    def test_legacy_views_ignore_the_new_relation_default(self) -> None:
        path = self.world.view(
            "legacy-default",
            """\
            name: Legacy default
            select:
              kinds: [entity, relation]
              types: [person]
            """,
        )

        _, _, plan, projection, findings = self.build(path)

        self.assertFalse(plan.composed)
        self.assertEqual(plan.explicit_relation_ids, frozenset())
        self.assertEqual(plan.endpoint_completions, frozenset())
        # Unchanged legacy behaviour: relations are still candidates and are
        # still dropped with a warning when an endpoint was filtered out.
        self.assertIn("relations/tomas-leads-guild", plan.relation_ids)
        self.assertNotIn("entities/guild", plan.base_ids)
        self.assertIn(
            "structure.relation-not-whole", {finding["code"] for finding in findings}
        )

    def test_everything_is_unaffected_by_composed_relation_defaults(self) -> None:
        self.world.view(
            "narrow",
            """\
            name: Narrow
            compose:
              selection:
                any_of: [people]
            """,
        )
        canon = load_canon(self.root)

        projection = project_view(canon, builtin_everything())

        self.assertEqual(
            self.node_ids(projection),
            {
                "entities/tomas",
                "entities/mara",
                "entities/guild",
                "entities/port",
                "entities/secret",
            },
        )
        self.assertEqual(len(projection["edges"]), 3)


if __name__ == "__main__":
    unittest.main()
