from __future__ import annotations

import unittest

from tests.test_compile import CompositionTestCase


class StyleCascadeTests(CompositionTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.world.module(
            "faction-colors",
            "style",
            'rules:\n'
            '  - match: {kind: entity, type: person}\n'
            '    set: {color: "#5d78a6", shape: ellipse}\n',
        )
        self.world.module(
            "office-emphasis",
            "style",
            'rules:\n'
            '  - match: {kind: entity, type: person}\n'
            '    set: {color: "#c9a227"}\n',
        )

    def test_later_module_wins_only_the_property_it_sets(self) -> None:
        path = self.world.view(
            "cascade",
            """\
            name: Cascade
            compose:
              selection:
                any_of: [people]
              styles: [faction-colors, office-emphasis]
            """,
        )

        plan = self.compile(path)
        overrides = plan.overrides_for("entities/tomas")

        self.assertEqual(overrides["color"], "#c9a227")
        # shape was never re-declared, so the earlier module still owns it.
        self.assertEqual(overrides["shape"], "ellipse")

    def test_overlap_warning_names_both_sources_property_and_values(self) -> None:
        path = self.world.view(
            "overlap",
            """\
            name: Overlap
            compose:
              selection:
                any_of: [people]
              styles: [faction-colors, office-emphasis]
            """,
        )

        plan = self.compile(path)
        overlaps = [item for item in plan.diagnostics if item.code == "style.overlap"]
        detail = next(
            item.detail for item in overlaps if item.detail["artifact"] == "entities/tomas"
        )

        self.assertEqual(detail["property"], "color")
        self.assertEqual(detail["winning_value"], "#c9a227")
        self.assertEqual(detail["losing_value"], "#5d78a6")
        self.assertIn("faction-colors", detail["losing_source"])
        self.assertIn("office-emphasis", detail["winning_source"])

    def test_view_local_styles_beat_imported_modules(self) -> None:
        path = self.world.view(
            "local-styles",
            """\
            name: Local styles
            compose:
              selection:
                any_of: [people]
              styles: [faction-colors, office-emphasis]
            styles:
              - match: {kind: entity, type: person}
                set: {color: "#111111"}
            """,
        )

        plan = self.compile(path)

        self.assertEqual(plan.overrides_for("entities/tomas")["color"], "#111111")

    def test_identical_values_do_not_warn(self) -> None:
        self.world.module(
            "office-emphasis",
            "style",
            'rules:\n'
            '  - match: {kind: entity, type: person}\n'
            '    set: {color: "#5d78a6"}\n',
        )
        path = self.world.view(
            "same-value",
            """\
            name: Same value
            compose:
              selection:
                any_of: [people]
              styles: [faction-colors, office-emphasis]
            """,
        )

        plan = self.compile(path)

        self.assertEqual([item for item in plan.diagnostics if item.code == "style.overlap"], [])

    def test_styles_never_apply_to_artifacts_outside_the_projection(self) -> None:
        path = self.world.view(
            "scoped",
            """\
            name: Scoped
            compose:
              selection:
                any_of: [organizations]
              relations:
                exclude: [no-relations]
              styles: [faction-colors]
            """,
        )

        plan = self.compile(path)

        self.assertEqual(plan.overrides_for("entities/tomas"), {})

    def test_styles_do_apply_to_endpoint_completed_artifacts(self) -> None:
        path = self.world.view(
            "completed-style",
            """\
            name: Completed style
            compose:
              selection:
                any_of: [organizations]
              relations:
                include: [leadership]
              styles: [faction-colors]
            """,
        )

        plan = self.compile(path)

        # Tomas is drawn only to keep the leadership relation whole, but he is
        # drawn, so he must be styled like anything else on the page.
        self.assertIn("entities/tomas", plan.endpoint_completions)
        self.assertEqual(plan.overrides_for("entities/tomas")["color"], "#5d78a6")

    def test_style_rules_cannot_be_structural(self) -> None:
        path = self.world.view(
            "structural-style",
            """\
            name: Structural style
            select:
              kinds: [entity]
            styles:
              - match: {kind: relation, type: leads}
                set: {as: nest}
            """,
        )

        with self.assertRaisesRegex(Exception, "unknown field.*'as'"):
            self.compile(path)


class LensOverlayTests(CompositionTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.world.module(
            "nest-leadership",
            "lens",
            "overlays:\n"
            "  - match: {kind: relation, type: leads}\n"
            "    set: {as: nest, direction: [leader, body]}\n",
        )
        self.world.module(
            "edge-leadership",
            "lens",
            "overlays:\n"
            "  - match: {kind: relation, type: leads}\n"
            "    set: {as: edge}\n",
        )
        self.world.module(
            "wildcard-leadership",
            "lens",
            "overlays:\n"
            "  - match: {kind: relation, type: '*'}\n"
            "    set: {as: chip}\n",
        )
        self.world.module(
            "link-colors",
            "lens",
            'overlays:\n'
            '  - match: {kind: relation, type: leads}\n'
            '    set: {color: "#c9a227", width: 3}\n',
        )

    def _relations_view(self, name: str, body: str) -> str:
        return self.world.view(name, body)

    def test_single_overlay_overrides_the_type_lens_without_conflict(self) -> None:
        path = self._relations_view(
            "single-overlay",
            """\
            name: Single overlay
            compose:
              lenses: [nest-leadership]
            """,
        )

        plan = self.compile(path)

        self.assertEqual(plan.overrides_for("relations/tomas-leads-guild")["as"], "nest")
        self.assertEqual(
            [item for item in plan.diagnostics if item.code == "lens.structural-conflict"], []
        )

    def test_disagreeing_structural_overlays_are_an_error(self) -> None:
        path = self._relations_view(
            "conflict",
            """\
            name: Conflict
            compose:
              lenses: [nest-leadership, edge-leadership]
            """,
        )

        plan = self.compile(path)
        errors = [item for item in plan.errors if item.code == "lens.structural-conflict"]

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].detail["property"], "as")
        self.assertIn("nest-leadership", errors[0].message)
        self.assertIn("edge-leadership", errors[0].message)

    def test_exact_view_local_rule_resolves_a_structural_conflict(self) -> None:
        path = self._relations_view(
            "resolved",
            """\
            name: Resolved
            compose:
              lenses: [nest-leadership, edge-leadership]
            lenses:
              - match: {kind: relation, type: leads}
                set: {as: edge}
            """,
        )

        plan = self.compile(path)

        self.assertEqual(plan.errors, ())
        self.assertEqual(plan.overrides_for("relations/tomas-leads-guild")["as"], "edge")
        self.assertIn(
            "lens.structural-resolved", {item.code for item in plan.diagnostics}
        )

    def test_broad_wildcard_does_not_resolve_a_structural_conflict(self) -> None:
        path = self._relations_view(
            "wildcard",
            """\
            name: Wildcard
            compose:
              lenses: [nest-leadership, edge-leadership]
            lenses:
              - match: {kind: relation, type: '*'}
                set: {as: chip}
            """,
        )

        plan = self.compile(path)

        self.assertTrue(
            [item for item in plan.errors if item.code == "lens.structural-conflict"]
        )

    def test_nonstructural_lens_properties_use_ordinary_precedence(self) -> None:
        path = self._relations_view(
            "nonstructural",
            """\
            name: Nonstructural
            compose:
              lenses: [link-colors]
            lenses:
              - match: {kind: relation, type: leads}
                set: {color: "#000000"}
            """,
        )

        plan = self.compile(path)
        overrides = plan.overrides_for("relations/tomas-leads-guild")

        self.assertEqual(overrides["color"], "#000000")
        self.assertEqual(overrides["width"], 3.0)
        self.assertEqual(plan.errors, ())

    def test_conflicting_direction_is_structural(self) -> None:
        self.world.module(
            "reversed-leadership",
            "lens",
            "overlays:\n"
            "  - match: {kind: relation, type: leads}\n"
            "    set: {direction: [body, leader]}\n",
        )
        path = self._relations_view(
            "direction-conflict",
            """\
            name: Direction conflict
            compose:
              lenses: [nest-leadership, reversed-leadership]
            """,
        )

        plan = self.compile(path)
        errors = [item for item in plan.errors if item.code == "lens.structural-conflict"]

        self.assertEqual([error.detail["property"] for error in errors], ["direction"])

    def test_styles_settle_presentation_on_top_of_lenses(self) -> None:
        self.world.module(
            "relation-colors",
            "style",
            'rules:\n'
            '  - match: {kind: relation, type: leads}\n'
            '    set: {color: "#ffffff"}\n',
        )
        path = self._relations_view(
            "layering",
            """\
            name: Layering
            compose:
              lenses: [link-colors]
              styles: [relation-colors]
            """,
        )

        plan = self.compile(path)
        overrides = plan.overrides_for("relations/tomas-leads-guild")

        self.assertEqual(overrides["color"], "#ffffff")
        self.assertEqual(overrides["width"], 3.0)


if __name__ == "__main__":
    unittest.main()
