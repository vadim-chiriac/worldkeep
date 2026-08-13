from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from viewer.load import builtin_everything, load_canon, load_view
from viewer.project import project_view


VIEWER_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = VIEWER_ROOT.parents[1]
EXAMPLE = WORKSPACE_ROOT / "Testing" / "fixtures" / "two-allied-countries"
ACCEPTANCE = WORKSPACE_ROOT / "Testing" / "fixtures" / "viewer-acceptance"


def write_artifact(root: Path, artifact_id: str, frontmatter: str, body: str = "") -> None:
    path = root / f"{artifact_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nid: {artifact_id}\n{frontmatter}---\n{body}", encoding="utf-8")


def write_view(root: Path, content: str) -> None:
    path = root / "views" / "test.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class ExampleProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.projection = project_view(
            load_canon(EXAMPLE), load_view(EXAMPLE, "views/political.yaml")
        )

    def test_projects_binary_and_reified_relations(self) -> None:
        nodes = {node["id"]: node for node in self.projection["nodes"]}
        edges = {edge["id"]: edge for edge in self.projection["edges"]}

        self.assertEqual(
            set(nodes),
            {
                "entities/avelor",
                "entities/brannoch",
                "entities/river-lume",
                "relations/lume-separates-avelor-brannoch",
            },
        )
        self.assertIn("relations/avelor-brannoch-alliance", edges)
        self.assertEqual(
            len(
                [
                    edge_id
                    for edge_id in edges
                    if edge_id.startswith("relations/lume-separates-avelor-brannoch::")
                ]
            ),
            3,
        )
        self.assertEqual(self.projection["warnings"], [])

    def test_v0_contract_contains_no_v1_fields(self) -> None:
        forbidden = {"aggregate_count", "collapsed", "hidden_children", "lifted_from", "series"}

        def visit(value: object) -> None:
            if isinstance(value, dict):
                self.assertTrue(forbidden.isdisjoint(value))
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(self.projection)
        self.assertEqual(set(self.projection), {"view", "nodes", "edges", "warnings"})

    def test_cli_emits_parseable_projection(self) -> None:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(sys.path)
        result = subprocess.run(
            [
                sys.executable,
                str(VIEWER_ROOT / "view.py"),
                str(EXAMPLE),
                "--view",
                "views/political.yaml",
                "--json",
            ],
            check=False,
            capture_output=True,
            env=environment,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["view"]["name"], "Political View")
        self.assertEqual(len(output["nodes"]), 4)

    def test_cli_writes_projection_file(self) -> None:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(sys.path)
        with TemporaryDirectory() as directory:
            output_path = Path(directory) / "nested" / "political.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(VIEWER_ROOT / "view.py"),
                    str(EXAMPLE),
                    "--view",
                    "views/political.yaml",
                    "--json",
                    "-o",
                    str(output_path),
                ],
                check=False,
                capture_output=True,
                env=environment,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertEqual(json.loads(output_path.read_text(encoding="utf-8"))["warnings"], [])


class BehaviorProjectionTests(unittest.TestCase):
    def test_connected_to_kinds_keeps_anchors_and_direct_neighbors_only(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            write_artifact(root, "ideas/held", "kind: idea\nstatus: canon\n")
            write_artifact(root, "ideas/isolated", "kind: idea\nstatus: canon\n")
            write_artifact(root, "entities/holder", "kind: entity\nstatus: canon\n")
            write_artifact(root, "entities/unrelated", "kind: entity\nstatus: canon\n")
            write_artifact(
                root,
                "relations/holds",
                "kind: relation\ntype: holds\nstatus: canon\n"
                "members: [entities/holder, ideas/held]\n",
            )
            write_artifact(
                root,
                "relations/unrelated",
                "kind: relation\ntype: holds\nstatus: canon\n"
                "members: [entities/holder, entities/unrelated]\n",
            )
            write_view(
                root,
                "name: Test\nselect:\n  kinds: [entity, idea, relation]\n"
                "  status: [canon]\n  connected_to_kinds: [idea]\n"
                "edges:\n  include: [holds]\n",
            )

            projection = project_view(load_canon(root), load_view(root, "views/test.yaml"))
            node_ids = {node["id"] for node in projection["nodes"]}
            edge_ids = {edge["id"] for edge in projection["edges"]}

            self.assertEqual(
                node_ids,
                {"ideas/held", "ideas/isolated", "entities/holder"},
            )
            self.assertEqual(edge_ids, {"relations/holds"})

    def test_nest_visible_membership_hierarchy_hide_and_chip(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "world.yaml").write_text("kernel_version: '0.11'\n", encoding="utf-8")
            write_artifact(root, "entities/whole", "kind: entity\nstatus: canon\n")
            write_artifact(root, "entities/part", "kind: entity\nstatus: canon\n")
            write_artifact(root, "entities/member", "kind: entity\nstatus: canon\n")
            write_artifact(
                root,
                "relations/part",
                "kind: relation\ntype: part_of\nstatus: canon\nmembers:\n"
                "  - {id: entities/part, role: part}\n"
                "  - {id: entities/whole, role: whole}\n",
            )
            write_artifact(
                root,
                "relations/member",
                "kind: relation\ntype: part_of/membership\nstatus: canon\nmembers:\n"
                "  - {id: entities/member, role: part}\n"
                "  - {id: entities/whole, role: whole}\n",
            )
            write_artifact(
                root,
                "relations/rank",
                "kind: relation\ntype: subordinate_to\nstatus: canon\nmembers:\n"
                "  - {id: entities/whole, role: superior}\n"
                "  - {id: entities/part, role: subordinate}\n",
            )
            write_artifact(
                root,
                "relations/order",
                "kind: relation\ntype: precedes\nstatus: canon\nmembers:\n"
                "  - {id: entities/part, role: earlier}\n"
                "  - {id: entities/member, role: later}\n",
            )
            write_artifact(
                root,
                "relations/state",
                "kind: relation\ntype: state/population\nstatus: canon\n"
                "members: [{id: entities/whole, role: subject}]\n"
                "when: during-test\namount: {value: 12, unit: persons}\n",
            )
            write_view(
                root,
                "name: Test\nrender: graph\nselect:\n  kinds: [entity, relation]\n"
                "  status: [canon]\nedges:\n"
                "  include: [part_of, part_of/membership, subordinate_to, precedes, state/*]\n",
            )

            projection = project_view(load_canon(root), load_view(root, "views/test.yaml"))
            nodes = {node["id"]: node for node in projection["nodes"]}
            behaviors = {edge["id"]: edge["behavior"] for edge in projection["edges"]}

            self.assertEqual(nodes["entities/part"]["parent"], "entities/whole")
            self.assertEqual(behaviors["relations/part"], "nest")
            self.assertFalse(
                next(edge for edge in projection["edges"] if edge["id"] == "relations/part")["directed"]
            )
            self.assertEqual(behaviors["relations/member"], "edge")
            # subordinate_to draws a line as of KERNEL v0.13; `rank` is gone.
            self.assertEqual(behaviors["relations/rank"], "edge")
            self.assertEqual(behaviors["relations/order"], "hide")
            self.assertEqual(nodes["entities/whole"]["chips"][0]["amount"]["value"], 12)

    def test_nary_nest_assigns_every_part_and_where_under_keeps_all_paths(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for artifact_id in ("entities/realm", "entities/north", "entities/vale"):
                write_artifact(root, artifact_id, "kind: entity\nstatus: canon\n")
            write_artifact(root, "types/part_of", "kind: type\n")
            write_artifact(root, "types/part_of/province", "kind: type\n")
            write_artifact(
                root,
                "relations/provinces",
                "kind: relation\ntype: part_of/province\nstatus: canon\nmembers:\n"
                "  - {id: entities/realm, role: whole}\n"
                "  - {id: entities/north, role: part}\n"
                "  - {id: entities/vale, role: part}\n",
            )
            write_view(
                root,
                "name: Test\nselect:\n  kinds: [entity, relation]\n  status: [canon]\n"
                "  where_under: entities/realm\n",
            )

            projection = project_view(load_canon(root), load_view(root, "views/test.yaml"))
            nodes = {node["id"]: node for node in projection["nodes"]}
            edges = {edge["id"]: edge for edge in projection["edges"]}

            self.assertEqual(nodes["entities/north"]["parent"], "entities/realm")
            self.assertEqual(nodes["entities/vale"]["parent"], "entities/realm")
            self.assertNotIn("relations/provinces", nodes)
            self.assertEqual(edges["relations/provinces::member:2"]["behavior"], "nest")
            self.assertEqual(edges["relations/provinces::member:3"]["behavior"], "nest")
            self.assertFalse(
                any("nest requires" in warning for warning in projection["warnings"])
            )

    def test_a_misspelt_layout_is_reported_rather_than_swallowed(self) -> None:
        """The renderer falls back to fcose for anything it does not know, so
        without this a typo produced a different picture and no explanation."""
        from viewer.compile import compile_view

        with TemporaryDirectory() as directory:
            root = Path(directory)
            write_artifact(root, "entities/one", "kind: entity\nstatus: canon\n")
            write_view(root, "name: Test\nlayout: dagr\nselect:\n  kinds: [entity]\n")

            plan = compile_view(load_canon(root), load_view(root, "views/test.yaml"))
            codes = {item.code for item in plan.diagnostics}

            self.assertIn("view.unknown-layout", codes)
            self.assertEqual(plan.layout, "fcose")

    def test_a_known_layout_is_left_alone(self) -> None:
        from viewer.compile import compile_view

        with TemporaryDirectory() as directory:
            root = Path(directory)
            write_artifact(root, "entities/one", "kind: entity\nstatus: canon\n")
            write_view(root, "name: Test\nlayout: dagre\nselect:\n  kinds: [entity]\n")

            plan = compile_view(load_canon(root), load_view(root, "views/test.yaml"))

            self.assertEqual(plan.layout, "dagre")
            self.assertNotIn(
                "view.unknown-layout", {item.code for item in plan.diagnostics}
            )

    def test_a_verse_of_a_held_doctrine_is_not_dormant(self) -> None:
        """`dormant` means nobody entertains this. A part of a creed somebody
        holds is in a head, even if no one holds that verse on its own."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            write_artifact(root, "entities/fenfolk", "kind: entity\nstatus: canon\n")
            write_artifact(root, "ideas/tharos", "kind: idea\nstatus: canon\n")
            write_artifact(root, "ideas/sela", "kind: idea\nstatus: canon\n")
            write_artifact(root, "ideas/forgotten", "kind: idea\nstatus: canon\n")
            write_artifact(root, "types/holds", "kind: type\n")
            write_artifact(root, "types/part_of", "kind: type\n")
            write_artifact(
                root,
                "relations/fenfolk-hold-tharos",
                "kind: relation\ntype: holds\nstatus: canon\nmembers:\n"
                "  - {id: entities/fenfolk, role: holder}\n"
                "  - {id: ideas/tharos, role: held}\n",
            )
            write_artifact(
                root,
                "relations/sela-in-tharos",
                "kind: relation\ntype: part_of\nstatus: canon\nmembers:\n"
                "  - {id: ideas/sela, role: part}\n"
                "  - {id: ideas/tharos, role: whole}\n",
            )
            write_view(root, "name: Test\nselect:\n  kinds: [entity, idea, relation]\n")

            projection = project_view(load_canon(root), load_view(root, "views/test.yaml"))
            badges = {node["id"]: node.get("badges", []) for node in projection["nodes"]}

            self.assertNotIn("dormant", badges["ideas/tharos"])
            self.assertNotIn("dormant", badges["ideas/sela"])
            # An idea in no doctrine at all is still dormant.
            self.assertIn("dormant", badges["ideas/forgotten"])

    def test_nest_uses_the_role_names_the_lens_declares(self) -> None:
        """A world may nest by its own vocabulary, not only part/whole.

        The role pair comes from the lens `direction`, in canon, so the picture
        is a property of the world rather than of the view that drew it.
        """
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for artifact_id in ("entities/cluj-county", "entities/cluj-napoca"):
                write_artifact(root, artifact_id, "kind: entity\nstatus: canon\n")
            write_artifact(
                root,
                "types/seat_of",
                "kind: type\nlens:\n  as: nest\n  direction: [seat, territory]\n",
            )
            write_artifact(
                root,
                "relations/cluj-seat",
                "kind: relation\ntype: seat_of\nstatus: canon\nmembers:\n"
                "  - {id: entities/cluj-napoca, role: seat}\n"
                "  - {id: entities/cluj-county, role: territory}\n",
            )
            write_view(root, "name: Test\nselect:\n  kinds: [entity, relation]\n")

            projection = project_view(load_canon(root), load_view(root, "views/test.yaml"))
            nodes = {node["id"]: node for node in projection["nodes"]}

            self.assertEqual(nodes["entities/cluj-napoca"]["parent"], "entities/cluj-county")
            self.assertFalse(
                any("nest requires" in warning for warning in projection["warnings"])
            )

    def test_nest_without_declared_roles_still_means_part_and_whole(self) -> None:
        """The default is unchanged, so canons written before this keep working."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for artifact_id in ("entities/realm", "entities/north"):
                write_artifact(root, artifact_id, "kind: entity\nstatus: canon\n")
            write_artifact(root, "types/encloses", "kind: type\nlens:\n  as: nest\n")
            write_artifact(
                root,
                "relations/enclosure",
                "kind: relation\ntype: encloses\nstatus: canon\nmembers:\n"
                "  - {id: entities/north, role: part}\n"
                "  - {id: entities/realm, role: whole}\n",
            )
            write_view(root, "name: Test\nselect:\n  kinds: [entity, relation]\n")

            projection = project_view(load_canon(root), load_view(root, "views/test.yaml"))
            nodes = {node["id"]: node for node in projection["nodes"]}

            self.assertEqual(nodes["entities/north"]["parent"], "entities/realm")

    def test_declared_roles_only_count_when_canon_declares_the_nest(self) -> None:
        """A direction declared for an edge is not a containment claim.

        `leads` orients an arrow from leader to body. If a view could reuse that
        pair as inside/outside merely by overriding `as`, the shape of the graph
        would depend on who drew it — the renderer-dependent behaviour KERNEL
        v0.13 removed. The override still applies; the role names do not.
        """
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for artifact_id in ("entities/tomas", "entities/guild"):
                write_artifact(root, artifact_id, "kind: entity\nstatus: canon\n")
            write_artifact(
                root,
                "types/leads",
                "kind: type\nlens:\n  as: edge\n  direction: [leader, body]\n",
            )
            write_artifact(
                root,
                "relations/tomas-leads-guild",
                "kind: relation\ntype: leads\nstatus: canon\nmembers:\n"
                "  - {id: entities/tomas, role: leader}\n"
                "  - {id: entities/guild, role: body}\n",
            )
            write_view(root, "name: Test\nselect:\n  kinds: [entity, relation]\n")

            projection = project_view(load_canon(root), load_view(root, "views/test.yaml"))
            nodes = {node["id"]: node for node in projection["nodes"]}

            self.assertIsNone(nodes["entities/tomas"].get("parent"))

    def test_nest_warning_names_the_declared_roles(self) -> None:
        """A world that nests by its own roles must be told so when it misses."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for artifact_id in ("entities/cluj-county", "entities/cluj-napoca"):
                write_artifact(root, artifact_id, "kind: entity\nstatus: canon\n")
            write_artifact(
                root,
                "types/seat_of",
                "kind: type\nlens:\n  as: nest\n  direction: [seat, territory]\n",
            )
            write_artifact(
                root,
                "relations/cluj-seat",
                "kind: relation\ntype: seat_of\nstatus: canon\nmembers:\n"
                "  - {id: entities/cluj-napoca, role: part}\n"
                "  - {id: entities/cluj-county, role: whole}\n",
            )
            write_view(root, "name: Test\nselect:\n  kinds: [entity, relation]\n")

            projection = project_view(load_canon(root), load_view(root, "views/test.yaml"))

            self.assertTrue(
                any(
                    "one 'territory' and one or more 'seat'" in warning
                    for warning in projection["warnings"]
                ),
                projection["warnings"],
            )

    def test_targeted_nary_nest_is_reified_without_losing_containment(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for artifact_id in ("entities/realm", "entities/north", "entities/vale"):
                write_artifact(root, artifact_id, "kind: entity\nstatus: canon\n")
            write_artifact(root, "ideas/commentary", "kind: idea\nstatus: canon\n")
            write_artifact(root, "types/part_of", "kind: type\n")
            write_artifact(root, "types/part_of/province", "kind: type\n")
            write_artifact(
                root,
                "relations/provinces",
                "kind: relation\ntype: part_of/province\nstatus: canon\nmembers:\n"
                "  - {id: entities/realm, role: whole}\n"
                "  - {id: entities/north, role: part}\n"
                "  - {id: entities/vale, role: part}\n",
            )
            write_artifact(
                root,
                "relations/commentary",
                "kind: relation\nstatus: canon\nmembers:\n"
                "  - ideas/commentary\n"
                "  - relations/provinces\n",
            )
            write_view(root, "name: Test\nselect:\n  status: [canon]\n")

            projection = project_view(load_canon(root), load_view(root, "views/test.yaml"))
            nodes = {node["id"]: node for node in projection["nodes"]}
            member_spokes = [
                edge
                for edge in projection["edges"]
                if edge["id"].startswith("relations/provinces::member:")
            ]

            self.assertIn("relations/provinces", nodes)
            self.assertEqual(nodes["entities/north"]["parent"], "entities/realm")
            self.assertEqual(nodes["entities/vale"]["parent"], "entities/realm")
            self.assertEqual(len(member_spokes), 3)

    def test_relation_targeted_by_another_relation_is_reified(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            write_artifact(root, "entities/a", "kind: entity\nstatus: canon\n")
            write_artifact(root, "ideas/x", "kind: idea\nstatus: canon\n")
            write_artifact(
                root,
                "relations/holds",
                "kind: relation\ntype: holds\nstatus: canon\n"
                "members: [entities/a, ideas/x]\n",
            )
            write_artifact(
                root,
                "relations/about",
                "kind: relation\nstatus: canon\n"
                "members: [ideas/x, relations/holds]\n",
            )
            write_view(root, "name: Test\nselect:\n  status: [canon]\n")

            projection = project_view(load_canon(root), load_view(root, "views/test.yaml"))
            node_ids = {node["id"] for node in projection["nodes"]}

            self.assertIn("relations/holds", node_ids)
            self.assertEqual(
                len(
                    [
                        edge
                        for edge in projection["edges"]
                        if edge["id"].startswith("relations/holds::member")
                    ]
                ),
                2,
            )

    def test_undefined_types_warn_but_project(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            write_artifact(
                root,
                "entities/x",
                "kind: entity\ntype: place/town\nstatus: canon\n",
            )
            write_view(root, "name: Test\nselect:\n  status: [canon]\n")

            projection = project_view(load_canon(root), load_view(root, "views/test.yaml"))

            self.assertEqual(len(projection["nodes"]), 1)
            self.assertTrue(any("undefined" in warning for warning in projection["warnings"]))

    def test_type_lens_uses_nearest_defined_ancestor(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            write_artifact(
                root,
                "entities/a",
                "kind: entity\nstatus: canon\n",
            )
            write_artifact(
                root,
                "entities/b",
                "kind: entity\nstatus: canon\n",
            )
            write_artifact(
                root,
                "relations/bond",
                "kind: relation\ntype: bond/oath/blood\nstatus: canon\n"
                "members: [entities/a, entities/b]\n",
            )
            write_artifact(
                root,
                "types/bond",
                "kind: type\nlens: {as: group, color: '#112233'}\n",
            )
            write_artifact(
                root,
                "types/bond/oath",
                "kind: type\nlens: {as: edge, color: '#445566'}\n",
            )
            write_view(root, "name: Test\nselect:\n  status: [canon]\n")

            projection = project_view(load_canon(root), load_view(root, "views/test.yaml"))
            edge = projection["edges"][0]

            self.assertEqual(edge["behavior"], "edge")
            self.assertEqual(edge["style"]["color"], "#445566")

    def test_removed_group_behavior_warns_and_falls_back_to_edge(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            write_artifact(root, "entities/a", "kind: entity\nstatus: canon\n")
            write_artifact(root, "entities/b", "kind: entity\nstatus: canon\n")
            write_artifact(
                root,
                "relations/bond",
                "kind: relation\ntype: bond\nstatus: canon\n"
                "members: [entities/a, entities/b]\n",
            )
            write_artifact(
                root,
                "types/bond",
                "kind: type\nlens: {as: group}\n",
            )
            write_view(root, "name: Test\nselect:\n  status: [canon]\n")

            projection = project_view(load_canon(root), load_view(root, "views/test.yaml"))

            self.assertEqual(projection["edges"][0]["behavior"], "edge")
            self.assertTrue(
                any("unknown lens behavior 'group'" in warning for warning in projection["warnings"])
            )


class ConnectedToTypesProjectionTests(unittest.TestCase):
    def _projection(self, root: Path, select: str, edges: str = "  include: [part_of/membership]\n") -> dict:
        write_view(root, "name: Test\nselect:\n  kinds: [entity, relation]\n  status: [canon]\n" + select + "edges:\n" + edges)
        return project_view(load_canon(root), load_view(root, "views/test.yaml"))

    def _world(self, root: Path) -> None:
        for artifact_id, type_path in (
            ("entities/mara", "person"), ("entities/eren", "person/elder"),
            ("entities/guild", "community/guild"), ("entities/assembly", "community/assembly"),
            ("entities/league", "community/league"),
        ):
            write_artifact(root, artifact_id, f"kind: entity\ntype: {type_path}\nstatus: canon\n")
        write_artifact(root, "relations/member", "kind: relation\ntype: part_of/membership\nstatus: canon\nmembers:\n  - {id: entities/mara, role: part}\n  - {id: entities/guild, role: whole}\n")
        write_artifact(root, "relations/away", "kind: relation\ntype: part_of/membership\nstatus: canon\nmembers:\n  - {id: entities/guild, role: part}\n  - {id: entities/league, role: whole}\n")
        write_artifact(root, "relations/excluded", "kind: relation\ntype: leads\nstatus: canon\nmembers: [entities/mara, entities/assembly]\n")

    def test_type_anchors_keep_people_guild_and_isolated_person_only(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory); self._world(root)
            projection = self._projection(root, "  types: [person, person/*, community, community/*]\n  connected_to_types: [person, person/*]\n")
            self.assertEqual({node["id"] for node in projection["nodes"]}, {"entities/mara", "entities/eren", "entities/guild"})
            self.assertEqual({edge["id"] for edge in projection["edges"]}, {"relations/member"})

    def test_kind_and_type_anchors_intersect_and_malformed_types_fall_back(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory); self._world(root)
            intersection = self._projection(root, "  types: [person, person/*, community, community/*]\n  connected_to_kinds: [idea]\n  connected_to_types: [person]\n")
            self.assertEqual(intersection["nodes"], [])
            malformed = self._projection(root, "  types: [person, person/*, community, community/*]\n  connected_to_types: person\n")
            self.assertEqual(len(malformed["nodes"]), 5)
            self.assertEqual(sum("connected_to_types" in warning for warning in malformed["warnings"]), 1)

    def test_reified_dependency_retains_members_without_expanding_non_anchor_neighbor(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory); self._world(root)
            write_artifact(root, "relations/member", "kind: relation\ntype: part_of/membership\nstatus: canon\nmembers:\n  - {id: entities/mara, role: part}\n  - {id: entities/guild, role: whole}\n  - relations/attestation\n")
            write_artifact(root, "relations/attestation", "kind: relation\ntype: discusses\nstatus: canon\nmembers: [entities/guild, entities/assembly]\n")
            projection = self._projection(root, "  types: [person, community, community/*]\n  connected_to_types: [person]\n", "  include: [part_of/membership, discusses]\n")
            ids = {node["id"] for node in projection["nodes"]}
            self.assertTrue({"entities/mara", "entities/guild", "entities/assembly", "relations/member", "relations/attestation"}.issubset(ids))
            self.assertNotIn("entities/league", ids)

    def test_view_without_anchor_fields_has_stable_prior_projection(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "world.yaml").write_text("kernel_version: '0.15'\n", encoding="utf-8")
            write_artifact(root, "entities/a", "kind: entity\nstatus: canon\n")
            write_artifact(root, "entities/b", "kind: entity\nstatus: canon\n")
            write_artifact(root, "relations/bond", "kind: relation\nstatus: canon\nmembers: [entities/a, entities/b]\n")
            write_view(root, "name: Stable\nselect:\n  kinds: [entity, relation]\n  status: [canon]\n")

            projection = project_view(load_canon(root), load_view(root, "views/test.yaml"))
            expected = {
                "view": {"name": "Stable", "layout": "fcose", "render": "graph"},
                "nodes": [
                    {"id": "entities/a", "kind": "entity", "type": None, "label": "entities/a", "parent": None, "style": {"shape": "roundrectangle", "color": None, "opacity": 1.0}, "badges": [], "chips": []},
                    {"id": "entities/b", "kind": "entity", "type": None, "label": "entities/b", "parent": None, "style": {"shape": "roundrectangle", "color": None, "opacity": 1.0}, "badges": [], "chips": []},
                ],
                "edges": [{"id": "relations/bond", "type": None, "source": "entities/a", "target": "entities/b", "directed": False, "behavior": "edge", "roles": {"source": None, "target": None}, "style": {"width": 2.0, "color": "#999999", "line": "solid"}}],
                "warnings": [],
            }
            self.assertEqual(json.dumps(projection, sort_keys=True), json.dumps(expected, sort_keys=True))


class EverythingAuditProjectionTests(unittest.TestCase):
    def test_audit_selects_active_fiat_and_reifies_unsafe_relations_without_custom_lenses(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            write_artifact(root, "entities/canon", "kind: entity\nstatus: canon\nfiat: true\n")
            write_artifact(root, "entities/draft", "kind: entity\nstatus: draft\n")
            write_artifact(root, "entities/third", "kind: entity\nstatus: canon\n")
            write_artifact(root, "entities/old", "kind: entity\nstatus: deprecated\n")
            write_artifact(root, "types/hidden", "kind: type\nstatus: canon\nlens: {as: hide, color: '#ff00ff'}\n")
            write_artifact(root, "types/container", "kind: type\nstatus: canon\nlens: {as: nest, color: '#ff00ff'}\n")
            write_artifact(root, "relations/binary", "kind: relation\ntype: hidden\nstatus: canon\nmembers: [entities/canon, entities/draft]\n")
            write_artifact(root, "relations/unary", "kind: relation\ntype: hidden\nstatus: canon\nmembers: [entities/canon]\n")
            write_artifact(root, "relations/many", "kind: relation\ntype: container\nstatus: canon\nmembers: [entities/canon, entities/draft, entities/third, entities/old]\n")

            projection = project_view(load_canon(root), builtin_everything())
            nodes = {node["id"]: node for node in projection["nodes"]}
            edges = {edge["id"]: edge for edge in projection["edges"]}

            self.assertEqual(set(nodes), {"entities/canon", "entities/draft", "entities/third", "relations/unary", "relations/many"})
            self.assertIn("fiat", nodes["entities/canon"]["badges"])
            self.assertEqual(nodes["entities/canon"]["style"], {"shape": "roundrectangle", "color": None, "opacity": 1.0})
            self.assertEqual(edges["relations/binary"]["behavior"], "edge")
            self.assertEqual(edges["relations/binary"]["style"], {"width": 2.0, "color": "#999999", "line": "solid"})
            self.assertIn("relations/unary::member:1", edges)
            self.assertIn("relations/many::member:1", edges)
            self.assertTrue(all(node["parent"] is None for node in nodes.values()))

    def test_audit_uses_standard_directions_but_ignores_type_file_direction(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for artifact_id in ("entities/a", "entities/b", "entities/c"):
                write_artifact(root, artifact_id, "kind: entity\nstatus: canon\n")
            write_artifact(root, "types/custom", "kind: type\nlens: {direction: [from, to]}\n")
            write_artifact(root, "relations/standard", "kind: relation\ntype: subordinate_to\nstatus: canon\nmembers:\n  - {id: entities/b, role: subordinate}\n  - {id: entities/a, role: superior}\n")
            write_artifact(root, "relations/containment", "kind: relation\ntype: part_of\nstatus: canon\nmembers:\n  - {id: entities/b, role: part}\n  - {id: entities/a, role: whole}\n")
            write_artifact(root, "relations/custom", "kind: relation\ntype: custom\nstatus: canon\nmembers:\n  - {id: entities/b, role: to}\n  - {id: entities/c, role: from}\n")

            edges = {edge["id"]: edge for edge in project_view(load_canon(root), builtin_everything())["edges"]}

            self.assertEqual((edges["relations/standard"]["source"], edges["relations/standard"]["target"]), ("entities/b", "entities/a"))
            self.assertTrue(edges["relations/standard"]["directed"])
            self.assertEqual((edges["relations/containment"]["source"], edges["relations/containment"]["target"]), ("entities/b", "entities/a"))
            self.assertTrue(edges["relations/containment"]["directed"])
            self.assertFalse(edges["relations/custom"]["directed"])

    def test_audit_reifies_relation_members_and_keeps_every_spoke_endpoint_visible(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for artifact_id in ("entities/a", "entities/b", "entities/c"):
                write_artifact(root, artifact_id, "kind: entity\nstatus: canon\n")
            write_artifact(root, "relations/fact", "kind: relation\nstatus: canon\nmembers: [entities/a, entities/b]\n")
            write_artifact(root, "relations/assertion", "kind: relation\nstatus: canon\nmembers: [relations/fact, entities/c]\n")

            projection = project_view(load_canon(root), builtin_everything())
            node_ids = {node["id"] for node in projection["nodes"]}

            self.assertTrue({"relations/fact", "relations/assertion"}.issubset(node_ids))
            self.assertTrue(all(edge["source"] in node_ids and edge["target"] in node_ids for edge in projection["edges"]))

    def test_audit_preserves_authored_nary_shape_and_reifies_bad_standard_direction(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for artifact_id in ("entities/a", "entities/b", "entities/c"):
                write_artifact(root, artifact_id, "kind: entity\nstatus: canon\n")
            write_artifact(root, "entities/old", "kind: entity\nstatus: deprecated\n")
            write_artifact(root, "relations/formerly-many", "kind: relation\nstatus: canon\nmembers: [entities/a, entities/b, entities/old]\n")
            write_artifact(root, "relations/bad-order", "kind: relation\ntype: subordinate_to\nstatus: canon\nmembers:\n  - {id: entities/a, role: subordinate}\n  - {id: entities/b, role: subordinate}\n")

            projection = project_view(load_canon(root), builtin_everything())
            nodes = {node["id"] for node in projection["nodes"]}
            edges = {edge["id"]: edge for edge in projection["edges"]}

            self.assertTrue({"relations/formerly-many", "relations/bad-order"}.issubset(nodes))
            self.assertIn("relations/formerly-many::member:1", edges)
            self.assertTrue(all(not edges[f"relations/bad-order::member:{index}"]["directed"] for index in (1, 2)))
            self.assertTrue(any("reified with undirected spokes" in warning for warning in projection["warnings"]))

    def test_audit_reifies_nary_part_of_with_part_to_whole_direction(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for artifact_id in ("entities/whole", "entities/part-a", "entities/part-b"):
                write_artifact(root, artifact_id, "kind: entity\nstatus: canon\n")
            write_artifact(
                root, "relations/containment",
                "kind: relation\ntype: part_of\nstatus: canon\nmembers:\n"
                "  - {id: entities/whole, role: whole}\n"
                "  - {id: entities/part-a, role: part}\n"
                "  - {id: entities/part-b, role: part}\n",
            )

            projection = project_view(load_canon(root), builtin_everything())
            edges = {edge["id"]: edge for edge in projection["edges"]}

            self.assertEqual(
                (edges["relations/containment::member:2"]["source"], edges["relations/containment::member:2"]["target"]),
                ("entities/part-a", "relations/containment"),
            )
            self.assertEqual(
                (edges["relations/containment::member:3"]["source"], edges["relations/containment::member:3"]["target"]),
                ("entities/part-b", "relations/containment"),
            )
            self.assertEqual(
                (edges["relations/containment::member:1"]["source"], edges["relations/containment::member:1"]["target"]),
                ("relations/containment", "entities/whole"),
            )
            self.assertTrue(all(edge["directed"] for edge in edges.values()))

    def test_audit_includes_missing_status_as_canon_and_excludes_unknown_status(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            write_artifact(root, "entities/default", "kind: entity\n")
            write_artifact(root, "entities/unknown", "kind: entity\nstatus: archived\n")

            ids = {node["id"] for node in project_view(load_canon(root), builtin_everything())["nodes"]}

            self.assertIn("entities/default", ids)
            self.assertNotIn("entities/unknown", ids)


class DirectionProjectionTests(unittest.TestCase):
    def _projection(self, root: Path) -> dict:
        write_view(root, "name: Test\nselect:\n  status: [canon]\n")
        return project_view(load_canon(root), load_view(root, "views/test.yaml"))

    def test_binary_direction_uses_roles_not_member_order(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for artifact_id in ("entities/crown", "entities/captain"):
                write_artifact(root, artifact_id, "kind: entity\nstatus: canon\n")
            write_artifact(
                root, "relations/command",
                "kind: relation\ntype: subordinate_to\nstatus: canon\nmembers:\n"
                "  - {id: entities/captain, role: subordinate}\n"
                "  - {id: entities/crown, role: superior}\n",
            )

            edge = self._projection(root)["edges"][0]

            self.assertEqual((edge["source"], edge["target"]), ("entities/captain", "entities/crown"))
            self.assertEqual(edge["roles"], {"source": "subordinate", "target": "superior"})
            self.assertTrue(edge["directed"])

    def test_undirected_edge_preserves_authored_member_order(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for artifact_id in ("entities/a", "entities/b"):
                write_artifact(root, artifact_id, "kind: entity\nstatus: canon\n")
            write_artifact(root, "relations/bond", "kind: relation\nstatus: canon\nmembers: [entities/b, entities/a]\n")

            edge = self._projection(root)["edges"][0]

            self.assertEqual((edge["source"], edge["target"]), ("entities/b", "entities/a"))
            self.assertFalse(edge["directed"])

    def test_custom_direction_inherits_through_type_path(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for artifact_id in ("entities/a", "entities/b"):
                write_artifact(root, artifact_id, "kind: entity\nstatus: canon\n")
            write_artifact(root, "types/command", "kind: type\nlens: {direction: [leader, follower]}\n")
            write_artifact(
                root, "relations/order",
                "kind: relation\ntype: command/field\nstatus: canon\nmembers:\n"
                "  - {id: entities/b, role: follower}\n"
                "  - {id: entities/a, role: leader}\n",
            )

            edge = self._projection(root)["edges"][0]

            self.assertEqual((edge["source"], edge["target"]), ("entities/a", "entities/b"))
            self.assertTrue(edge["directed"])

    def test_unresolved_binary_direction_warns_and_falls_back(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for artifact_id in ("entities/a", "entities/b"):
                write_artifact(root, artifact_id, "kind: entity\nstatus: canon\n")
            write_artifact(root, "types/command", "kind: type\nlens: {direction: [leader, follower]}\n")
            write_artifact(
                root, "relations/broken",
                "kind: relation\ntype: command\nstatus: canon\nmembers:\n"
                "  - {id: entities/a, role: leader}\n"
                "  - {id: entities/b, role: leader}\n",
            )

            projection = self._projection(root)
            edge = projection["edges"][0]

            self.assertEqual((edge["source"], edge["target"]), ("entities/a", "entities/b"))
            self.assertFalse(edge["directed"])
            self.assertEqual(sum("direction leader -> follower cannot be resolved" in warning for warning in projection["warnings"]), 1)

    def test_invalid_direction_declaration_warns_and_is_ignored(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for artifact_id in ("entities/a", "entities/b"):
                write_artifact(root, artifact_id, "kind: entity\nstatus: canon\n")
            write_artifact(root, "types/command", "kind: type\nlens: {direction: leader}\n")
            write_artifact(
                root, "relations/command",
                "kind: relation\ntype: command\nstatus: canon\nmembers: [entities/b, entities/a]\n",
            )

            projection = self._projection(root)
            edge = projection["edges"][0]

            self.assertEqual((edge["source"], edge["target"]), ("entities/b", "entities/a"))
            self.assertFalse(edge["directed"])
            self.assertTrue(any("types/command.md: lens.direction must be" in warning for warning in projection["warnings"]))

    def test_reified_direction_routes_through_relation_node(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for artifact_id in ("entities/leader", "entities/a", "entities/b", "entities/witness"):
                write_artifact(root, artifact_id, "kind: entity\nstatus: canon\n")
            write_artifact(
                root, "relations/command",
                "kind: relation\ntype: subordinate_to\nstatus: canon\nmembers:\n"
                "  - {id: entities/a, role: subordinate}\n"
                "  - {id: entities/leader, role: superior}\n"
                "  - {id: entities/b, role: subordinate}\n"
                "  - {id: entities/witness, role: witness}\n",
            )

            edges = {edge["id"]: edge for edge in self._projection(root)["edges"]}

            self.assertEqual((edges["relations/command::member:2"]["source"], edges["relations/command::member:2"]["target"]), ("relations/command", "entities/leader"))
            self.assertTrue(edges["relations/command::member:2"]["directed"])
            for index in (1, 3):
                self.assertEqual((edges[f"relations/command::member:{index}"]["source"], edges[f"relations/command::member:{index}"]["target"]), ("entities/a" if index == 1 else "entities/b", "relations/command"))
                self.assertTrue(edges[f"relations/command::member:{index}"]["directed"])
            self.assertFalse(edges["relations/command::member:4"]["directed"])

    def test_reified_missing_direction_side_warns_and_makes_all_spokes_undirected(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for artifact_id in ("entities/a", "entities/b", "entities/c"):
                write_artifact(root, artifact_id, "kind: entity\nstatus: canon\n")
            write_artifact(
                root, "relations/broken-command",
                "kind: relation\ntype: subordinate_to\nstatus: canon\nmembers:\n"
                "  - {id: entities/a, role: subordinate}\n"
                "  - {id: entities/b, role: subordinate}\n"
                "  - {id: entities/c, role: witness}\n",
            )

            projection = self._projection(root)

            self.assertTrue(all(not edge["directed"] for edge in projection["edges"]))
            self.assertEqual(sum("direction subordinate -> superior cannot be resolved" in warning for warning in projection["warnings"]), 1)

    def test_every_projected_edge_has_a_boolean_directed_key(self) -> None:
        projection = project_view(load_canon(ACCEPTANCE), load_view(ACCEPTANCE, "views/all-behaviors.yaml"))

        self.assertTrue(projection["edges"])
        self.assertTrue(all(isinstance(edge.get("directed"), bool) for edge in projection["edges"]))


class AcceptanceWorldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.projection = project_view(
            load_canon(ACCEPTANCE),
            load_view(ACCEPTANCE, "views/all-behaviors.yaml"),
        )

    def test_acceptance_world_is_clean_and_covers_every_behavior(self) -> None:
        nodes = {node["id"]: node for node in self.projection["nodes"]}
        edges = {edge["id"]: edge for edge in self.projection["edges"]}
        behaviors = {edge["behavior"] for edge in edges.values()}

        self.assertEqual(self.projection["warnings"], [])
        self.assertEqual(nodes["entities/outer-ward"]["parent"], "entities/citadel")
        self.assertEqual(nodes["entities/citadel-gate"]["parent"], "entities/citadel")
        self.assertIn("relations/ward-in-citadel::member:1", edges)
        self.assertIn("relations/ward-in-citadel::member:2", edges)
        self.assertTrue({"nest", "hide", "edge"}.issubset(behaviors))
        self.assertEqual(nodes["entities/citadel"]["chips"][0]["type"], "state/population")
        self.assertIn("relations/siege-participation", nodes)
        self.assertIn("relations/guild-holds-oath", nodes)

    def test_acceptance_world_marks_dormancy_practice_and_fiat(self) -> None:
        nodes = {node["id"]: node for node in self.projection["nodes"]}

        self.assertNotIn("dormant", nodes["ideas/watch-oath"]["badges"])
        self.assertIn("dormant", nodes["ideas/forgotten-prophecy"]["badges"])
        self.assertIn("practice", nodes["actions/night-watch"]["badges"])
        self.assertNotIn("practice", nodes["actions/first-siege"]["badges"])
        self.assertIn("fiat", nodes["entities/citadel"]["badges"])

    def test_beliefs_view_prunes_unrelated_entities(self) -> None:
        projection = project_view(
            load_canon(ACCEPTANCE),
            load_view(ACCEPTANCE, "views/02-shared-beliefs.yaml"),
        )
        node_ids = {node["id"] for node in projection["nodes"]}
        edge_ids = {edge["id"] for edge in projection["edges"]}

        self.assertTrue(
            {
                "ideas/watch-oath",
                "ideas/oath-commentary",
                "ideas/forgotten-prophecy",
                "entities/watch-guild",
            }.issubset(node_ids)
        )
        self.assertNotIn("entities/captain-vale", node_ids)
        self.assertNotIn("entities/citadel", node_ids)
        self.assertNotIn("entities/outer-ward", node_ids)
        self.assertIn("relations/guild-holds-oath", edge_ids)

    def test_ranked_actions_view_prunes_unrelated_entities(self) -> None:
        projection = project_view(
            load_canon(ACCEPTANCE),
            load_view(ACCEPTANCE, "views/04-ranked-actions.yaml"),
        )
        node_ids = {node["id"] for node in projection["nodes"]}

        self.assertTrue(
            {
                "actions/first-siege",
                "actions/night-watch",
                "entities/captain-vale",
                "entities/watch-guild",
                "relations/siege-participation",
            }.issubset(node_ids)
        )
        self.assertNotIn("entities/citadel", node_ids)

    def test_direction_hierarchy_view_isolates_subordinate_to_for_dagre(self) -> None:
        projection = project_view(
            load_canon(ACCEPTANCE),
            load_view(ACCEPTANCE, "views/07-direction-hierarchy.yaml"),
        )
        edge = projection["edges"][0]

        self.assertEqual(projection["warnings"], [])
        self.assertEqual(projection["view"]["layout"], "dagre")
        self.assertEqual([item["id"] for item in projection["edges"]], ["relations/captain-subordinate"])
        self.assertEqual((edge["source"], edge["target"]), ("entities/captain-vale", "entities/watch-guild"))
        self.assertTrue(edge["directed"])

    def test_cli_reports_projection_warnings_on_stderr(self) -> None:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(sys.path)
        with TemporaryDirectory() as directory:
            root = Path(directory)
            write_artifact(
                root,
                "entities/x",
                "kind: entity\ntype: missing/child\nstatus: canon\n",
            )
            write_view(root, "name: Test\nselect:\n  status: [canon]\n")
            result = subprocess.run(
                [
                    sys.executable,
                    str(VIEWER_ROOT / "view.py"),
                    str(root),
                    "--view",
                    "views/test.yaml",
                    "--json",
                ],
                check=False,
                capture_output=True,
                env=environment,
                text=True,
            )

            self.assertEqual(result.returncode, 0)
            self.assertIn("warning:", result.stderr)
            self.assertEqual(len(json.loads(result.stdout)["nodes"]), 1)


if __name__ == "__main__":
    unittest.main()
