"""What may be folded into one relation, and — more importantly — what may not.

The detector exists to counteract a measured bias, so its value is entirely in
its precision: a hint that fires on links which genuinely differ would train
authors to ignore it, which is worse than no hint at all.
"""
from __future__ import annotations

from pathlib import Path
import sys
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

    def test_two_links_are_not_a_pattern(self) -> None:
        rows = [entity("region"), entity("a"), entity("b"),
                relation("r1", "region", "a"), relation("r2", "region", "b")]

        self.assertEqual(find_mergeable(rows), [])

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
            relation("r2", "region", "c2", status="canon"),
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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
