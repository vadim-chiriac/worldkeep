from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
import unittest

from tests.test_compile import CompositionTestCase
from viewer.compile import compile_view
from viewer.load import builtin_everything, list_views, load_canon, load_view
from viewer.modules import load_module_index
from viewer.project import project_view, project_views


VIEWER_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = VIEWER_ROOT.parents[1]
EXAMPLE = WORKSPACE_ROOT / "Testing" / "fixtures" / "two-allied-countries"
ACCEPTANCE = WORKSPACE_ROOT / "Testing" / "fixtures" / "viewer-acceptance"


class RendererContractTests(unittest.TestCase):
    def test_element_shapes_are_unchanged_for_existing_worlds(self) -> None:
        for world in (EXAMPLE, ACCEPTANCE):
            canon = load_canon(world)
            for view in list_views(world):
                with self.subTest(world=world.name, view=view.name):
                    projection = project_view(canon, view)

                    self.assertEqual(
                        set(projection), {"view", "nodes", "edges", "warnings"}
                    )
                    self.assertEqual(
                        set(projection["view"]), {"name", "layout", "render"}
                    )
                    for node in projection["nodes"]:
                        self.assertEqual(
                            set(node),
                            {
                                "id",
                                "kind",
                                "type",
                                "label",
                                "parent",
                                "style",
                                "badges",
                                "chips",
                            },
                        )
                        self.assertEqual(
                            set(node["style"]), {"shape", "color", "opacity"}
                        )
                    for edge in projection["edges"]:
                        self.assertEqual(
                            set(edge),
                            {
                                "id",
                                "type",
                                "source",
                                "target",
                                "directed",
                                "behavior",
                                "roles",
                                "style"
                            },
                        )
                        self.assertEqual(set(edge["style"]), {"width", "color", "line"})

    def test_everything_is_identical_with_and_without_the_compiler_path(self) -> None:
        canon = load_canon(ACCEPTANCE)
        direct = project_view(canon, builtin_everything())
        through_helper = project_views(canon, [builtin_everything()])[0]

        self.assertEqual(direct, through_helper)

    def test_project_views_matches_one_by_one_projection(self) -> None:
        canon = load_canon(ACCEPTANCE)
        views = list_views(ACCEPTANCE)

        self.assertEqual(
            project_views(canon, views), [project_view(canon, view) for view in views]
        )


COMPOSITION_ACCEPTANCE = WORKSPACE_ROOT / "Testing" / "fixtures" / "composition-acceptance"
COMPOSITION_VIEW = "views/composed-overview.yaml"


class CompositionAcceptanceTests(unittest.TestCase):
    """Pin the small readable fixture that demonstrates Phase 2 composition."""

    def setUp(self) -> None:
        from viewer.validate_view import validate_view

        self.canon = load_canon(COMPOSITION_ACCEPTANCE)
        self.view = load_view(COMPOSITION_ACCEPTANCE, COMPOSITION_VIEW)
        self.plan = compile_view(
            self.canon, self.view, index=load_module_index(COMPOSITION_ACCEPTANCE)
        )
        self.projection = project_view(self.canon, self.view, plan=self.plan)
        self.result = validate_view(self.canon, self.view)

    def test_the_acceptance_view_validates(self) -> None:
        self.assertTrue(self.result.ok, self.result.errors)

    def test_overlapping_membership_resolves_to_one_set(self) -> None:
        node_ids = [node["id"] for node in self.projection["nodes"]]

        self.assertEqual(len(node_ids), len(set(node_ids)))
        self.assertIn("entities/tomas-veyra", node_ids)
        self.assertIn("entities/merchants-guild", node_ids)
        # Excluded by retired-figures, and nothing resurrects him.
        self.assertNotIn("entities/pell-oarsman", node_ids)

    def test_style_precedence_is_property_specific_with_provenance(self) -> None:
        tomas = next(
            node for node in self.projection["nodes"] if node["id"] == "entities/tomas-veyra"
        )
        overlap = next(
            item
            for item in self.plan.diagnostics
            if item.code == "style.overlap"
            and item.detail["artifact"] == "entities/tomas-veyra"
        )

        self.assertEqual(tomas["style"]["color"], "#5d78a6")
        self.assertEqual(tomas["style"]["shape"], "ellipse")
        self.assertIn("base-palette", overlap.detail["losing_source"])
        self.assertIn("faction-palette", overlap.detail["winning_source"])

    def test_the_structural_conflict_is_resolved_and_actually_nests(self) -> None:
        parents = {
            node["id"]: node["parent"]
            for node in self.projection["nodes"]
            if node["parent"]
        }

        self.assertEqual(
            parents,
            {
                "entities/merchants-guild": "entities/free-port",
                "entities/river-covenant": "entities/free-port",
            },
        )
        self.assertIn(
            "lens.structural-resolved", {item.code for item in self.plan.diagnostics}
        )

    def test_removing_the_local_resolution_invalidates_the_view(self) -> None:
        from viewer.load import View
        from viewer.validate_view import validate_view

        data = {key: value for key, value in self.view.data.items() if key != "lenses"}
        unresolved = View(
            name=self.view.name,
            render=self.view.render,
            data=data,
            path=self.view.path,
            relative_path=self.view.relative_path,
            warnings=self.view.warnings,
        )

        result = validate_view(self.canon, unresolved)

        self.assertFalse(result.ok)
        self.assertIn(
            "lens.structural-conflict", {item["code"] for item in result.errors}
        )
        self.assertTrue(
            result.projection["warnings"][0].startswith("UNVALIDATED FALLBACK:")
        )


class ComposedProjectionTests(CompositionTestCase):
    def project(self, relative_view: str, **kwargs):
        canon = load_canon(self.root)
        view = load_view(self.root, relative_view)
        plan = compile_view(canon, view, index=load_module_index(self.root))
        return project_view(canon, view, plan=plan, **kwargs)

    def test_composed_view_projects_selected_artifacts_and_relations(self) -> None:
        path = self.world.view(
            "composed",
            """\
            name: People and leadership
            compose:
              selection:
                any_of: [people, organizations]
              relations:
                include: [leadership]
            """,
        )

        projection = self.project(path)
        node_ids = {node["id"] for node in projection["nodes"]}
        edge_ids = {edge["id"] for edge in projection["edges"]}

        self.assertIn("entities/tomas", node_ids)
        self.assertIn("entities/guild", node_ids)
        self.assertEqual(edge_ids, {"relations/tomas-leads-guild"})
        self.assertNotIn("entities/port", node_ids)

    def test_style_modules_reach_the_projected_node_style(self) -> None:
        self.world.module(
            "faction-colors",
            "style",
            'rules:\n'
            '  - match: {kind: entity, type: person}\n'
            '    set: {color: "#5d78a6", shape: ellipse}\n',
        )
        path = self.world.view(
            "styled",
            """\
            name: Styled
            compose:
              selection:
                any_of: [people]
              styles: [faction-colors]
            """,
        )

        projection = self.project(path)
        tomas = next(
            node for node in projection["nodes"] if node["id"] == "entities/tomas"
        )

        self.assertEqual(tomas["style"]["color"], "#5d78a6")
        self.assertEqual(tomas["style"]["shape"], "ellipse")

    def test_lens_module_changes_structure_in_the_projection(self) -> None:
        self.world.module(
            "nest-leadership",
            "lens",
            "overlays:\n"
            "  - match: {kind: relation, type: leads}\n"
            "    set: {as: nest}\n",
        )
        path = self.world.view(
            "nested",
            """\
            name: Nested leadership
            compose:
              lenses: [nest-leadership]
            """,
        )

        projection = self.project(path)
        edge = next(
            edge
            for edge in projection["edges"]
            if edge["id"].startswith("relations/tomas-leads-guild")
        )

        # 'leads' has no part/whole roles, so nesting cannot be represented and
        # the relation must stay visibly inspectable rather than disappear.
        self.assertIn(edge["behavior"], {"edge", "nest"})
        self.assertTrue(
            any(node["id"] == "relations/tomas-leads-guild" for node in projection["nodes"])
        )

    def test_structural_findings_are_collected_when_requested(self) -> None:
        self.world.module(
            "nest-leadership",
            "lens",
            "overlays:\n"
            "  - match: {kind: relation, type: leads}\n"
            "    set: {as: nest}\n",
        )
        path = self.world.view(
            "findings",
            """\
            name: Findings
            compose:
              lenses: [nest-leadership]
            """,
        )

        findings: list[dict] = []
        self.project(path, findings=findings)

        self.assertIn(
            "structure.nest-not-whole", {finding["code"] for finding in findings}
        )

    def test_compiler_diagnostics_reach_projection_warnings(self) -> None:
        self.world.module(
            "colors-a",
            "style",
            'rules:\n  - match: {kind: entity, type: person}\n    set: {color: "#111111"}\n',
        )
        self.world.module(
            "colors-b",
            "style",
            'rules:\n  - match: {kind: entity, type: person}\n    set: {color: "#222222"}\n',
        )
        path = self.world.view(
            "warned",
            """\
            name: Warned
            compose:
              selection:
                any_of: [people]
              styles: [colors-a, colors-b]
            """,
        )

        projection = self.project(path)

        self.assertTrue(
            any("colors-a" in warning and "colors-b" in warning for warning in projection["warnings"])
        )


class ComposedCliTests(CompositionTestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(sys.path)
        return subprocess.run(
            [sys.executable, str(VIEWER_ROOT / "view.py"), str(self.root), *arguments],
            check=False,
            capture_output=True,
            env=environment,
            text=True,
        )

    def test_cli_projects_a_composed_view_as_json(self) -> None:
        path = self.world.view(
            "cli-composed",
            """\
            name: CLI composed
            compose:
              selection:
                any_of: [people]
            """,
        )

        result = self.run_cli("--view", path, "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        projection = json.loads(result.stdout)
        self.assertEqual(projection["view"]["name"], "CLI composed")
        self.assertTrue(projection["nodes"])

    def test_cli_reports_a_composition_error_without_a_traceback(self) -> None:
        path = self.world.view(
            "cli-broken",
            """\
            name: CLI broken
            compose:
              selection:
                any_of: [ghosts]
            """,
        )

        result = self.run_cli("--view", path, "--json")

        self.assertEqual(result.returncode, 2)
        self.assertIn("no module with id 'ghosts'", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_all_views_still_lists_everything_first_with_modules_present(self) -> None:
        self.world.view(
            "listed",
            """\
            name: Listed
            compose:
              selection:
                any_of: [people]
            """,
        )

        result = self.run_cli("--all-views", "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["views"][0]["view"]["name"], "Everything")

    def test_everything_ignores_style_and_lens_modules(self) -> None:
        self.world.module(
            "loud-colors",
            "style",
            'rules:\n  - match: {kind: entity, type: person}\n    set: {color: "#ff00ff"}\n',
        )
        self.world.view(
            "loud",
            """\
            name: Loud
            compose:
              styles: [loud-colors]
            """,
        )

        result = self.run_cli("--everything", "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        projection = json.loads(result.stdout)
        colors = {node["style"]["color"] for node in projection["nodes"]}
        self.assertNotIn("#ff00ff", colors)


class SharedLoadTests(CompositionTestCase):
    def test_multiple_views_reuse_one_module_index(self) -> None:
        first = self.world.view(
            "first",
            """\
            name: First
            compose:
              selection:
                any_of: [people]
            """,
        )
        second = self.world.view(
            "second",
            """\
            name: Second
            compose:
              selection:
                any_of: [organizations]
            """,
        )

        canon = load_canon(self.root)
        views = [load_view(self.root, first), load_view(self.root, second)]

        import viewer.project as project_module

        calls = {"count": 0}
        original = project_module.__dict__.get("_load_module_index_probe")
        self.assertIsNone(original)

        import viewer.modules as modules_module

        real_loader = modules_module.load_module_index

        def counting_loader(root):
            calls["count"] += 1
            return real_loader(root)

        modules_module.load_module_index = counting_loader
        try:
            projections = project_views(canon, views)
        finally:
            modules_module.load_module_index = real_loader

        self.assertEqual(calls["count"], 1)
        self.assertEqual(len(projections), 2)
        self.assertEqual(projections[0]["view"]["name"], "First")


if __name__ == "__main__":
    unittest.main()
