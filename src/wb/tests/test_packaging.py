"""wb ships into two bundles from one source and must work in both layouts."""

from __future__ import annotations

import importlib.util
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

if str(WB_ROOT) not in sys.path:
    sys.path.insert(0, str(WB_ROOT))

from wblib.paths import ToolPaths  # noqa: E402


def load_build():
    spec = importlib.util.spec_from_file_location(
        "wb_build_for_packaging_test", WORKSPACE_ROOT / "build.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    saved = sys.argv
    sys.argv = ["build.py"]
    try:
        spec.loader.exec_module(module)
    finally:
        sys.argv = saved
    return module


def stage_plugin(root: Path) -> Path:
    """Build the installed layout: skills/<skill>/scripts, as the plugin ships."""
    skills = root / "skills"
    scribe = skills / "worldbuilding-scribe"
    viewer = skills / "canon-viewer"
    (scribe / "scripts").mkdir(parents=True)
    (scribe / "references").mkdir(parents=True)
    (viewer / "scripts").mkdir(parents=True)

    for bundle in (scribe, viewer):
        shutil.copy2(WB_ROOT / "wb.py", bundle / "scripts" / "wb.py")
        shutil.copytree(
            WB_ROOT / "wblib",
            bundle / "scripts" / "wblib",
            ignore=shutil.ignore_patterns("__pycache__"),
        )

    shutil.copy2(WORKSPACE_ROOT / "src" / "skills" / "worldbuilding-scribe" / "scripts" / "apply.py", scribe / "scripts" / "apply.py")
    shutil.copy2(WORKSPACE_ROOT / "src" / "skills" / "worldbuilding-scribe" / "scripts" / "validate.py", scribe / "scripts" / "validate.py")
    shutil.copy2(
        WORKSPACE_ROOT / "Specification" / "KERNEL.md", scribe / "references" / "KERNEL.md"
    )
    shutil.copy2(
        WORKSPACE_ROOT / "Specification" / "SCRIBE.md", scribe / "references" / "SCRIBE.md"
    )
    shutil.copy2(
        WORKSPACE_ROOT / "src" / "viewer" / "view.py", viewer / "scripts" / "view.py"
    )
    shutil.copytree(
        WORKSPACE_ROOT / "src" / "viewer" / "viewer",
        viewer / "scripts" / "viewer",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    return skills


class CanonicalSourceTests(unittest.TestCase):
    def test_the_build_packages_wb_from_development_wb_only(self) -> None:
        build = load_build()

        with TemporaryDirectory() as directory:
            bundle = Path(directory) / "bundle"
            copied = build.copy_agent_cli(bundle)

        names = {path.name for path in copied}
        self.assertIn("wb.py", names)
        self.assertIn("paths.py", names)
        self.assertEqual(build.WB, WORKSPACE_ROOT / "src" / "wb")

    def test_packaged_wb_is_byte_identical_to_the_canonical_source(self) -> None:
        build = load_build()

        with TemporaryDirectory() as directory:
            bundle = Path(directory) / "bundle"
            build.copy_agent_cli(bundle)

            self.assertEqual(
                (bundle / "scripts" / "wb.py").read_bytes(),
                (WB_ROOT / "wb.py").read_bytes(),
            )
            for source in sorted((WB_ROOT / "wblib").glob("*.py")):
                with self.subTest(module=source.name):
                    self.assertEqual(
                        (bundle / "scripts" / "wblib" / source.name).read_bytes(),
                        source.read_bytes(),
                    )

    def test_both_bundles_receive_the_agent_cli(self) -> None:
        build = load_build()

        with TemporaryDirectory() as directory:
            build_dir = Path(directory)
            scribe_bundle, _ = build.build_scribe(build_dir)
            viewer_bundle, _ = build.build_viewer(build_dir)

            for bundle in (scribe_bundle, viewer_bundle):
                with self.subTest(bundle=bundle.name):
                    self.assertTrue((bundle / "scripts" / "wb.py").is_file())
                    self.assertTrue((bundle / "scripts" / "wblib" / "session.py").is_file())

    def test_repository_spec_history_is_not_packaged(self) -> None:
        build = load_build()

        with TemporaryDirectory() as directory:
            scribe_bundle, _ = build.build_scribe(Path(directory))

            self.assertFalse((scribe_bundle / "references" / "SPEC-HISTORY.md").exists())

    def test_there_is_no_second_copy_of_wb_in_the_source_tree(self) -> None:
        stray = [
            path
            for path in WORKSPACE_ROOT.rglob("wb.py")
            if "dist" not in path.parts
            and "plugins" not in path.parts
            and path != WB_ROOT / "wb.py"
        ]

        self.assertEqual(stray, [], f"unexpected extra wb.py: {stray}")


class InstalledLayoutTests(unittest.TestCase):
    """Compare whole resolved paths, not trailing text.

    Exact equality is what proves the resolver stayed inside the staged bundle
    instead of falling through to the repository source tree, and it is the
    only form that holds on both POSIX and Windows separators.
    """

    def assertResolves(self, located: str | None, expected: Path) -> None:
        self.assertIsNotNone(located)
        self.assertEqual(Path(located), expected.resolve())

    def test_the_scribe_bundle_resolves_its_viewer_sibling(self) -> None:
        with TemporaryDirectory() as directory:
            skills = stage_plugin(Path(directory))
            paths = ToolPaths(skills / "worldbuilding-scribe" / "scripts")

            located = paths.describe()

            self.assertResolves(
                located["apply"],
                skills / "worldbuilding-scribe" / "scripts" / "apply.py",
            )
            self.assertResolves(
                located["view"], skills / "canon-viewer" / "scripts" / "view.py"
            )
            self.assertResolves(
                located["kernel"],
                skills / "worldbuilding-scribe" / "references" / "KERNEL.md",
            )

    def test_the_viewer_bundle_resolves_its_scribe_sibling(self) -> None:
        with TemporaryDirectory() as directory:
            skills = stage_plugin(Path(directory))
            paths = ToolPaths(skills / "canon-viewer" / "scripts")

            located = paths.describe()

            self.assertResolves(
                located["view"], skills / "canon-viewer" / "scripts" / "view.py"
            )
            self.assertResolves(
                located["apply"],
                skills / "worldbuilding-scribe" / "scripts" / "apply.py",
            )
            self.assertResolves(
                located["scribe"],
                skills / "worldbuilding-scribe" / "references" / "SCRIBE.md",
            )

    def test_wb_runs_from_an_installed_bundle_without_the_source_tree(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            skills = stage_plugin(root)
            world = root / "world"
            shutil.copytree(SEED_WORLD, world)

            environment = os.environ.copy()
            environment.pop("PYTHONPATH", None)
            result = subprocess.run(
                [
                    sys.executable,
                    str(skills / "worldbuilding-scribe" / "scripts" / "wb.py"),
                    "session",
                    str(world),
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=str(root),
                env=environment,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("world:", result.stdout)
        self.assertIn("scribe:", result.stdout)

    def test_doctor_reports_a_missing_sibling_rather_than_guessing(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            skills = stage_plugin(root)
            shutil.rmtree(skills / "canon-viewer")

            environment = os.environ.copy()
            environment.pop("PYTHONPATH", None)
            result = subprocess.run(
                [
                    sys.executable,
                    str(skills / "worldbuilding-scribe" / "scripts" / "wb.py"),
                    "doctor",
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=str(root),
                env=environment,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("missing tool: view", result.stdout)


if __name__ == "__main__":
    unittest.main()
