"""What may be folded into one relation, and — more importantly — what may not.

The detector exists to counteract a measured bias, so its value is entirely in
its precision: a hint that fires on links which genuinely differ would train
authors to ignore it, which is worse than no hint at all.
"""
from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

WB_ROOT = Path(__file__).resolve().parents[1]
if str(WB_ROOT) not in sys.path:
    sys.path.insert(0, str(WB_ROOT))

from wblib.mergeable import find_mergeable, format_mergeable  # noqa: E402


def relation(artifact_id: str, whole: str, part: str, **facets) -> tuple[str, str, dict]:
    frontmatter = {
        "id": artifact_id,
        "kind": "relation",
        "type": "part_of",
        "members": [{"id": part, "role": "part"}, {"id": whole, "role": "whole"}],
    }
    frontmatter.update(facets)
    return (artifact_id, f"relations/{artifact_id}.md", frontmatter)


def entity(artifact_id: str) -> tuple[str, str, dict]:
    return (artifact_id, f"entities/{artifact_id}.md", {"id": artifact_id, "kind": "entity"})


class MergeableTests(unittest.TestCase):
    def test_links_differing_only_in_the_varying_member_are_reported(self) -> None:
        rows = [entity("region")] + [entity(f"county{n}") for n in range(3)] + [
            relation(f"r{n}", "region", f"county{n}") for n in range(3)
        ]

        found = find_mergeable(rows)

        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["anchor"], "region")
        self.assertEqual(found[0]["anchor_role"], "whole")
        self.assertEqual(found[0]["member_role"], "part")
        self.assertEqual(len(found[0]["relations"]), 3)

    def test_two_identical_links_are_already_a_pattern(self) -> None:
        """SCRIBE says "two or more", and a pair is the case a reader is least
        likely to spot for themselves."""
        rows = [entity("region"), entity("a"), entity("b"),
                relation("r1", "region", "a"), relation("r2", "region", "b")]

        found = find_mergeable(rows)

        self.assertEqual(len(found), 1)
        self.assertEqual(len(found[0]["relations"]), 2)

    def test_distinct_targets_are_left_alone(self) -> None:
        """Forty seats in forty counties is forty relations, correctly."""
        rows = []
        for n in range(5):
            rows += [entity(f"county{n}"), entity(f"seat{n}"),
                     relation(f"r{n}", f"county{n}", f"seat{n}")]

        self.assertEqual(find_mergeable(rows), [])

    def test_a_differing_facet_blocks_the_suggestion(self) -> None:
        """Independent timing is exactly what the kernel says to split on."""
        rows = [entity("region")] + [entity(f"c{n}") for n in range(3)] + [
            relation("r0", "region", "c0", when="First Era"),
            relation("r1", "region", "c1", when="Second Era"),
            relation("r2", "region", "c2", when="Third Era"),
        ]

        self.assertEqual(find_mergeable(rows), [])

    def test_a_differing_status_blocks_the_suggestion(self) -> None:
        rows = [entity("region")] + [entity(f"c{n}") for n in range(3)] + [
            relation("r0", "region", "c0", status="canon"),
            relation("r1", "region", "c1", status="draft"),
            relation("r2", "region", "c2", status="deprecated"),
        ]

        self.assertEqual(find_mergeable(rows), [])

    def test_a_relation_something_points_at_is_left_addressable(self) -> None:
        """Folding it into a sibling would break the reference to it."""
        rows = [entity("region")] + [entity(f"c{n}") for n in range(3)] + [
            relation(f"r{n}", "region", f"c{n}") for n in range(3)
        ] + [(
            "ideas/commentary",
            "ideas/commentary.md",
            {"id": "ideas/commentary", "kind": "idea", "members": [{"id": "r1"}]},
        )]

        found = find_mergeable(rows)

        # The other two may still be suggested; the pointed-at one may not.
        self.assertNotIn("r1", [rid for g in found for rid in g["relations"]])

    def test_differing_provenance_blocks_the_suggestion(self) -> None:
        """A link the author stated and one the scribe inferred elsewhere are
        two statements, which is what SCRIBE means by provenance."""
        rows = [entity("region")] + [entity(f"c{n}") for n in range(3)] + [
            relation("r0", "region", "c0", **{"scribe.origin": "author", "scribe.session": "a"}),
            relation("r1", "region", "c1", **{"scribe.origin": "mixed", "scribe.session": "b"}),
            relation("r2", "region", "c2", **{"scribe.origin": "mixed", "scribe.session": "c"}),
        ]

        self.assertEqual(find_mergeable(rows), [])

    def test_provenance_is_read_in_either_spelling(self) -> None:
        """The format allows a nested `scribe:` mapping as well as dotted keys;
        matching one spelling and not the other would compare nothing."""
        rows = [entity("region")] + [entity(f"c{n}") for n in range(2)] + [
            relation("r0", "region", "c0", scribe={"origin": "author", "session": "a"}),
            relation("r1", "region", "c1", scribe={"origin": "mixed", "session": "b"}),
        ]

        self.assertEqual(find_mergeable(rows), [])

    def test_a_differing_body_blocks_the_suggestion(self) -> None:
        """Folding two links with different prose would throw one away."""
        bodies = {"r0": "Annexed after the war.", "r1": "Bought outright.", "r2": ""}
        rows = [entity("region")] + [entity(f"c{n}") for n in range(3)] + [
            relation(f"r{n}", "region", f"c{n}") for n in range(3)
        ]

        self.assertEqual(find_mergeable(rows, bodies.get), [])

    def test_identical_bodies_still_group(self) -> None:
        bodies = dict.fromkeys(("r0", "r1", "r2"), "Part of the fen.")
        rows = [entity("region")] + [entity(f"c{n}") for n in range(3)] + [
            relation(f"r{n}", "region", f"c{n}") for n in range(3)
        ]

        self.assertEqual(len(find_mergeable(rows, bodies.get)), 1)

    def test_a_field_the_world_invented_blocks_the_suggestion(self) -> None:
        """The vocabulary is open, so a signature that knew only the standard
        facets would be blind to the field a world added to tell links apart."""
        rows = [entity("region")] + [entity(f"c{n}") for n in range(3)] + [
            relation("r0", "region", "c0", treaty="entities/first-accord"),
            relation("r1", "region", "c1", treaty="entities/second-accord"),
            relation("r2", "region", "c2", treaty="entities/third-accord"),
        ]

        self.assertEqual(find_mergeable(rows), [])

    def test_without_a_body_reader_a_relation_with_prose_is_left_alone(self) -> None:
        """Silence is the only safe answer when the comparison cannot be made."""
        rows = [entity("region")] + [entity(f"c{n}") for n in range(3)] + [
            relation(f"r{n}", "region", f"c{n}", body="Something specific.")
            for n in range(3)
        ]

        self.assertEqual(find_mergeable(rows), [])

    def test_relations_of_different_types_do_not_group(self) -> None:
        rows = [entity("region")] + [entity(f"c{n}") for n in range(3)]
        for n in range(3):
            row = relation(f"r{n}", "region", f"c{n}")
            row[2]["type"] = f"type{n}"
            rows.append(row)

        self.assertEqual(find_mergeable(rows), [])

    def test_each_relation_is_claimed_by_at_most_one_group(self) -> None:
        """Both members are tried as the anchor, so a relation could otherwise
        appear in two overlapping suggestions and be double-counted."""
        rows = [entity("region")] + [entity(f"c{n}") for n in range(4)] + [
            relation(f"r{n}", "region", f"c{n}") for n in range(4)
        ]

        found = find_mergeable(rows)
        claimed = [rid for group in found for rid in group["relations"]]

        self.assertEqual(len(claimed), len(set(claimed)))

    def test_the_report_names_the_roles_and_the_count(self) -> None:
        rows = [entity("region")] + [entity(f"c{n}") for n in range(3)] + [
            relation(f"r{n}", "region", f"c{n}") for n in range(3)
        ]

        line = format_mergeable(find_mergeable(rows))[0]

        self.assertIn("3 'part_of' relations", line)
        self.assertIn("share whole region", line)
        self.assertIn("3 'part' members", line)


class UnreadableBodyTests(unittest.TestCase):
    """The runtime path, not a stand-in for it.

    `CanonReader.body_of` used to turn any read failure into an empty string,
    so two relations nobody could open looked identical to the detector and it
    would happily suggest folding them. The comparison has to be able to say
    "I could not check" — which only shows up if a real file on disk is really
    unreadable, so this writes bytes that are not valid UTF-8.
    """

    def setUp(self) -> None:
        self.temporary = TemporaryDirectory()
        self.world = Path(self.temporary.name)
        (self.world / "world.yaml").write_text('kernel_version: "0.17"\n', encoding="utf-8")
        for name in ("region", "a", "b"):
            self._write(f"entities/{name}", f"kind: entity\nstatus: canon\n", "")
        for index, part in enumerate(("a", "b")):
            self._write(
                f"relations/r{index}",
                "kind: relation\ntype: part_of\nstatus: canon\nmembers:\n"
                f"  - {{id: entities/{part}, role: part}}\n"
                "  - {id: entities/region, role: whole}\n",
                "Same prose in both.",
            )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write(self, artifact_id: str, frontmatter: str, body: str) -> Path:
        path = self.world / f"{artifact_id}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\nid: {artifact_id}\n{frontmatter}---\n{body}\n", encoding="utf-8")
        return path

    def _reader(self):
        from wblib.context import CanonReader

        return CanonReader(self.world)

    def test_identical_readable_bodies_are_reported(self) -> None:
        reader = self._reader()

        found = find_mergeable(reader.artifacts, reader.body_or_none)

        self.assertEqual(len(found), 1)

    def test_an_unreadable_body_is_not_treated_as_empty(self) -> None:
        """Frontmatter is read once and cached; bodies are read lazily after.
        A file can therefore be gone by the time its prose is wanted — an
        ordinary thing during a long session while the author edits files."""
        reader = self._reader()
        reader.artifacts  # noqa: B018 — populate the cache, as the real flow does
        # Both, deliberately: with one readable the bodies differ anyway and
        # the test would pass without exercising anything. Collapsing both to
        # the empty string is what made two unreadable files look alike.
        (self.world / "relations/r0.md").unlink()
        (self.world / "relations/r1.md").unlink()

        self.assertIsNone(reader.body_or_none("relations/r0"))
        self.assertEqual(reader.body_of("relations/r0"), "")
        self.assertEqual(find_mergeable(reader.artifacts, reader.body_or_none), [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
