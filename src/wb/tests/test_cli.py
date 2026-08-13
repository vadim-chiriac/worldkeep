from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

WB_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = WB_ROOT.parents[1]
SEED_WORLD = WORKSPACE_ROOT / "src" / "skills" / "worldbuilding-scribe" / "assets" / "seed-world"
RIVERLIGHT = WORKSPACE_ROOT / "Testing" / "manual" / "riverlight-test"

if str(WB_ROOT) not in sys.path:
    sys.path.insert(0, str(WB_ROOT))


def run_wb(*arguments: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(sys.path)
    return subprocess.run(
        [sys.executable, str(WB_ROOT / "wb.py"), *arguments],
        input=stdin,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )


class WorldCopyTestCase(unittest.TestCase):
    """Never mutate a retained world; every write test gets its own copy."""

    source = SEED_WORLD

    def setUp(self) -> None:
        self._directory = TemporaryDirectory()
        self.world = Path(self._directory.name) / "world"
        shutil.copytree(self.source, self.world)

    def tearDown(self) -> None:
        self._directory.cleanup()


ONE_ARTIFACT = json.dumps(
    [
        {
            "id": "entities/ada",
            "kind": "entity",
            "type": "person",
            "name": "Ada Wren",
            "tags": ["founder"],
            "body": "Ada founded the guild by the river.",
        }
    ]
)


class CaptureTests(WorldCopyTestCase):
    def test_capture_through_stdin_writes_a_draft_and_validates(self) -> None:
        result = run_wb("capture", str(self.world), "--session", "s1", stdin=ONE_ARTIFACT)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("wrote 1 artifact(s)", result.stdout)
        self.assertIn("Validation:", result.stdout)

        written = (self.world / "entities" / "ada.md").read_text(encoding="utf-8")
        self.assertIn("status: draft", written)
        self.assertIn("scribe.session: s1", written)

    def test_capture_never_silently_promotes(self) -> None:
        run_wb("capture", str(self.world), "--session", "s1", stdin=ONE_ARTIFACT)

        written = (self.world / "entities" / "ada.md").read_text(encoding="utf-8")

        self.assertIn("status: draft", written)
        self.assertNotIn("status: canon", written)

    def test_capture_accepts_an_input_file(self) -> None:
        payload = self.world.parent / "batch.json"
        payload.write_text(ONE_ARTIFACT, encoding="utf-8")

        result = run_wb(
            "capture", str(self.world), "--session", "s1", "--input-file", str(payload)
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.world / "entities" / "ada.md").exists())

    def test_malformed_payload_is_rejected_before_touching_the_canon(self) -> None:
        result = run_wb(
            "capture", str(self.world), "--session", "s1", stdin='[{"kind": "entity"}]'
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("missing 'id'", result.stderr)
        # The canon is untouched: the seed ships no entities, and none appeared.
        self.assertEqual(list((self.world / "entities").glob("*.md")), [])

    def test_non_json_input_is_rejected(self) -> None:
        result = run_wb("capture", str(self.world), "--session", "s1", stdin="not json")

        self.assertEqual(result.returncode, 2)
        self.assertIn("not valid JSON", result.stderr)


class ApprovalTests(WorldCopyTestCase):
    def _capture(self) -> None:
        result = run_wb("capture", str(self.world), "--session", "s1", stdin=ONE_ARTIFACT)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_approve_promotes_only_when_asked(self) -> None:
        self._capture()

        result = run_wb("approve", str(self.world), "entities/ada")

        self.assertEqual(result.returncode, 0, result.stderr)
        written = (self.world / "entities" / "ada.md").read_text(encoding="utf-8")
        self.assertIn("status: canon", written)

    def test_reject_deletes_the_draft(self) -> None:
        self._capture()

        result = run_wb("reject", str(self.world), "entities/ada")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.world / "entities" / "ada.md").exists())

    def test_approve_and_reject_stay_separate_operations(self) -> None:
        self._capture()
        parser_help = run_wb("--help").stdout

        self.assertIn("approve", parser_help)
        self.assertIn("reject", parser_help)
        # Rejecting an unknown id fails loudly instead of succeeding quietly.
        missing = run_wb("reject", str(self.world), "entities/nobody")
        self.assertEqual(missing.returncode, 1)
        self.assertIn("not found", missing.stdout)

    def test_json_envelope_preserves_exit_code_and_output(self) -> None:
        self._capture()

        result = run_wb("approve", str(self.world), "entities/ada", "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        envelope = json.loads(result.stdout)
        self.assertEqual(envelope["schema"], "wb.result/v1")
        self.assertEqual(envelope["exit_code"], 0)
        self.assertTrue(envelope["ok"])
        self.assertIn("promoted 1 to canon", envelope["stdout"])


class ValidateTests(WorldCopyTestCase):
    def test_validate_runs_the_canon_validator(self) -> None:
        result = run_wb("validate", str(self.world))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("artifacts:", result.stdout)
        self.assertIn("ERRORS:", result.stdout)

    def test_validate_reports_a_broken_canon_with_exit_one(self) -> None:
        (self.world / "entities" / "broken.md").write_text(
            "---\nid: entities/broken\nkind: entity\nwhere: entities/nowhere\n"
            "status: canon\n---\n\nDangling.\n",
            encoding="utf-8",
        )

        result = run_wb("validate", str(self.world))

        self.assertEqual(result.returncode, 1)
        self.assertIn("ERROR", result.stdout)

    def test_validate_can_target_a_named_view(self) -> None:
        result = run_wb(
            "validate", str(self.world), "--view", "views/canon-only.yaml"
        )

        self.assertIn(result.returncode, (0, 1))
        self.assertIn("view:", result.stdout)


class ViewerCommandTests(unittest.TestCase):
    def test_everything_matches_the_underlying_viewer(self) -> None:
        through_wb = run_wb("view", str(RIVERLIGHT), "--everything", "--json")
        direct = subprocess.run(
            [
                sys.executable,
                str(WORKSPACE_ROOT / "src" / "viewer" / "view.py"),
                str(RIVERLIGHT),
                "--everything",
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)},
        )

        self.assertEqual(through_wb.returncode, 0, through_wb.stderr)
        self.assertEqual(
            json.loads(through_wb.stdout), json.loads(direct.stdout)
        )

    def test_named_view_projection_is_unchanged(self) -> None:
        result = run_wb(
            "view", str(RIVERLIGHT), "--view", "views/people-and-groups.yaml", "--json"
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        projection = json.loads(result.stdout)
        self.assertEqual(set(projection), {"view", "nodes", "edges", "warnings"})

    def test_list_views_puts_everything_first(self) -> None:
        result = run_wb("view", str(RIVERLIGHT), "--list-views")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith("<built-in:everything>\tEverything"))

    def test_explain_reaches_the_viewer_explanation(self) -> None:
        result = run_wb(
            "explain",
            str(RIVERLIGHT),
            "--view",
            "views/people-and-groups.yaml",
            "--artifact",
            "entities/tomas-veyra",
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        trace = json.loads(result.stdout)
        self.assertEqual(trace["artifact"], "entities/tomas-veyra")

    def test_long_form_output_option_writes_a_file(self) -> None:
        with TemporaryDirectory() as directory:
            target = Path(directory) / "projection.json"

            result = run_wb(
                "view", str(RIVERLIGHT), "--everything", "--json", "--output", str(target)
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("nodes", json.loads(target.read_text(encoding="utf-8")))


class DoctorTests(unittest.TestCase):
    def test_doctor_finds_every_packaged_tool_in_the_source_tree(self) -> None:
        result = run_wb("doctor", "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["schema"], "wb.doctor/v1")
        for name in ("apply", "validate", "view", "kernel", "scribe"):
            self.assertIsNotNone(document["tools"][name], name)
        self.assertEqual(document["problems"], [])

    def test_doctor_changes_nothing(self) -> None:
        with TemporaryDirectory() as directory:
            world = Path(directory) / "world"
            shutil.copytree(SEED_WORLD, world)
            before = sorted(path.name for path in world.rglob("*"))

            run_wb("doctor", str(world))

            self.assertEqual(sorted(path.name for path in world.rglob("*")), before)

    def test_doctor_reports_a_bad_world_without_crashing(self) -> None:
        result = run_wb("doctor", "/nonexistent/place", "--json")

        self.assertEqual(result.returncode, 1)
        document = json.loads(result.stdout)
        self.assertIn("error", document["world"])


class BackwardCompatibilityTests(unittest.TestCase):
    def test_the_low_level_apply_cli_still_works_unchanged(self) -> None:
        with TemporaryDirectory() as directory:
            world = Path(directory) / "world"
            shutil.copytree(SEED_WORLD, world)

            result = subprocess.run(
                [
                    sys.executable,
                    str(WORKSPACE_ROOT / "src" / "skills" / "worldbuilding-scribe" / "scripts" / "apply.py"),
                    str(world),
                    "--index",
                    "--kind",
                    "type",
                    "--limit",
                    "3",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("artifacts:", result.stdout)

    def test_wb_and_apply_agree_on_what_a_search_finds(self) -> None:
        direct = subprocess.run(
            [
                sys.executable,
                str(WORKSPACE_ROOT / "src" / "skills" / "worldbuilding-scribe" / "scripts" / "apply.py"),
                str(RIVERLIGHT),
                "--find",
                "covenant",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        through_wb = run_wb("find", str(RIVERLIGHT), "covenant", "--limit", "500", "--json")

        self.assertEqual(direct.returncode, 0, direct.stderr)
        self.assertEqual(through_wb.returncode, 0, through_wb.stderr)
        expected = int(direct.stdout.split(" match", 1)[0])
        self.assertEqual(json.loads(through_wb.stdout)["total"], expected)


if __name__ == "__main__":
    unittest.main()
