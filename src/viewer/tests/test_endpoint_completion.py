"""Endpoint completion is projection integrity, never selection resurrection."""

from __future__ import annotations

import json
import unittest

from tests.test_compile import CompositionTestCase
from viewer.compile import compile_view
from viewer.explain import explain_artifact, format_explanation
from viewer.load import load_canon, load_view
from viewer.modules import load_module_index
from viewer.project import project_view
from viewer.validate_view import validate_view


class EndpointCompletionTestCase(CompositionTestCase):
    def build(self, relative_view: str):
        canon = load_canon(self.root)
        view = load_view(self.root, relative_view)
        plan = compile_view(canon, view, index=load_module_index(self.root))
        findings: list[dict] = []
        projection = project_view(canon, view, plan=plan, findings=findings)
        return canon, view, plan, projection, findings

    def leadership_view(self, name: str = "leadership-only") -> str:
        return self.world.view(
            name,
            """\
            name: People and leadership
            compose:
              selection:
                any_of: [people]
              relations:
                include: [leadership]
            """,
        )


class CompletedRelationRendersTests(EndpointCompletionTestCase):
    def test_selected_relation_renders_with_its_completed_endpoint(self) -> None:
        _, _, _, projection, _ = self.build(self.leadership_view())

        node_ids = {node["id"] for node in projection["nodes"]}
        edge_ids = {edge["id"] for edge in projection["edges"]}

        self.assertIn("entities/tomas", node_ids)
        self.assertIn("entities/guild", node_ids)
        self.assertIn("relations/tomas-leads-guild", edge_ids)

    def test_completed_endpoint_is_support_not_semantic_selection(self) -> None:
        _, _, plan, _, _ = self.build(self.leadership_view())

        self.assertNotIn("entities/guild", plan.semantic_base_ids)
        self.assertIn("entities/guild", plan.base_ids)
        self.assertIn("entities/guild", plan.endpoint_completions)
        # Provenance is untouched: no selection module claims the guild.
        for role, modules in plan.selection_sources.items():
            for module_id, chosen in modules.items():
                self.assertNotIn(
                    "entities/guild", chosen, f"{role}/{module_id} claimed the guild"
                )

    def test_completion_reports_itself_as_a_diagnostic(self) -> None:
        _, _, plan, _, _ = self.build(self.leadership_view())

        completion = next(
            item
            for item in plan.diagnostics
            if item.code == "selection.endpoint-completion"
        )

        self.assertIn("entities/guild", completion.detail["artifacts"])
        self.assertIn("leave a selected relation", completion.message)

    def test_no_relation_not_whole_finding_for_a_completed_relation(self) -> None:
        canon, view, _, projection, findings = self.build(self.leadership_view())

        self.assertNotIn(
            "structure.relation-not-whole", {finding["code"] for finding in findings}
        )
        self.assertFalse(
            any("relation omitted" in warning for warning in projection["warnings"])
        )

        result = validate_view(canon, view, index=load_module_index(self.root))
        self.assertTrue(result.ok, result.errors)


class CompletionExplanationTests(EndpointCompletionTestCase):
    def _trace(self):
        canon, _, plan, projection, _ = self.build(self.leadership_view())
        return explain_artifact(canon, plan, projection, "entities/guild")

    def test_json_trace_separates_selection_from_display(self) -> None:
        trace = self._trace()
        selection = trace["selection"]

        self.assertFalse(selection["included"])
        self.assertTrue(selection["displayed"])
        self.assertTrue(selection["endpoint_completion"])
        self.assertEqual(selection["semantic_outcome"], "not selected")
        self.assertIn("independently selected relation", selection["reason"])
        self.assertEqual(
            json.loads(json.dumps(trace, default=str))["selection"]["endpoint_completion"],
            True,
        )

    def test_human_trace_states_both_outcomes(self) -> None:
        text = format_explanation(self._trace())

        self.assertIn("semantically selected: no", text)
        self.assertIn("shown in the projection: yes", text)
        self.assertIn("endpoint completion", text)


class ExcludedEndpointTests(EndpointCompletionTestCase):
    def _excluded_view(self) -> str:
        self.world.module(
            "guild-only",
            "selection",
            "select:\n  kinds: [entity]\n  types: [community/polity]\n",
        )
        return self.world.view(
            "excluded-endpoint",
            """\
            name: Excluded endpoint
            compose:
              selection:
                any_of: [people, organizations]
                exclude: [guild-only]
              relations:
                include: [leadership]
            """,
        )

    def test_an_excluded_endpoint_is_displayed_but_never_resurrected(self) -> None:
        canon, _, plan, projection, _ = self.build(self._excluded_view())

        self.assertNotIn("entities/guild", plan.semantic_base_ids)
        self.assertIn("entities/guild", plan.endpoint_completions)
        self.assertIn(
            "entities/guild", {node["id"] for node in projection["nodes"]}
        )

        trace = explain_artifact(canon, plan, projection, "entities/guild")
        selection = trace["selection"]

        self.assertFalse(selection["included"])
        self.assertTrue(selection["displayed"])
        self.assertEqual(selection["excluded_by"], ["guild-only"])
        self.assertIn("excluded by compose.selection.exclude", selection["semantic_outcome"])
        self.assertIn("not selection resurrection", selection["reason"])


class ExclusionStillWinsTests(EndpointCompletionTestCase):
    def test_an_excluded_relation_adds_no_endpoints(self) -> None:
        path = self.world.view(
            "relation-excluded",
            """\
            name: Relation excluded
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
        self.assertEqual(plan.endpoint_completions, frozenset())
        self.assertNotIn("entities/guild", plan.base_ids)
        self.assertNotIn(
            "entities/guild", {node["id"] for node in projection["nodes"]}
        )

    def test_completion_never_admits_a_relation_endpoint_that_policy_excluded(self) -> None:
        # A relation whose member is another relation must not drag that
        # excluded relation back in as a node.
        self.world.write(
            "relations/comment-on-leadership.md",
            "---\nid: relations/comment-on-leadership\nkind: relation\ntype: participates\n"
            "members:\n  - {id: relations/tomas-leads-guild, role: subject}\n"
            "  - {id: entities/mara, role: witness}\n---\n\nAbout the leadership.\n",
        )
        self.world.module(
            "commentary", "relation", "edges:\n  include: [participates]\n"
        )
        path = self.world.view(
            "reified-excluded",
            """\
            name: Reified excluded
            compose:
              selection:
                any_of: [people]
              relations:
                include: [commentary]
            """,
        )

        _, _, plan, projection, findings = self.build(path)

        self.assertNotIn("relations/tomas-leads-guild", plan.relation_ids)
        self.assertNotIn("relations/tomas-leads-guild", plan.base_ids)
        self.assertIn(
            "structure.relation-not-whole", {finding["code"] for finding in findings}
        )


class MissingEndpointTests(EndpointCompletionTestCase):
    def test_a_nonexistent_endpoint_is_never_fabricated(self) -> None:
        self.world.write(
            "relations/tomas-leads-ghost.md",
            "---\nid: relations/tomas-leads-ghost\nkind: relation\ntype: leads\n"
            "members:\n  - {id: entities/tomas, role: leader}\n"
            "  - {id: entities/ghost-guild, role: body}\n---\n\nDangling.\n",
        )
        path = self.leadership_view("ghost-endpoint")

        canon, view, plan, projection, findings = self.build(path)

        self.assertNotIn("entities/ghost-guild", plan.base_ids)
        self.assertNotIn(
            "entities/ghost-guild", {node["id"] for node in projection["nodes"]}
        )
        self.assertNotIn(
            "relations/tomas-leads-ghost", {edge["id"] for edge in projection["edges"]}
        )
        self.assertIn(
            "structure.relation-not-whole", {finding["code"] for finding in findings}
        )

        result = validate_view(canon, view, index=load_module_index(self.root))
        self.assertFalse(result.ok)
        self.assertIn(
            "structure.relation-not-whole", {item["code"] for item in result.errors}
        )


class LegacyViewUnchangedTests(EndpointCompletionTestCase):
    def test_a_legacy_view_still_drops_the_relation_and_only_warns(self) -> None:
        # No compose block: selecting people but not the guild must keep the
        # pre-composition behaviour of omitting the relation with a warning,
        # never completing the endpoint and never failing validation.
        path = self.world.view(
            "legacy-not-whole",
            """\
            name: Legacy not whole
            select:
              kinds: [entity, relation]
              types: [person]
            """,
        )

        canon, view, plan, projection, findings = self.build(path)

        self.assertFalse(plan.composed)
        self.assertEqual(plan.endpoint_completions, frozenset())
        self.assertNotIn("entities/guild", plan.base_ids)
        self.assertNotIn(
            "relations/tomas-leads-guild", {edge["id"] for edge in projection["edges"]}
        )
        self.assertIn(
            "structure.relation-not-whole", {finding["code"] for finding in findings}
        )

        result = validate_view(canon, view, index=load_module_index(self.root))

        self.assertTrue(result.ok, result.errors)
        self.assertIn(
            "structure.relation-not-whole", {item["code"] for item in result.warnings}
        )
        self.assertNotIn(
            "structure.relation-not-whole", {item["code"] for item in result.errors}
        )


class NoGraphTraversalTests(EndpointCompletionTestCase):
    def test_completion_stops_at_one_hop_and_does_not_walk_the_graph(self) -> None:
        # The guild is completed for the leadership relation. Its own further
        # neighbours must not follow it in, because part_of was never selected.
        _, _, plan, _, _ = self.build(self.leadership_view())

        self.assertEqual(plan.relation_ids, frozenset({"relations/tomas-leads-guild"}))
        self.assertIn("entities/guild", plan.base_ids)
        self.assertNotIn("entities/port", plan.base_ids)
        # Completion added exactly the one endpoint the selected relation needed.
        self.assertEqual(plan.endpoint_completions, frozenset({"entities/guild"}))


if __name__ == "__main__":
    unittest.main()
