"""wb restates a little metadata; these tests stop it drifting from the source.

`scribe.yaml` is behavioural, so its defaults live in prose in SCRIBE.md and
nowhere in code. wb has to report them, which means one small table. This file
is what keeps that table honest: it parses SCRIBE.md itself and fails if the
names, allowed values, or defaults disagree.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

WB_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = WB_ROOT.parents[1]
SCRIBE_DOC = WORKSPACE_ROOT / "Specification" / "SCRIBE.md"
KERNEL_DOC = WORKSPACE_ROOT / "Specification" / "KERNEL.md"
SPEC_HISTORY_DOC = WORKSPACE_ROOT / "Specification" / "SPEC-HISTORY.md"
SEED_SCRIBE = WORKSPACE_ROOT / "src" / "skills" / "worldbuilding-scribe" / "assets" / "seed-world" / "scribe.yaml"

if str(WB_ROOT) not in sys.path:
    sys.path.insert(0, str(WB_ROOT))

from wblib.paths import parse_document_version  # noqa: E402
from wblib.scribe_config import SCRIBE_SETTINGS  # noqa: E402


SETTING_LINE = re.compile(
    r"^(?P<name>[a-z_]+):\s+(?P<default>\S+)\s*#\s*(?P<allowed>.+?)\s*$"
)


def documented_settings(text: str) -> dict[str, tuple[str, tuple[str, ...]]]:
    """Parse the settings block SCRIBE.md section 10 documents."""
    found: dict[str, tuple[str, tuple[str, ...]]] = {}
    for block in re.findall(r"```yaml\n(.*?)```", text, re.S):
        if "approval:" not in block:
            continue
        for line in block.splitlines():
            match = SETTING_LINE.match(line.strip())
            if not match:
                continue
            allowed = tuple(
                item.strip() for item in match.group("allowed").split("|") if item.strip()
            )
            found[match.group("name")] = (match.group("default"), allowed)
        if found:
            break
    return found


class ScribeDefaultsSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.documented = documented_settings(SCRIBE_DOC.read_text(encoding="utf-8"))

    def test_the_documented_block_was_found(self) -> None:
        self.assertTrue(
            self.documented,
            "could not locate the scribe.yaml settings block in SCRIBE.md; "
            "update this parser rather than the table it guards",
        )

    def test_setting_names_match_scribe_md(self) -> None:
        self.assertEqual(set(SCRIBE_SETTINGS), set(self.documented))

    def test_defaults_match_scribe_md(self) -> None:
        for name, (default, _allowed) in SCRIBE_SETTINGS.items():
            with self.subTest(setting=name):
                self.assertEqual(default, self.documented[name][0])

    def test_allowed_values_match_scribe_md(self) -> None:
        for name, (_default, allowed) in SCRIBE_SETTINGS.items():
            with self.subTest(setting=name):
                self.assertEqual(allowed, self.documented[name][1])

    def test_the_shipped_seed_scribe_yaml_states_the_same_defaults(self) -> None:
        import yaml

        seed = yaml.safe_load(SEED_SCRIBE.read_text(encoding="utf-8")) or {}

        for name, (default, _allowed) in SCRIBE_SETTINGS.items():
            with self.subTest(setting=name):
                self.assertEqual(seed.get(name), default)


class DocumentVersionSyncTests(unittest.TestCase):
    def test_runtime_specs_do_not_embed_release_history(self) -> None:
        for document in (KERNEL_DOC, SCRIBE_DOC):
            with self.subTest(document=document.name):
                body = document.read_text(encoding="utf-8")
                self.assertNotRegex(body, r"(?m)^> \*\*v\d")

    def test_repository_history_keeps_current_spec_versions(self) -> None:
        history = SPEC_HISTORY_DOC.read_text(encoding="utf-8")

        self.assertIn("### v0.16", history)
        self.assertIn("### v0.9", history)
        self.assertIn("informational and is not bundled", history)

    def test_wb_reads_the_same_versions_the_build_does(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "wb_build_for_test", WORKSPACE_ROOT / "build.py"
        )
        assert spec is not None and spec.loader is not None
        build = importlib.util.module_from_spec(spec)
        saved = sys.argv
        sys.argv = ["build.py"]
        try:
            spec.loader.exec_module(build)
        finally:
            sys.argv = saved

        for document in (KERNEL_DOC, SCRIBE_DOC):
            with self.subTest(document=document.name):
                self.assertEqual(
                    parse_document_version(document),
                    build.parse_first_heading(document),
                )


if __name__ == "__main__":
    unittest.main()
