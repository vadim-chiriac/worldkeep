from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
import unittest

import yaml

from tests.test_compile import CompositionTestCase
from viewer.compile import compile_view
from viewer.explain import explain_artifact, format_explanation
from viewer.load import load_canon, load_view, lock_path_for
from viewer.modules import load_module_index
from viewer.project import project_view
from viewer.validate_view import validate_view


VIEWER_ROOT = Path(__file__).resolve().parents[1]


class ValidationTestCase(CompositionTestCase):
    def validate(self, relative_view: str, **kwargs):
        canon = load_canon(self.root)
        view = load_view(self.root, relative_view)
        return validate_view(canon, view, index=load_module_index(self.root), **kwargs)


class ValidationTests(ValidationTestCase):
    def test_a_clean_composed_view_validates(self) -> None:
        path = self.world.view(
            "clean",
            """\
            name: Clean
            compose:
              selection:
                any_of: [people, organizations]
              relations:
                include: [leadership]
            """,
        )

        result = self.validate(path)

        self.assertTrue(result.ok, result.errors)
        self.assertGreater(result.counts["nodes"], 0)
        self.assertEqual(result.lock_state, "absent")

    def test_missing_module_is_reported_without_projecting(self) -> None:
        path = self.world.view(
            "broken",
            """\
            name: Broken
            compose:
              selection:
                any_of: [ghosts]
            """,
        )

        result = self.validate(path)

        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0]["code"], "compose.invalid")
        self.assertIsNone(result.projection)

    def test_unresolved_structural_conflict_fails_validation(self) -> None:
        self.world.module(
            "nest-leadership",
            "lens",
            "overlays:\n  - match: {kind: relation, type: leads}\n    set: {as: nest}\n",
        )
        self.world.module(
            "chip-leadership",
            "lens",
            "overlays:\n  - match: {kind: relation, type: leads}\n    set: {as: chip}\n",
        )
        path = self.world.view(
            "conflicted",
            """\
            name: Conflicted
            compose:
              lenses: [nest-leadership, chip-leadership]
            """,
        )

        result = self.validate(path)

        self.assertFalse(result.ok)
        self.assertIn(
            "lens.structural-conflict", {item["code"] for item in result.errors}
        )

    def test_fallback_is_prominent_in_the_projection_warnings(self) -> None:
        self.world.module(
            "nest-leadership",
            "lens",
            "overlays:\n  - match: {kind: relation, type: leads}\n    set: {as: nest}\n",
        )
        self.world.module(
            "chip-leadership",
            "lens",
            "overlays:\n  - match: {kind: relation, type: leads}\n    set: {as: chip}\n",
        )
        path = self.world.view(
            "fallback",
            """\
            name: Fallback
            compose:
              lenses: [nest-leadership, chip-leadership]
            """,
        )

        canon = load_canon(self.root)
        view = load_view(self.root, path)
        plan = compile_view(canon, view, index=load_module_index(self.root))
        projection = project_view(canon, view, plan=plan)

        self.assertTrue(projection["warnings"][0].startswith("UNVALIDATED FALLBACK:"))
        # The disputed structural key is dropped, not silently decided.
        self.assertNotIn("as", plan.lens_overrides.get("relations/tomas-leads-guild", {}))

    def test_containment_cycle_fails_cleanly_against_the_actual_projection(self) -> None:
        self.world.write(
            "relations/port-in-guild.md",
            "---\nid: relations/port-in-guild\nkind: relation\ntype: part_of\n"
            "members:\n  - {id: entities/port, role: part}\n"
            "  - {id: entities/guild, role: whole}\n---\n\nCircular containment.\n",
        )
        path = self.world.view(
            "cycle",
            """\
            name: Cycle
            compose:
              relations:
                include: [containment]
            """,
        )

        result = self.validate(path)

        self.assertFalse(result.ok)
        self.assertIn(
            "structure.containment-cycle", {item["code"] for item in result.errors}
        )
        # Failing cleanly means the projection still exists and nothing nests
        # into a loop, rather than the compiler raising.
        parents = {
            node["id"]: node["parent"]
            for node in result.projection["nodes"]
            if node["parent"]
        }
        self.assertNotIn("entities/port", parents)

    def test_multiple_nest_parents_fail_against_the_actual_projection(self) -> None:
        self.world.write(
            "relations/guild-in-tomas.md",
            "---\nid: relations/guild-in-tomas\nkind: relation\ntype: part_of\n"
            "members:\n  - {id: entities/guild, role: part}\n"
            "  - {id: entities/tomas, role: whole}\n---\n\nAlso contained.\n",
        )
        path = self.world.view(
            "two-parents",
            """\
            name: Two parents
            compose:
              relations:
                include: [containment]
            """,
        )

        result = self.validate(path)

        self.assertFalse(result.ok)
        self.assertIn(
            "structure.multiple-nest-parents", {item["code"] for item in result.errors}
        )

    def test_style_report_exposes_exact_ancestor_selector_that_misses_descendants(self) -> None:
        self.world.module(
            "place-colors",
            "style",
            'rules:\n  - match: {kind: entity, type: place}\n    set: {color: "#225588"}\n',
        )
        path = self.world.view(
            "narrow-place-style",
            """\
            name: Narrow place style
            compose:
              selection:
                any_of: [settlements]
              styles: [place-colors]
            """,
        )

        result = self.validate(path)

        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.style_rules[0]["source"], "module 'place-colors' styles[1]")
        self.assertEqual(result.style_rules[0]["matched_count"], 0)
        self.assertEqual(result.style_rules[0]["descendant_count"], 1)
        self.assertEqual(result.style_rules[0]["descendant_types"], ["place/settlement"])
        warning = next(
            item for item in result.warnings if item["code"] == "style.exact-type-descendants"
        )
        self.assertIn("place/*", warning["message"])
        self.assertNotIn("style.rule-unmatched", {item["code"] for item in result.warnings})
        self.assertIn("style rules (1):", result.as_text())
        self.assertEqual(result.as_json()["style_rules"], result.style_rules)

    def test_style_report_names_zero_match_rule_without_descendants(self) -> None:
        self.world.module(
            "vehicle-colors",
            "style",
            'rules:\n  - match: {kind: entity, type: vehicle}\n    set: {color: "#225588"}\n',
        )
        path = self.world.view(
            "unmatched-style",
            """\
            name: Unmatched style
            compose:
              selection:
                any_of: [people]
              styles: [vehicle-colors]
            """,
        )

        result = self.validate(path)

        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.style_rules[0]["matched_count"], 0)
        self.assertIn("style.rule-unmatched", {item["code"] for item in result.warnings})

    def test_style_report_keeps_wildcards_and_cascade_rules_separate(self) -> None:
        self.world.module(
            "place-colors",
            "style",
            'rules:\n  - match: {kind: entity, type: place/*}\n    set: {color: "#225588"}\n',
        )
        self.world.module(
            "person-shapes",
            "style",
            'rules:\n  - match: {kind: entity, type: person}\n    set: {shape: ellipse}\n',
        )
        self.world.module(
            "person-colors",
            "style",
            'rules:\n  - match: {kind: entity, type: person}\n    set: {color: "#225588"}\n',
        )
        path = self.world.view(
            "style-cascade-report",
            """\
            name: Style cascade report
            compose:
              selection:
                any_of: [people, settlements]
              styles: [place-colors, person-shapes, person-colors]
            styles:
              - match: {kind: entity, type: person}
                set: {color: "#111111"}
            """,
        )

        result = self.validate(path)

        self.assertTrue(result.ok, result.errors)
        self.assertEqual([rule["matched_count"] for rule in result.style_rules], [1, 3, 3, 3])
        self.assertEqual(
            result.style_rules[-1]["source"], f"{path}: styles[1]"
        )
        self.assertFalse(
            any(
                item["code"] in {"style.rule-unmatched", "style.exact-type-descendants"}
                for item in result.warnings
            ),
            result.warnings,
        )


class AssertionTests(ValidationTestCase):
    def test_nonempty_assertion_fails_on_an_empty_selection(self) -> None:
        path = self.world.view(
            "empty",
            """\
            name: Empty
            compose:
              selection:
                any_of: [people]
                exclude: [people]
              relations:
                exclude: [no-relations]
            assert:
              nonempty: true
            """,
        )

        result = self.validate(path)

        self.assertFalse(result.ok)
        self.assertIn("assert.nonempty", {item["code"] for item in result.errors})

    def test_contains_types_accepts_subtypes(self) -> None:
        path = self.world.view(
            "types",
            """\
            name: Types
            compose:
              selection:
                any_of: [people, organizations]
            assert:
              contains_types: [person, community]
            """,
        )

        result = self.validate(path)

        self.assertTrue(result.ok, result.errors)

    def test_contains_types_reports_what_is_missing(self) -> None:
        path = self.world.view(
            "missing-types",
            """\
            name: Missing types
            compose:
              selection:
                any_of: [people]
            assert:
              contains_types: [person, vehicle]
            """,
        )

        result = self.validate(path)

        self.assertFalse(result.ok)
        failure = next(
            item for item in result.errors if item["code"] == "assert.contains_types"
        )
        self.assertEqual(failure["detail"]["missing"], ["vehicle"])

    def test_unknown_assertion_is_an_error(self) -> None:
        path = self.world.view(
            "bad-assert",
            """\
            name: Bad assert
            compose:
              selection:
                any_of: [people]
            assert:
              node_count: 3
            """,
        )

        result = self.validate(path)

        self.assertFalse(result.ok)
        self.assertIn("assert.unknown", {item["code"] for item in result.errors})


class LockTests(ValidationTestCase):
    def _view(self) -> str:
        return self.world.view(
            "locked",
            """\
            name: Locked
            compose:
              selection:
                any_of: [people]
              relations:
                include: [leadership]
            """,
        )

    def test_no_lock_is_written_without_the_explicit_option(self) -> None:
        path = self._view()

        self.validate(path)

        self.assertFalse(lock_path_for(self.root / path).exists())

    def test_writing_a_lock_records_dependencies_and_reads_back_as_current(self) -> None:
        path = self._view()

        written = self.validate(path, write_lock_file=True)
        lock_file = lock_path_for(self.root / path)
        document = yaml.safe_load(lock_file.read_text(encoding="utf-8"))

        self.assertEqual(written.lock_state, "written")
        self.assertEqual(document["schema"], "wb.view-lock/v1")
        self.assertEqual(document["view"], path)
        self.assertEqual(
            sorted(module["id"] for module in document["dependencies"]["modules"]),
            ["leadership", "people"],
        )
        self.assertEqual(self.validate(path).lock_state, "current")

    def test_a_failed_validation_never_writes_a_lock(self) -> None:
        path = self.world.view(
            "unlockable",
            """\
            name: Unlockable
            compose:
              selection:
                any_of: [people]
            assert:
              contains_types: [vehicle]
            """,
        )

        result = self.validate(path, write_lock_file=True)

        self.assertFalse(result.ok)
        self.assertFalse(lock_path_for(self.root / path).exists())
        self.assertIn("lock.refused", {item["code"] for item in result.warnings})

    def test_module_change_makes_the_lock_stale_and_names_the_module(self) -> None:
        path = self._view()
        self.validate(path, write_lock_file=True)

        self.world.module(
            "people", "selection", "select:\n  kinds: [entity]\n  types: [person, person/*]\n"
        )
        result = self.validate(path)

        self.assertEqual(result.lock_state, "stale")
        self.assertIn("module 'people'", result.lock_changes)

    def test_view_change_makes_the_lock_stale(self) -> None:
        path = self._view()
        self.validate(path, write_lock_file=True)

        self.world.view(
            "locked",
            """\
            name: Locked
            compose:
              selection:
                any_of: [people]
              relations:
                include: [leadership]
            layout: dagre
            """,
        )
        result = self.validate(path)

        self.assertEqual(result.lock_state, "stale")
        self.assertTrue(any("view recipe" in change for change in result.lock_changes))

    def test_type_lens_change_makes_the_lock_stale(self) -> None:
        path = self._view()
        self.validate(path, write_lock_file=True)

        self.world.write(
            "types/leads.md",
            "---\nid: types/leads\nkind: type\napplies_to_kind: relation\n"
            "lens:\n  as: edge\n  direction: [body, leader]\n---\n\nLeads.\n",
        )
        result = self.validate(path)

        self.assertEqual(result.lock_state, "stale")
        self.assertIn("type fingerprint", result.lock_changes)

    def test_kernel_schema_change_makes_the_lock_stale(self) -> None:
        path = self._view()
        self.validate(path, write_lock_file=True)

        (self.root / "world.yaml").write_text(
            'kernel_version: "0.15"\nname: "Composition World"\n', encoding="utf-8"
        )
        result = self.validate(path)

        self.assertEqual(result.lock_state, "stale")
        self.assertIn("kernel version", result.lock_changes)

    def test_an_unvalidated_fallback_cannot_produce_a_lock(self) -> None:
        self.world.module(
            "nest-leadership",
            "lens",
            "overlays:\n  - match: {kind: relation, type: leads}\n    set: {as: nest}\n",
        )
        self.world.module(
            "chip-leadership",
            "lens",
            "overlays:\n  - match: {kind: relation, type: leads}\n    set: {as: chip}\n",
        )
        path = self.world.view(
            "fallback-lock",
            """\
            name: Fallback lock
            compose:
              lenses: [nest-leadership, chip-leadership]
            """,
        )

        result = self.validate(path, write_lock_file=True)

        self.assertFalse(result.ok)
        self.assertIn(
            "lens.structural-conflict", {item["code"] for item in result.errors}
        )
        self.assertFalse(lock_path_for(self.root / path).exists())
        self.assertIn("lock.refused", {item["code"] for item in result.warnings})

    def test_canon_body_change_alone_does_not_make_the_lock_stale(self) -> None:
        path = self._view()
        self.validate(path, write_lock_file=True)

        self.world.write(
            "entities/tomas.md",
            "---\nid: entities/tomas\nkind: entity\ntype: person\n---\n\nEntirely rewritten prose.\n",
        )
        result = self.validate(path)

        self.assertEqual(result.lock_state, "current")

    def test_a_lock_file_is_never_discovered_as_a_view(self) -> None:
        from viewer.load import list_views

        path = self._view()
        self.validate(path, write_lock_file=True)

        names = [view.relative_path for view in list_views(self.root)]

        self.assertIn(path, names)
        self.assertFalse(any(name.endswith(".view.lock.yaml") for name in names))


class ExplanationTests(ValidationTestCase):
    def _trace(self, relative_view: str, artifact_id: str):
        canon = load_canon(self.root)
        view = load_view(self.root, relative_view)
        plan = compile_view(canon, view, index=load_module_index(self.root))
        projection = project_view(canon, view, plan=plan)
        return explain_artifact(canon, plan, projection, artifact_id)

    def test_trace_names_the_module_that_included_an_artifact(self) -> None:
        path = self.world.view(
            "traced",
            """\
            name: Traced
            compose:
              selection:
                any_of: [people, organizations]
            """,
        )

        trace = self._trace(path, "entities/tomas")

        self.assertTrue(trace["selection"]["included"])
        self.assertEqual(trace["selection"]["any_of"], ["people"])

    def test_trace_names_the_module_that_excluded_an_artifact(self) -> None:
        path = self.world.view(
            "excluded",
            """\
            name: Excluded
            compose:
              selection:
                any_of: [people]
                exclude: [private-notes]
            """,
        )

        trace = self._trace(path, "entities/secret")

        self.assertFalse(trace["selection"]["included"])
        self.assertEqual(trace["selection"]["excluded_by"], ["private-notes"])
        self.assertIn("resurrect", trace["selection"]["reason"])

    def test_trace_reports_the_winning_style_source(self) -> None:
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
            "styled",
            """\
            name: Styled
            compose:
              selection:
                any_of: [people]
              styles: [colors-a, colors-b]
            """,
        )

        trace = self._trace(path, "entities/tomas")

        self.assertEqual(trace["style"]["color"]["value"], "#222222")
        self.assertIn("colors-b", trace["style"]["color"]["source"])

    def test_trace_reports_relation_policy_and_nest_parent(self) -> None:
        path = self.world.view(
            "nested",
            """\
            name: Nested
            compose:
              relations:
                include: [containment]
            """,
        )

        relation = self._trace(path, "relations/guild-in-port")
        child = self._trace(path, "entities/guild")

        self.assertTrue(relation["relation_policy"]["included"])
        self.assertEqual(relation["relation_policy"]["composed_include"], ["part_of"])
        self.assertEqual(child["projection"]["parent"], "entities/port")

    def test_text_and_json_traces_agree(self) -> None:
        path = self.world.view(
            "both-forms",
            """\
            name: Both forms
            compose:
              selection:
                any_of: [people]
            """,
        )

        trace = self._trace(path, "entities/tomas")
        text = format_explanation(trace)

        self.assertIn("entities/tomas", text)
        self.assertIn("people", text)
        self.assertEqual(json.loads(json.dumps(trace, default=str))["artifact"], "entities/tomas")

    def test_unknown_artifact_is_explained_not_crashed(self) -> None:
        path = self.world.view(
            "unknown",
            """\
            name: Unknown
            compose:
              selection:
                any_of: [people]
            """,
        )

        trace = self._trace(path, "entities/nobody")

        self.assertFalse(trace["known"])
        self.assertIn("no artifact", format_explanation(trace))


class ValidateExplainCliTests(ValidationTestCase):
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

    def test_validate_view_succeeds_without_generating_html(self) -> None:
        path = self.world.view(
            "cli-valid",
            """\
            name: CLI valid
            compose:
              selection:
                any_of: [people]
            """,
        )

        result = self.run_cli("--validate-view", path)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("VALID", result.stdout)

    def test_validate_view_json_reports_failure_with_exit_code_one(self) -> None:
        path = self.world.view(
            "cli-invalid",
            """\
            name: CLI invalid
            compose:
              selection:
                any_of: [people]
            assert:
              contains_types: [vehicle]
            """,
        )

        result = self.run_cli("--validate-view", path, "--json")

        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["errors"][0]["code"], "assert.contains_types")

    def test_explain_view_requires_an_artifact(self) -> None:
        path = self.world.view(
            "cli-explain",
            """\
            name: CLI explain
            compose:
              selection:
                any_of: [people]
            """,
        )

        result = self.run_cli("--explain-view", path)

        self.assertEqual(result.returncode, 2)
        self.assertIn("--artifact", result.stderr)

    def test_explain_view_emits_a_stable_json_trace(self) -> None:
        path = self.world.view(
            "cli-explain-json",
            """\
            name: CLI explain json
            compose:
              selection:
                any_of: [people]
            """,
        )

        result = self.run_cli(
            "--explain-view", path, "--artifact", "entities/tomas", "--json"
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        trace = json.loads(result.stdout)
        self.assertEqual(trace["artifact"], "entities/tomas")
        self.assertEqual(trace["selection"]["any_of"], ["people"])

    def test_write_lock_requires_validate_view(self) -> None:
        result = self.run_cli("--all-views", "--json", "--write-lock")

        self.assertEqual(result.returncode, 2)
        self.assertIn("--write-lock", result.stderr)


if __name__ == "__main__":
    unittest.main()
