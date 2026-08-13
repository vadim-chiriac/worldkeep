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
RIVERLIGHT = WORKSPACE_ROOT / "Testing" / "manual" / "riverlight-test"

if str(WB_ROOT) not in sys.path:
    sys.path.insert(0, str(WB_ROOT))

from wblib.context import (  # noqa: E402
    CanonReader,
    format_context,
    lookup,
    one_hop_neighbors,
    search,
)


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


def build_chain_world(directory: Path) -> Path:
    """a -- r1 -- b -- r2 -- c, so one hop must stop at b."""
    world = directory / "chain"
    (world / "entities").mkdir(parents=True)
    (world / "relations").mkdir(parents=True)
    (world / "types").mkdir(parents=True)
    (world / "world.yaml").write_text(
        'kernel_version: "0.16"\nname: "Chain"\n'
        "std_types: [part_of]\n",
        encoding="utf-8",
    )
    for name, label, tags in (
        ("a", "Anna Reed", "[founder]"),
        ("b", "Bram Colt", "[ledger]"),
        ("c", "Cass Idris", "[far]"),
    ):
        (world / "entities" / f"{name}.md").write_text(
            f"---\nid: entities/{name}\nkind: entity\ntype: person\nname: {label}\n"
            f"tags: {tags}\nstatus: canon\n---\n\n{label} lives here.\n",
            encoding="utf-8",
        )
    (world / "relations" / "r1.md").write_text(
        "---\nid: relations/r1\nkind: relation\ntype: part_of/membership\n"
        "members:\n  - {id: entities/a, role: part}\n  - {id: entities/b, role: whole}\n"
        "status: canon\n---\n\nA belongs to B.\n",
        encoding="utf-8",
    )
    (world / "relations" / "r2.md").write_text(
        "---\nid: relations/r2\nkind: relation\ntype: part_of/membership\n"
        "members:\n  - {id: entities/b, role: part}\n  - {id: entities/c, role: whole}\n"
        "status: canon\n---\n\nB belongs to C.\n",
        encoding="utf-8",
    )
    return world


class SearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reader = CanonReader(RIVERLIGHT)

    def test_query_matches_ids_names_and_tags_and_says_why(self) -> None:
        result = search(self.reader, "covenant", limit=50)

        self.assertGreater(result.total, 0)
        for match in result.matches:
            self.assertTrue(match.reasons)
            for reason in match.reasons:
                self.assertIn(reason, {"id", "name", "tag"})
        self.assertTrue(
            any("name" in match.reasons for match in result.matches)
        )

    def test_results_are_stably_ordered(self) -> None:
        first = [match.id for match in search(self.reader, "river", limit=50).matches]
        second = [match.id for match in search(self.reader, "river", limit=50).matches]

        self.assertEqual(first, second)
        self.assertEqual(first, sorted(first))

    def test_truncation_reports_the_total_and_omitted_count(self) -> None:
        full = search(self.reader, "river", limit=500)
        clipped = search(self.reader, "river", limit=2)

        self.assertGreater(full.total, 2)
        self.assertTrue(clipped.truncated)
        self.assertEqual(clipped.shown, 2)
        self.assertEqual(clipped.total, full.total)
        self.assertEqual(clipped.as_json()["omitted"], full.total - 2)

    def test_summaries_are_returned_by_default_and_full_bodies_on_request(self) -> None:
        with TemporaryDirectory() as directory:
            reader = CanonReader(build_chain_world(Path(directory)))

            summary = search(reader, "Anna", limit=1)
            whole = search(reader, "Anna", limit=1, full=True)

        self.assertIsNone(summary.matches[0].body)
        self.assertEqual(summary.matches[0].snippet, "Anna Reed lives here.")
        self.assertEqual(whole.matches[0].body, "Anna Reed lives here.")
        self.assertEqual(whole.matches[0].snippet, "")

    def test_a_body_less_artifact_yields_an_empty_snippet_not_frontmatter(self) -> None:
        # Frontmatter must never leak into a snippet when there is no prose.
        result = search(self.reader, "River Covenant", limit=1)

        self.assertEqual(result.matches[0].snippet, "")

    def test_filters_narrow_without_a_query(self) -> None:
        result = search(self.reader, None, kind="relation", limit=500)

        self.assertGreater(result.total, 0)
        for match in result.matches:
            self.assertEqual(match.kind, "relation")
            self.assertEqual(match.reasons, ["filter"])

    def test_type_and_status_filters_compose(self) -> None:
        result = search(self.reader, None, kind="entity", type_pattern="community/*", limit=500)

        self.assertGreater(result.total, 0)
        for match in result.matches:
            self.assertEqual(match.kind, "entity")
            self.assertTrue(match.type.startswith("community/"))

    def test_a_query_matching_nothing_is_an_honest_zero(self) -> None:
        result = search(self.reader, "zzz-no-such-thing", limit=10)

        self.assertEqual(result.total, 0)
        self.assertEqual(result.matches, [])


class LookupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reader = CanonReader(RIVERLIGHT)

    def test_exact_lookup_returns_one_artifact(self) -> None:
        result = lookup(self.reader, "entities/tomas-veyra")

        self.assertEqual(result.total, 1)
        self.assertEqual(result.matches[0].id, "entities/tomas-veyra")
        self.assertEqual(result.matches[0].reasons, ["exact id"])

    def test_a_missing_artifact_is_never_fabricated(self) -> None:
        result = lookup(self.reader, "entities/does-not-exist")

        self.assertEqual(result.total, 0)
        self.assertEqual(result.matches, [])
        self.assertTrue(any("no artifact" in note for note in result.notes))


class NeighborTests(unittest.TestCase):
    def test_neighbours_name_the_connecting_relation_and_roles(self) -> None:
        reader = CanonReader(RIVERLIGHT)

        result = one_hop_neighbors(reader, "entities/tomas-veyra", limit=50)

        self.assertGreater(result.total, 0)
        for neighbor in result.neighbors:
            self.assertTrue(neighbor.via)
            self.assertTrue(neighbor.via_kind)
        membership = [n for n in result.neighbors if n.via_type == "part_of/membership"]
        self.assertTrue(membership)
        self.assertEqual(membership[0].target_role, "part")
        self.assertEqual(membership[0].neighbor_role, "whole")

    def test_one_hop_does_not_widen_the_graph(self) -> None:
        with TemporaryDirectory() as directory:
            world = build_chain_world(Path(directory))
            reader = CanonReader(world)

            result = one_hop_neighbors(reader, "entities/a", limit=50)

        reached = {neighbor.id for neighbor in result.neighbors}
        self.assertEqual(reached, {"entities/b"})
        # entities/c is two hops away and must not appear.
        self.assertNotIn("entities/c", reached)

    def test_neighbours_of_a_missing_artifact_are_reported_not_invented(self) -> None:
        with TemporaryDirectory() as directory:
            reader = CanonReader(build_chain_world(Path(directory)))

            result = one_hop_neighbors(reader, "entities/ghost", limit=10)

        self.assertEqual(result.total, 0)
        self.assertTrue(any("no artifact" in note for note in result.notes))


class IndexIndependenceTests(unittest.TestCase):
    def _answers(self, world: Path) -> tuple[int, set[str]]:
        reader = CanonReader(world)
        found = search(reader, "Bram", limit=50)
        neighbours = one_hop_neighbors(reader, "entities/a", limit=50)
        return found.total, {neighbor.id for neighbor in neighbours.neighbors}

    def test_answers_are_the_same_with_no_index_stale_index_or_fresh_index(self) -> None:
        with TemporaryDirectory() as directory:
            world = build_chain_world(Path(directory))

            absent = self._answers(world)

            (world / "INDEX.md").write_text(
                "<!-- GENERATED BY apply.py. DO NOT EDIT BY HAND. -->\n"
                "# Canon index\n\n| id | kind | type | name |\n|---|---|---|---|\n"
                "| `entities/ghost` | entity | person | Ghost |\n",
                encoding="utf-8",
            )
            stale = self._answers(world)

            subprocess.run(
                [
                    sys.executable,
                    str(WORKSPACE_ROOT / "src" / "skills" / "worldbuilding-scribe" / "scripts" / "apply.py"),
                    str(world),
                    "--reindex",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            fresh = self._answers(world)

        self.assertEqual(absent, stale)
        self.assertEqual(stale, fresh)
        self.assertEqual(absent[1], {"entities/b"})

    def test_a_stale_index_is_reported_as_stale(self) -> None:
        with TemporaryDirectory() as directory:
            world = build_chain_world(Path(directory))
            (world / "INDEX.md").write_text(
                "<!-- GENERATED BY apply.py. DO NOT EDIT BY HAND. -->\n"
                "| id | kind | type | name |\n|---|---|---|---|\n"
                "| `entities/a` | entity | person | Anna Reed |\n",
                encoding="utf-8",
            )

            state = CanonReader(world).index_state()

        self.assertEqual(state["state"], "stale")
        self.assertGreater(state["missing"], 0)

    def test_context_never_writes_an_index(self) -> None:
        with TemporaryDirectory() as directory:
            world = build_chain_world(Path(directory))

            search(CanonReader(world), "Anna", limit=5)

            self.assertFalse((world / "INDEX.md").exists())


class ContextCliTests(unittest.TestCase):
    def test_query_through_the_cli(self) -> None:
        result = run_wb("context", str(RIVERLIGHT), "--query", "covenant", "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertGreater(document["total"], 0)
        self.assertIn("matched_on", document["matches"][0])

    def test_artifact_and_neighbors_through_the_cli(self) -> None:
        exact = run_wb(
            "context", str(RIVERLIGHT), "--artifact", "entities/tomas-veyra", "--json"
        )
        near = run_wb(
            "context", str(RIVERLIGHT), "--neighbors", "entities/tomas-veyra", "--json"
        )

        self.assertEqual(exact.returncode, 0, exact.stderr)
        self.assertEqual(json.loads(exact.stdout)["matches"][0]["id"], "entities/tomas-veyra")
        self.assertEqual(near.returncode, 0, near.stderr)
        self.assertIn("neighbors", json.loads(near.stdout))

    def test_selectors_are_mutually_exclusive(self) -> None:
        result = run_wb(
            "context",
            str(RIVERLIGHT),
            "--query",
            "x",
            "--artifact",
            "entities/tomas-veyra",
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("not allowed with", result.stderr)

    def test_human_output_states_truncation(self) -> None:
        result = run_wb("context", str(RIVERLIGHT), "--query", "river", "--limit", "1")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("omitted", result.stdout)

    def test_context_is_read_only(self) -> None:
        with TemporaryDirectory() as directory:
            world = Path(directory) / "world"
            shutil.copytree(RIVERLIGHT, world)
            before = {
                path.relative_to(world).as_posix(): path.stat().st_mtime
                for path in sorted(world.rglob("*"))
                if path.is_file()
            }

            run_wb("context", str(world), "--query", "covenant")

            after = {
                path.relative_to(world).as_posix(): path.stat().st_mtime
                for path in sorted(world.rglob("*"))
                if path.is_file()
            }

        self.assertEqual(before, after)


class FormattingTests(unittest.TestCase):
    def test_human_output_names_the_match_reason(self) -> None:
        reader = CanonReader(RIVERLIGHT)

        text = format_context(search(reader, "covenant", limit=2))

        self.assertIn("matches for 'covenant'", text)
        self.assertIn("<-", text)


if __name__ == "__main__":
    unittest.main()
