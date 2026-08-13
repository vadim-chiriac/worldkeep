from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import textwrap
import unittest

from viewer.modules import (
    MODULE_SCHEMA,
    ModuleError,
    ModuleIndex,
    load_module_index,
    parse_module,
)


SELECTION_MODULE = textwrap.dedent(
    f"""\
    schema: {MODULE_SCHEMA}
    id: people
    version: 1
    kind: selection
    select:
      kinds: [entity]
      types: [person, person/*]
      status: [canon, draft]
    """
)

RELATION_MODULE = textwrap.dedent(
    f"""\
    schema: {MODULE_SCHEMA}
    id: affiliations
    version: 1
    kind: relation
    edges:
      include: [part_of/membership]
      exclude: []
    """
)

STYLE_MODULE = textwrap.dedent(
    f"""\
    schema: {MODULE_SCHEMA}
    id: faction-colors
    version: 2
    kind: style
    rules:
      - match: {{kind: entity, type: community/polity/*}}
        set: {{color: "#5d78a6", shape: round-rectangle}}
      - match: {{kind: relation, type: leads}}
        set: {{color: "#c9a227", width: 2}}
    """
)

LENS_MODULE = textwrap.dedent(
    f"""\
    schema: {MODULE_SCHEMA}
    id: geographic-containment
    version: 1
    kind: lens
    overlays:
      - match: {{kind: relation, type: located_in}}
        set: {{as: nest, direction: [place, container]}}
    """
)


def _world(files: dict[str, str], directory: Path) -> Path:
    root = directory / "world"
    (root / "view-modules").mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (root / "view-modules" / name).write_text(text, encoding="utf-8")
    return root


class ManifestParsingTests(unittest.TestCase):
    def _parse(self, text: str, name: str = "module.yaml"):
        import yaml

        return parse_module(
            yaml.safe_load(text),
            relative_path=f"view-modules/{name}",
            path=Path(name),
        )

    def test_each_kind_parses_into_its_own_normalized_payload(self) -> None:
        selection = self._parse(SELECTION_MODULE)
        relation = self._parse(RELATION_MODULE)
        style = self._parse(STYLE_MODULE)
        lens = self._parse(LENS_MODULE)

        self.assertEqual(selection.kind, "selection")
        self.assertEqual(selection.payload["types"], ["person", "person/*"])
        self.assertEqual(relation.payload, {"include": ["part_of/membership"], "exclude": []})
        self.assertEqual(style.version, 2)
        self.assertEqual(style.payload[0]["set"], {"color": "#5d78a6", "shape": "round-rectangle"})
        self.assertEqual(style.payload[1]["set"]["width"], 2.0)
        self.assertEqual(lens.payload[0]["set"], {"as": "nest", "direction": ["place", "container"]})

    def test_normalized_hash_ignores_formatting_and_key_order(self) -> None:
        reordered = textwrap.dedent(
            f"""\
            kind: selection
            id: people
            version: 1
            schema: {MODULE_SCHEMA}

            select:
              status: [canon, draft]
              types:   [person, person/*]
              kinds: [entity]
            """
        )

        self.assertEqual(
            self._parse(SELECTION_MODULE).content_hash,
            self._parse(reordered).content_hash,
        )

    def test_hash_changes_when_payload_changes(self) -> None:
        changed = SELECTION_MODULE.replace("status: [canon, draft]", "status: [canon]")

        self.assertNotEqual(
            self._parse(SELECTION_MODULE).content_hash,
            self._parse(changed).content_hash,
        )

    def test_wrong_schema_is_rejected(self) -> None:
        text = SELECTION_MODULE.replace(MODULE_SCHEMA, "wb.view-module/v2")

        with self.assertRaisesRegex(ModuleError, "schema must be"):
            self._parse(text)

    def test_unknown_kind_is_rejected(self) -> None:
        text = SELECTION_MODULE.replace("kind: selection", "kind: emphasis")

        with self.assertRaisesRegex(ModuleError, "kind must be one of"):
            self._parse(text)

    def test_unknown_manifest_field_is_an_error(self) -> None:
        text = SELECTION_MODULE + "layout: dagre\n"

        with self.assertRaisesRegex(ModuleError, "unknown field.*'layout'"):
            self._parse(text)

    def test_payload_must_match_declared_kind(self) -> None:
        text = textwrap.dedent(
            f"""\
            schema: {MODULE_SCHEMA}
            id: mismatch
            version: 1
            kind: selection
            edges:
              include: [leads]
            """
        )

        with self.assertRaisesRegex(ModuleError, "must carry 'select'"):
            self._parse(text)

    def test_missing_payload_is_rejected(self) -> None:
        text = textwrap.dedent(
            f"""\
            schema: {MODULE_SCHEMA}
            id: empty
            version: 1
            kind: style
            """
        )

        with self.assertRaisesRegex(ModuleError, "requires a 'rules' payload"):
            self._parse(text)

    def test_bad_ids_and_versions_are_rejected(self) -> None:
        for bad_id in ("../escape", "nested/id", "-leading", "with space", ""):
            with self.subTest(bad_id=bad_id):
                text = SELECTION_MODULE.replace("id: people", f"id: {bad_id!r}")
                with self.assertRaises(ModuleError):
                    self._parse(text)

        for bad_version in ("0", "-1", "'1'", "1.5", "true"):
            with self.subTest(bad_version=bad_version):
                text = SELECTION_MODULE.replace("version: 1", f"version: {bad_version}")
                with self.assertRaisesRegex(ModuleError, "version must be a positive integer"):
                    self._parse(text)

    def test_imports_and_recursion_are_rejected_by_name(self) -> None:
        for key, expected in (
            ("compose", "cannot compose"),
            ("imports", "cannot import"),
            ("extends", "cannot inherit"),
            ("url", "remote or external"),
            ("path", "arbitrary paths"),
        ):
            with self.subTest(key=key):
                text = SELECTION_MODULE + f"{key}: [other]\n"
                with self.assertRaisesRegex(ModuleError, expected):
                    self._parse(text)

    def test_unknown_selector_and_rule_properties_are_errors(self) -> None:
        with self.assertRaisesRegex(ModuleError, "unknown field.*'expr'"):
            self._parse(SELECTION_MODULE + "  expr: 'kind == entity'\n")

        overlay = LENS_MODULE.replace("set: {as: nest", "set: {rank: 3, as: nest")
        with self.assertRaisesRegex(ModuleError, "unknown field.*'rank'"):
            self._parse(overlay)

    def test_style_rules_cannot_set_structural_keys(self) -> None:
        text = STYLE_MODULE.replace('set: {color: "#c9a227", width: 2}', "set: {as: nest}")

        with self.assertRaisesRegex(ModuleError, "unknown field.*'as'"):
            self._parse(text)

    def test_match_selectors_stay_narrow(self) -> None:
        text = STYLE_MODULE.replace("match: {kind: relation, type: leads}", "match: {status: canon}")

        with self.assertRaisesRegex(ModuleError, "unknown field.*'status'"):
            self._parse(text)

    def test_invalid_property_values_are_rejected(self) -> None:
        cases = (
            ("set: {as: nest, direction: [place, container]}", "set: {as: group}", "must be one of"),
            (
                "set: {as: nest, direction: [place, container]}",
                "set: {as: nest, direction: [place]}",
                r"\[source_role, target_role\]",
            ),
            (
                "set: {as: nest, direction: [place, container]}",
                "set: {as: nest, direction: [place, place]}",
                "roles must differ",
            ),
        )
        for original, replacement, expected in cases:
            with self.subTest(replacement=replacement):
                with self.assertRaisesRegex(ModuleError, expected):
                    self._parse(LENS_MODULE.replace(original, replacement))

        with self.assertRaisesRegex(ModuleError, "number or 'weight'"):
            self._parse(STYLE_MODULE.replace("width: 2", "width: thick"))


class ModuleIndexTests(unittest.TestCase):
    def test_missing_folder_yields_an_empty_index(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "world"
            root.mkdir()

            index = load_module_index(root)

        self.assertEqual(index.modules, {})
        self.assertEqual(index.warnings, ())

    def test_indexes_direct_yaml_children_only(self) -> None:
        with TemporaryDirectory() as directory:
            root = _world(
                {
                    "people.yaml": SELECTION_MODULE,
                    "affiliations.yml": RELATION_MODULE,
                    "README.md": "not a module",
                },
                Path(directory),
            )
            nested = root / "view-modules" / "nested"
            nested.mkdir()
            (nested / "hidden.yaml").write_text(STYLE_MODULE, encoding="utf-8")

            index = load_module_index(root)

        self.assertEqual(set(index.modules), {"people", "affiliations"})
        self.assertEqual(index.modules["people"].relative_path, "view-modules/people.yaml")
        self.assertEqual(len(index.warnings), 1)
        self.assertIn("nested module folders are ignored", index.warnings[0])

    def test_duplicate_ids_are_rejected_with_both_files_named(self) -> None:
        with TemporaryDirectory() as directory:
            root = _world(
                {"a-people.yaml": SELECTION_MODULE, "b-people.yaml": SELECTION_MODULE},
                Path(directory),
            )

            with self.assertRaisesRegex(ModuleError, "duplicate module id 'people'"):
                load_module_index(root)

    def test_malformed_module_fails_the_whole_index(self) -> None:
        with TemporaryDirectory() as directory:
            root = _world({"broken.yaml": "kind: selection\n"}, Path(directory))

            with self.assertRaisesRegex(ModuleError, "schema must be"):
                load_module_index(root)

    def test_fingerprint_tracks_module_content(self) -> None:
        with TemporaryDirectory() as directory:
            root = _world({"people.yaml": SELECTION_MODULE}, Path(directory))
            before = load_module_index(root).fingerprint()

            (root / "view-modules" / "people.yaml").write_text(
                SELECTION_MODULE.replace("status: [canon, draft]", "status: [canon]"),
                encoding="utf-8",
            )
            after = load_module_index(root).fingerprint()

        self.assertNotEqual(before, after)


class ReferenceResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._directory = TemporaryDirectory()
        self.root = _world(
            {
                "people.yaml": SELECTION_MODULE,
                "affiliations.yaml": RELATION_MODULE,
                "faction-colors.yaml": STYLE_MODULE,
                "geographic-containment.yaml": LENS_MODULE,
            },
            Path(self._directory.name),
        )
        self.index: ModuleIndex = load_module_index(self.root)

    def tearDown(self) -> None:
        self._directory.cleanup()

    def test_resolves_by_id_when_the_kind_matches(self) -> None:
        module = self.index.resolve("people", kind="selection", context="compose.selection.any_of")

        self.assertEqual(module.id, "people")
        self.assertEqual(
            module.provenance(),
            {
                "id": "people",
                "kind": "selection",
                "schema": MODULE_SCHEMA,
                "version": 1,
                "path": "view-modules/people.yaml",
                "content_hash": module.content_hash,
            },
        )

    def test_kind_mismatch_names_both_kinds(self) -> None:
        with self.assertRaisesRegex(ModuleError, "has kind 'relation'.*requires kind 'selection'"):
            self.index.resolve("affiliations", kind="selection", context="compose.selection.any_of")

    def test_missing_reference_lists_known_ids(self) -> None:
        with self.assertRaisesRegex(ModuleError, "no module with id 'ghosts'"):
            self.index.resolve("ghosts", kind="selection", context="compose.selection.any_of")

    def test_paths_and_remote_references_are_rejected(self) -> None:
        unsafe = (
            "../secrets",
            "nested/people",
            "view-modules/people.yaml",
            "/etc/passwd",
            "https://example.com/people.yaml",
            "file:///tmp/people.yaml",
            "C:\\modules\\people",
            ".hidden",
        )
        for reference in unsafe:
            with self.subTest(reference=reference):
                with self.assertRaises(ModuleError):
                    self.index.resolve(reference, kind="selection", context="compose.selection.any_of")

    def test_non_string_references_are_rejected(self) -> None:
        for reference in (None, 3, ["people"], {"id": "people"}, "", "  "):
            with self.subTest(reference=reference):
                with self.assertRaises(ModuleError):
                    self.index.resolve(reference, kind="selection", context="compose.selection.any_of")


if __name__ == "__main__":
    unittest.main()
