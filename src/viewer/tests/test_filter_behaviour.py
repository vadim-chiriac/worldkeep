"""Run the shipped filter code, rather than asserting on its source text.

The filter panel is the one part of the viewer that lives entirely in the
browser, and string assertions over the bundle proved able to pass while the
behaviour was wrong: a containment chain was being traced through a relation
set that had already dropped every relation touching a hidden artifact, so
hiding a level orphaned everything below it and no test noticed.

These tests extract `relationModel` and `filteredProjection` from the rendered
document and execute them under Node against a real canon. They skip when Node
is unavailable, which keeps the suite runnable everywhere without pretending to
have checked something it did not.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from viewer.load import load_canon, load_view
from viewer.project import project_view
from viewer.render_graph import render_graph


VIEWER_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = VIEWER_ROOT.parents[1]
SEED = WORKSPACE_ROOT / "src" / "skills" / "worldbuilding-scribe" / "assets" / "seed-world"

HARNESS = r"""
import fs from "node:fs";
// Normalize on the way in as well as on the way out: a document produced by
// any other tool on Windows would otherwise defeat every split below.
const html = fs.readFileSync(process.argv[2], "utf8").replace(/\r\n/g, "\n");
const data = JSON.parse(html.split('id="projection-data">')[1].split("</script>")[0]);
const body = html.split("<script>\n(function(){")[1];
const take = (name) => {
  const start = body.indexOf(`  function ${name}(`);
  let i = body.indexOf("{", start), depth = 0;
  for (; i < body.length; i++) {
    if (body[i] === "{") depth++;
    else if (body[i] === "}") { depth--; if (!depth) break; }
  }
  return body.slice(start, i + 1);
};
const api = new Function(`
  const exactType=(value)=>value||"(untyped)";
  const artifactKey=(kind,type)=>JSON.stringify([kind,exactType(type)]);
  let artifactTypes=new Set(),relationTypes=new Set();
  ${take("relationModel")}
  ${take("filteredProjection")}
  return {filteredProjection,setFilters:(a,r)=>{artifactTypes=a;relationTypes=r}};
`)();

const hiddenType = process.argv[3] || "";
const droppedRelation = process.argv[4] || "";
const key = (n) => JSON.stringify([n.kind, n.type || "(untyped)"]);
const artifacts = new Set(
  data.nodes.filter((n) => n.kind !== "relation" && (n.type || "") !== hiddenType).map(key)
);
const relations = new Set(
  data.edges.map((e) => e.type || "(untyped)").filter((t) => t !== droppedRelation)
);
api.setFilters(artifacts, relations);
const result = api.filteredProjection(data);
console.log(JSON.stringify({
  artifacts: result.artifacts,
  relations: result.relations,
  parents: Object.fromEntries(result.projection.nodes.map((n) => [n.id, n.parent || null])),
}));
"""


def _world(root: Path) -> None:
    """A three-deep containment chain plus one that must not compose."""
    shutil.copytree(SEED, root, dirs_exist_ok=True)
    (root / "entities").mkdir(exist_ok=True)
    (root / "relations").mkdir(exist_ok=True)
    (root / "types").mkdir(exist_ok=True)

    def write(path: str, text: str) -> None:
        (root / path).write_text(text, encoding="utf-8")

    for artifact_id, type_name in (
        ("country", "place"),
        ("region", "regiune"),
        ("county", "judet"),
        ("seat", "resedinta"),
    ):
        write(
            f"entities/{artifact_id}.md",
            f"---\nid: entities/{artifact_id}\nkind: entity\ntype: {type_name}\n"
            f"name: {artifact_id.title()}\nstatus: canon\n---\n",
        )
    for type_name in ("regiune", "judet", "resedinta"):
        write(
            f"types/{type_name}.md",
            f"---\nid: types/{type_name}\nkind: type\napplies_to_kind: entity\nstatus: canon\n---\n",
        )
    for child, parent in (("region", "country"), ("county", "region"), ("seat", "county")):
        write(
            f"relations/{child}-in-{parent}.md",
            f"---\nid: relations/{child}-in-{parent}\nkind: relation\ntype: part_of\n"
            f"status: canon\nmembers:\n- {{id: entities/{child}, role: part}}\n"
            f"- {{id: entities/{parent}, role: whole}}\n---\n",
        )
    write(
        "views/chain.yaml",
        "name: Chain\nrender: graph\nselect:\n  kinds: [entity, relation]\nlayout: fcose\n",
    )


@unittest.skipUnless(shutil.which("node"), "Node is required to execute the viewer bundle")
class FilterBehaviourTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        root = Path(cls._tmp.name) / "world"
        _world(root)
        canon = load_canon(root)
        cls.html = Path(cls._tmp.name) / "chain.html"
        # newline="\n" is load-bearing, not tidiness: the harness locates the
        # bundle by splitting on a literal "\n", and Windows would otherwise
        # translate every one of them to "\r\n" on the way out.
        cls.html.write_text(
            render_graph(project_view(canon, load_view(root, "views/chain.yaml")), canon),
            encoding="utf-8",
            newline="\n",
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def filter(self, hidden_type: str = "", dropped_relation: str = "") -> dict:
        with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as handle:
            handle.write(HARNESS)
            script = handle.name
        try:
            done = subprocess.run(
                ["node", script, str(self.html), hidden_type, dropped_relation],
                capture_output=True, text=True, check=False,
            )
        finally:
            Path(script).unlink(missing_ok=True)
        # check=True would raise before anyone sees the JS error, which turns a
        # one-line fault into a page of Python traceback that says nothing.
        self.assertEqual(done.returncode, 0, done.stderr or done.stdout)
        return json.loads(done.stdout)

    def test_unfiltered_chain_nests_each_level_in_the_next(self) -> None:
        parents = self.filter()["parents"]

        self.assertEqual(parents["entities/seat"], "entities/county")
        self.assertEqual(parents["entities/county"], "entities/region")
        self.assertEqual(parents["entities/region"], "entities/country")
        self.assertIsNone(parents["entities/country"])

    def test_hiding_a_middle_level_reattaches_to_the_one_above(self) -> None:
        """The regression: this used to orphan everything below the hidden level,
        because the chain was traced through relations the cascade had already
        dropped for touching a hidden artifact."""
        parents = self.filter(hidden_type="judet")["parents"]

        self.assertNotIn("entities/county", parents)
        self.assertEqual(parents["entities/seat"], "entities/region")

    def test_hiding_two_levels_still_finds_the_nearest_survivor(self) -> None:
        parents = self.filter(hidden_type="regiune")["parents"]

        self.assertEqual(parents["entities/county"], "entities/country")
        self.assertEqual(parents["entities/seat"], "entities/county")

    def test_unticking_the_relation_removes_nesting_rather_than_rerouting_it(self) -> None:
        parents = self.filter(dropped_relation="part_of")["parents"]

        self.assertTrue(all(parent is None for parent in parents.values()), parents)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
