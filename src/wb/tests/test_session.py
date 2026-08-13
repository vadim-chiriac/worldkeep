from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

WB_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = WB_ROOT.parents[1]
SEED_WORLD = WORKSPACE_ROOT / "src" / "skills" / "worldbuilding-scribe" / "assets" / "seed-world"
RIVERLIGHT = WORKSPACE_ROOT / "Testing" / "manual" / "riverlight-test"

if str(WB_ROOT) not in sys.path:
    sys.path.insert(0, str(WB_ROOT))

from wblib.discovery import DiscoveryError, resolve_canon  # noqa: E402
from wblib.scribe_config import SCRIBE_SETTINGS, load_scribe_config  # noqa: E402
from wblib.session import build_session, format_session  # noqa: E402


def make_world(directory: Path, name: str = "Test World", *, scribe: str | None = None) -> Path:
    world = directory / "world"
    (world / "entities").mkdir(parents=True)
    (world / "types").mkdir(parents=True)
    (world / "world.yaml").write_text(
        f'kernel_version: "0.16"\nname: "{name}"\n'
        "facets: [when, where, valence, weight, members, status, amount, fiat]\n"
        "std_types: [part_of, holds]\n",
        encoding="utf-8",
    )
    (world / "types" / "person.md").write_text(
        "---\nid: types/person\nkind: type\nname: Person\napplies_to_kind: entity\n"
        "status: canon\n---\n\nA person.\n",
        encoding="utf-8",
    )
    (world / "entities" / "ada.md").write_text(
        "---\nid: entities/ada\nkind: entity\ntype: person\nname: Ada Wren\n"
        "tags: [founder]\nstatus: canon\n---\n\nAda founded the guild by the river.\n",
        encoding="utf-8",
    )
    (world / "entities" / "bram.md").write_text(
        "---\nid: entities/bram\nkind: entity\ntype: person\nname: Bram Colt\n"
        "status: draft\n---\n\nBram keeps the ledger.\n",
        encoding="utf-8",
    )
    if scribe is not None:
        (world / "scribe.yaml").write_text(scribe, encoding="utf-8")
    return world


def run_wb(*arguments: str) -> subprocess.CompletedProcess:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(sys.path)
    return subprocess.run(
        [sys.executable, str(WB_ROOT / "wb.py"), *arguments],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )


class CanonResolutionTests(unittest.TestCase):
    def test_an_exact_canon_folder_is_used_directly(self) -> None:
        resolution = resolve_canon(SEED_WORLD)

        self.assertEqual(resolution.world, SEED_WORLD.resolve())
        self.assertIn("Seed template", resolution.name)

    def test_a_bounded_root_with_one_canon_selects_it(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            world = make_world(root, "Only World")

            resolution = resolve_canon(root)

            self.assertEqual(resolution.world, world.resolve())
            self.assertEqual(resolution.name, "Only World")

    def test_a_bounded_root_with_several_canons_requires_a_choice(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("alpha", "beta"):
                sub = root / name
                sub.mkdir()
                make_world(sub, name.title())

            with self.assertRaises(DiscoveryError) as caught:
                resolve_canon(root)

        message = str(caught.exception)
        self.assertIn("2 canon folders", message)
        self.assertIn("Alpha", message)
        self.assertIn("Beta", message)

    def test_a_root_with_no_canon_is_an_error(self) -> None:
        with TemporaryDirectory() as directory:
            (Path(directory) / "notes").mkdir()

            with self.assertRaisesRegex(DiscoveryError, "no canon folder found"):
                resolve_canon(directory)

    def test_a_missing_path_is_an_error(self) -> None:
        with self.assertRaisesRegex(DiscoveryError, "does not exist"):
            resolve_canon("/nonexistent/place")

    def test_discovery_never_descends_past_the_bounded_depth(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            deep = root / "one" / "two" / "three"
            deep.mkdir(parents=True)
            make_world(deep, "Too Deep")

            with self.assertRaisesRegex(DiscoveryError, "no canon folder found"):
                resolve_canon(root)


class ScribeSettingsTests(unittest.TestCase):
    def test_absent_file_reports_documented_defaults(self) -> None:
        with TemporaryDirectory() as directory:
            world = make_world(Path(directory))

            config = load_scribe_config(world)

        self.assertFalse(config.present)
        for name, (default, _allowed) in SCRIBE_SETTINGS.items():
            self.assertEqual(config.values[name], default)
            self.assertEqual(config.sources[name], "default")

    def test_explicit_settings_override_and_are_attributed(self) -> None:
        with TemporaryDirectory() as directory:
            world = make_world(
                Path(directory),
                scribe="approval: material_only\nprose: quote\n",
            )

            config = load_scribe_config(world)

        self.assertTrue(config.present)
        self.assertEqual(config.values["approval"], "material_only")
        self.assertEqual(config.sources["approval"], "scribe.yaml")
        self.assertEqual(config.values["prose"], "quote")
        # Untouched settings keep their documented defaults.
        self.assertEqual(config.values["types"], "ask")
        self.assertEqual(config.sources["types"], "default")
        self.assertEqual(config.non_default(), {"approval": "material_only", "prose": "quote"})

    def test_invalid_values_warn_and_fall_back(self) -> None:
        with TemporaryDirectory() as directory:
            world = make_world(Path(directory), scribe="approval: whenever\nnonsense: 1\n")

            config = load_scribe_config(world)

        self.assertEqual(config.values["approval"], "strict")
        self.assertEqual(config.sources["approval"], "default")
        self.assertTrue(any("approval=" in warning for warning in config.warnings))
        self.assertTrue(any("unknown setting 'nonsense'" in warning for warning in config.warnings))


class SessionDocumentTests(unittest.TestCase):
    def _document(self, world: Path, **kwargs) -> dict:
        return build_session(resolve_canon(world), **kwargs)

    def test_counts_are_reported_by_kind_and_status(self) -> None:
        with TemporaryDirectory() as directory:
            document = self._document(make_world(Path(directory)))

        self.assertEqual(document["counts"]["total"], 3)
        self.assertEqual(document["counts"]["by_kind"], {"entity": 2, "type": 1})
        self.assertEqual(document["counts"]["by_status"], {"canon": 2, "draft": 1})

    def test_document_is_versioned_and_deterministic(self) -> None:
        with TemporaryDirectory() as directory:
            world = make_world(Path(directory))
            first = self._document(world)
            second = self._document(world)

        self.assertEqual(first["schema"], "wb.session/v1")
        self.assertEqual(
            json.dumps(first, sort_keys=True, default=str),
            json.dumps(second, sort_keys=True, default=str),
        )

    def test_versions_and_compatibility_problems_are_reported(self) -> None:
        document = self._document(RIVERLIGHT)

        versions = document["versions"]
        self.assertEqual(versions["world_kernel"], "0.15")
        self.assertTrue(versions["kernel_document"].startswith("v0."))
        self.assertTrue(versions["scribe_document"].startswith("v0."))
        self.assertTrue(
            any("kernel_version" in problem for problem in versions["problems"]),
            versions["problems"],
        )

    def test_types_and_views_are_summarised(self) -> None:
        document = self._document(RIVERLIGHT, task="view")

        self.assertIn("part_of", document["types"]["standard"])
        self.assertIn("person", document["types"]["defined"])
        self.assertEqual(document["views"]["builtin"], ["Everything"])
        self.assertTrue(document["views"]["named_total"] >= 1)
        self.assertTrue(
            any(module["kind"] == "selection" for module in document["views"]["modules"])
        )

    def test_truncation_is_reported_with_omitted_counts(self) -> None:
        with TemporaryDirectory() as directory:
            world = make_world(Path(directory))
            types_dir = world / "types"
            for number in range(60):
                (types_dir / f"filler{number:02d}.md").write_text(
                    f"---\nid: types/filler{number:02d}\nkind: type\n"
                    f"name: Filler {number}\nstatus: canon\n---\n\nFiller.\n",
                    encoding="utf-8",
                )

            document = self._document(world)

        types = document["types"]
        self.assertEqual(len(types["defined"]), 40)
        self.assertEqual(types["defined_total"], 61)
        self.assertEqual(types["defined_omitted"], 21)

    def test_index_state_is_reported_without_regenerating_it(self) -> None:
        with TemporaryDirectory() as directory:
            world = make_world(Path(directory))

            absent = self._document(world)
            self.assertEqual(absent["index"]["state"], "absent")
            self.assertFalse((world / "INDEX.md").exists())

            (world / "INDEX.md").write_text(
                "<!-- GENERATED BY apply.py. DO NOT EDIT BY HAND. -->\n"
                "# Canon index\n\n| id | kind | type | name |\n|---|---|---|---|\n"
                "| `entities/ada` | entity | person | Ada Wren |\n",
                encoding="utf-8",
            )
            stale = self._document(world)

        self.assertEqual(stale["index"]["state"], "stale")
        self.assertTrue(any("stale" in warning for warning in stale["warnings"]))

    def test_query_adds_a_bounded_context_section(self) -> None:
        document = self._document(RIVERLIGHT, query="River Covenant")

        found = document["context"]
        self.assertGreaterEqual(found["total"], 1)
        self.assertLessEqual(len(found["matches"]), 5)
        self.assertTrue(all(match["matched_on"] for match in found["matches"]))

    def test_next_operations_follow_the_task(self) -> None:
        with TemporaryDirectory() as directory:
            world = make_world(Path(directory))
            capture = self._document(world, task="capture")
            view = self._document(world, task="view")

        self.assertTrue(any("wb capture" in step for step in capture["next"]))
        # A draft is present, so approval is offered.
        self.assertTrue(any("wb approve" in step for step in capture["next"]))
        self.assertTrue(any("wb view" in step for step in view["next"]))

    def test_human_output_is_compact(self) -> None:
        document = self._document(RIVERLIGHT, task="view")

        text = format_session(document)

        self.assertIn("world: Riverlight", text)
        self.assertLess(len(text), 6000)


class SessionCliTests(unittest.TestCase):
    def test_cli_reports_a_world_and_exits_zero(self) -> None:
        result = run_wb("session", str(SEED_WORLD))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("world:", result.stdout)

    def test_cli_json_is_parseable_and_versioned(self) -> None:
        result = run_wb("session", str(SEED_WORLD), "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["schema"], "wb.session/v1")

    def test_cli_reports_several_worlds_as_a_usage_error(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("alpha", "beta"):
                sub = root / name
                sub.mkdir()
                make_world(sub, name.title())

            result = run_wb("session", str(root))

        self.assertEqual(result.returncode, 2)
        self.assertIn("name one of them", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_writes_to_an_output_file(self) -> None:
        with TemporaryDirectory() as directory:
            target = Path(directory) / "session.json"

            result = run_wb("session", str(SEED_WORLD), "--json", "--output", str(target))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(target.read_text(encoding="utf-8"))["schema"], "wb.session/v1")


if __name__ == "__main__":
    unittest.main()
