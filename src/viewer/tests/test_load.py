from __future__ import annotations

import os
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from viewer.load import ViewLoadError, builtin_everything, list_views, load_canon, load_view


VIEWER_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = VIEWER_ROOT.parents[1]
EXAMPLE = WORKSPACE_ROOT / "Testing" / "fixtures" / "two-allied-countries"


class ExampleWorldTests(unittest.TestCase):
    def test_loads_example_and_resolves_ancestor_type(self) -> None:
        canon = load_canon(EXAMPLE)

        self.assertEqual(len(canon.artifacts), 8)
        self.assertEqual(set(canon.types), {"alliance", "place", "separates"})
        self.assertEqual(canon.resolve_type("place/country").id, "types/place")
        self.assertEqual(canon.resolve_type("place/river").id, "types/place")
        self.assertEqual(canon.warnings, [])

    def test_lists_and_loads_political_view(self) -> None:
        views = list_views(EXAMPLE)

        self.assertEqual(len(views), 2)
        self.assertEqual(views[0], builtin_everything())
        self.assertEqual(views[1].relative_path, "views/political.yaml")
        self.assertEqual(views[1].name, "Political View")
        self.assertEqual(load_view(EXAMPLE, "views/political.yaml"), views[1])

    def test_cli_lists_views(self) -> None:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(sys.path)
        result = subprocess.run(
            [
                sys.executable,
                str(VIEWER_ROOT / "view.py"),
                str(EXAMPLE),
                "--list-views",
            ],
            check=False,
            capture_output=True,
            env=environment,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "<built-in:everything>\tEverything\nviews/political.yaml\tPolitical View\n")
        self.assertEqual(result.stderr, "")


class LoaderBehaviorTests(unittest.TestCase):
    def test_root_index_without_frontmatter_is_ignored(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "world.yaml").write_text("kernel_version: '0.14'\n", encoding="utf-8")
            (root / "INDEX.md").write_text("Generated index\n", encoding="utf-8")

            canon = load_canon(root)

            self.assertEqual(canon.artifacts, {})
            self.assertEqual(canon.warnings, [])

    def test_warns_and_keeps_loading_bad_artifacts(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "entities").mkdir()
            (root / "world.yaml").write_text("kernel_version: '0.11'\n", encoding="utf-8")
            (root / "entities" / "good.md").write_text(
                "---\nid: entities/good\nkind: entity\nwhere: [entities/missing]\n---\nBody\n",
                encoding="utf-8",
            )
            (root / "entities" / "bad.md").write_text("No frontmatter\n", encoding="utf-8")

            canon = load_canon(root)

            self.assertIn("entities/good", canon.artifacts)
            self.assertTrue(any("no YAML frontmatter" in item for item in canon.warnings))
            self.assertTrue(any("dangling reference" in item for item in canon.warnings))

    def test_crlf_frontmatter_is_supported(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "entities").mkdir()
            (root / "entities" / "x.md").write_bytes(
                b"---\r\nid: entities/x\r\nkind: entity\r\n---\r\nBody\r\n"
            )

            canon = load_canon(root)

            self.assertEqual(canon.artifacts["entities/x"].body, "Body\r\n")

    def test_duplicate_id_keeps_first_file_deterministically(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "entities").mkdir()
            for filename, name in (("a.md", "First"), ("b.md", "Second")):
                (root / "entities" / filename).write_text(
                    f"---\nid: duplicate\nkind: entity\nname: {name}\n---\n",
                    encoding="utf-8",
                )

            canon = load_canon(root)

            self.assertEqual(canon.artifacts["duplicate"].name, "First")
            self.assertTrue(any("duplicate id" in item for item in canon.warnings))

    def test_malformed_view_is_fatal(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "views").mkdir()
            (root / "views" / "broken.yaml").write_text("name: [\n", encoding="utf-8")

            with self.assertRaises(ViewLoadError):
                list_views(root)

    def test_view_path_must_stay_inside_views_folder(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "views").mkdir()
            (root / "outside.yaml").write_text("name: Outside\n", encoding="utf-8")

            with self.assertRaises(ViewLoadError):
                load_view(root, "outside.yaml")

    def test_everything_exists_without_views_folder_and_reserved_recipes_fail(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(list_views(root), [builtin_everything()])
            (root / "views").mkdir()
            (root / "views" / "everything.yml").write_text("name: Other\n", encoding="utf-8")
            with self.assertRaisesRegex(ViewLoadError, "built in.*differently named custom view"):
                list_views(root)
            (root / "views" / "everything.yml").unlink()
            (root / "views" / "custom.yaml").write_text("name:  everything  \n", encoding="utf-8")
            with self.assertRaisesRegex(ViewLoadError, "cannot be shadowed"):
                list_views(root)

    def test_cli_everything_and_all_views_work_without_named_views(self) -> None:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(sys.path)
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "entities").mkdir()
            (root / "entities" / "a.md").write_text(
                "---\nid: entities/a\nkind: entity\nstatus: canon\n---\n", encoding="utf-8"
            )
            base = [sys.executable, str(VIEWER_ROOT / "view.py"), str(root)]
            everything = subprocess.run([*base, "--everything", "--json"], capture_output=True, text=True, env=environment)
            all_views = subprocess.run([*base, "--all-views", "--json"], capture_output=True, text=True, env=environment)
            self.assertEqual(everything.returncode, 0, everything.stderr)
            self.assertEqual(all_views.returncode, 0, all_views.stderr)
            self.assertEqual(json.loads(everything.stdout)["view"]["name"], "Everything")
            self.assertEqual(json.loads(all_views.stdout)["view"]["name"], "Everything")


if __name__ == "__main__":
    unittest.main()
