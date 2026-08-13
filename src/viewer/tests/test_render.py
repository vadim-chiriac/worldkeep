from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from viewer.load import list_views, load_canon, load_view
from viewer.project import project_view
from viewer.render_graph import (
    ASSETS,
    render_graph,
    render_graph_document,
    render_markdown,
)


VIEWER_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = VIEWER_ROOT.parents[1]
EXAMPLE = WORKSPACE_ROOT / "Testing" / "fixtures" / "two-allied-countries"
ACCEPTANCE = WORKSPACE_ROOT / "Testing" / "fixtures" / "viewer-acceptance"


class RendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.canon = load_canon(EXAMPLE)
        cls.projection = project_view(
            cls.canon, load_view(EXAMPLE, "views/political.yaml")
        )

    def test_cdn_html_contains_projection_and_pinned_scripts(self) -> None:
        rendered = render_graph(self.projection, self.canon)

        self.assertIn("<title>Political View</title>", rendered)
        self.assertIn('id="projection-data"', rendered)
        self.assertIn('id="artifact-details"', rendered)
        for _, url in ASSETS:
            self.assertIn(f'src="{url}"', rendered)

    def test_vendor_html_inlines_every_script(self) -> None:
        rendered = render_graph(self.projection, self.canon, vendor=True)

        self.assertNotIn('<script src="https://unpkg.com/', rendered)
        for filename, _ in ASSETS:
            self.assertIn(f'data-vendor="{filename}"', rendered)
        self.assertGreater(len(rendered), 700_000)

    def test_markdown_escapes_active_content(self) -> None:
        rendered = render_markdown(
            '<script>window.pwned = true</script>\n\n'
            '<img src=x onerror=alert(1)>\n\n**Safe bold** and `code`.'
        )

        self.assertNotIn("<script>", rendered)
        self.assertNotIn("<img", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", rendered)
        self.assertIn("<strong>Safe bold</strong>", rendered)
        self.assertIn("<code>code</code>", rendered)

    def test_cli_writes_cdn_and_vendor_html(self) -> None:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(sys.path)
        with TemporaryDirectory() as directory:
            cdn_path = Path(directory) / "political.html"
            offline_path = Path(directory) / "political-offline.html"
            base = [
                sys.executable,
                str(VIEWER_ROOT / "view.py"),
                str(EXAMPLE),
                "--view",
                "views/political.yaml",
            ]
            cdn = subprocess.run(
                [*base, "-o", str(cdn_path)],
                check=False,
                capture_output=True,
                env=environment,
                text=True,
            )
            offline = subprocess.run(
                [*base, "-o", str(offline_path), "--vendor"],
                check=False,
                capture_output=True,
                env=environment,
                text=True,
            )

            self.assertEqual(cdn.returncode, 0, cdn.stderr)
            self.assertEqual(offline.returncode, 0, offline.stderr)
            self.assertLess(cdn_path.stat().st_size, offline_path.stat().st_size)
            self.assertIn("Political View", cdn_path.read_text(encoding="utf-8"))

    def test_embedded_projection_is_the_stage_2_contract(self) -> None:
        rendered = render_graph(self.projection, self.canon)
        payload = rendered.split('id="projection-data">', 1)[1].split("</script>", 1)[0]

        self.assertEqual(json.loads(payload), self.projection)

    def test_renderer_contains_dormant_and_practice_marks(self) -> None:
        rendered = render_graph(self.projection, self.canon)

        self.assertIn('node[dormant = 1]', rendered)
        self.assertIn('"border-style":"dashed"', rendered)
        self.assertIn('node[practice = 1]', rendered)
        self.assertIn('"outline-width":"2px"', rendered)

    def test_renderer_maps_directed_edges_to_target_arrowheads(self) -> None:
        rendered = render_graph(self.projection, self.canon)

        self.assertIn("directed:edge.directed?1:0", rendered)
        self.assertIn('selector:"edge[directed = 1]"', rendered)
        self.assertIn('"target-arrow-shape":"triangle"', rendered)
        self.assertIn('"target-arrow-color":"data(color)"', rendered)
        self.assertIn('"target-arrow-fill":"filled"', rendered)
        self.assertIn('"arrow-scale":.9', rendered)

    def test_single_view_has_no_multi_view_shell(self) -> None:
        rendered = render_graph(self.projection, self.canon, vendor=True)

        self.assertNotIn('id="view-picker"', rendered)
        self.assertNotIn('id="multi-view-data"', rendered)
        for filename, _ in ASSETS:
            self.assertEqual(rendered.count(f'data-vendor="{filename}"'), 1)

    def test_offline_renderer_includes_projection_derived_type_filters(self) -> None:
        rendered = render_graph(self.projection, self.canon, vendor=True)

        self.assertIn('id="filters"', rendered)
        self.assertIn("Filter this view", rendered)
        self.assertIn("All / Reset", rendered)
        self.assertIn("(untyped)", rendered)
        self.assertIn("relationModel(projection)", rendered)
        self.assertIn("filteredProjection(projection)", rendered)
        self.assertIn("relations:valid.size", rendered)

    def test_filter_rows_keep_artifact_kind_type_keys_and_rebuild_active_data(self) -> None:
        rendered = render_graph(self.projection, self.canon)

        # Artifact selection is keyed by kind plus exact type; grouping for
        # display must retain that key rather than passing a path-only value to
        # the checkbox. Rebuilding also makes inspector chip lookup use the
        # filtered projection, not stale unfiltered data.
        self.assertIn('grouped.get(kind).set(key,count)', rendered)
        self.assertIn('const artifactKey=(kind,type)=>JSON.stringify([kind,exactType(type)])', rendered)
        self.assertIn('const [kind]=artifactKeyParts(key)', rendered)
        self.assertNotIn('node.kind+"\\u0000"', rendered)
        self.assertNotIn('key.split("\\u0000")', rendered)
        self.assertIn('input.dataset.filterKey=key', rendered)
        self.assertIn('window.__WB_DATA__=result.projection', rendered)
        self.assertIn('function clearInspector(){inspector.innerHTML=', rendered)
        self.assertLess(rendered.index('function clearInspector(){inspector.innerHTML='), rendered.index('function applyCurrentFilters()'))
        self.assertIn('clearInspector();if(!cy.nodes().length)', rendered)
        self.assertIn('if(enabled)clearFilterSearch()', rendered)
        self.assertIn('data-filter-action="all" disabled', rendered)
        self.assertIn('aria-label="Search filter types" disabled', rendered)

    def test_filter_toggles_reuse_remembered_positions_without_relayout(self) -> None:
        rendered = render_graph(self.projection, self.canon)
        filter_code = rendered.split('function applyCurrentFilters()', 1)[1].split(
            'document.getElementById("filter-catalogue")', 1
        )[0]

        # The initial layout populates the cache. A filter toggle records any
        # user moves, reinstates positions for surviving/returning nodes, and
        # only refits the preset layout; it must not randomize fcose again.
        self.assertIn('let activeProjection=data,artifactTypes=new Set(),relationTypes=new Set(),positionMemory=new Map()', rendered)
        self.assertIn('function rememberNodePositions()', rendered)
        self.assertIn('function markViewerReady(state){rememberNodePositions();setFilterControlsReady(true);window.__WB_VIEWER_READY__=true', rendered)
        self.assertIn('function elementsFor(projection,positions=positionMemory)', rendered)
        self.assertIn('const position=positions.get(node.id);if(position)item.position=position', rendered)
        self.assertIn('rememberNodePositions();const result=filteredProjection(activeProjection)', filter_code)
        self.assertIn('cy.add(elementsFor(result.projection,positionMemory))', filter_code)
        self.assertIn('const options={name:"preset",animate:false,fit:false,padding:58}', filter_code)
        self.assertNotIn('randomize:true', filter_code)
        self.assertIn('const pan=cy.pan(),viewport={zoom:cy.zoom(),pan:{x:pan.x,y:pan.y}}', filter_code)
        self.assertEqual(filter_code.count('restoreViewport(viewport)'), 2)
        self.assertIn('function restoreViewport(viewport){cy.zoom(viewport.zoom);cy.pan(viewport.pan)}', rendered)
        self.assertIn('function setFilterControlsReady(ready)', rendered)
        self.assertIn('input.disabled=!filtersReady', rendered)
        self.assertIn('setFilterControlsReady(true)', rendered)
        # The one layout run happens after the filter machinery is installed and
        # disabled, never as a side effect of toggling a filter.
        self.assertIn(
            'window.__WB_FILTERED_PROJECTION__=()=>filteredProjection(activeProjection).projection;\n'
            '  setFilterControlsReady(false);\n\n  const requestedLayout=',
            rendered,
        )


class ViewerAffordanceTests(unittest.TestCase):
    """The three things an author does with a rendered view besides read it."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.canon = load_canon(EXAMPLE)
        cls.rendered = render_graph(
            project_view(cls.canon, load_view(EXAMPLE, "views/political.yaml")),
            cls.canon,
        )

    def test_dagre_is_refused_on_a_nested_projection_and_says_why(self) -> None:
        """dagre ranks compound children as if flat — see cytoscape.js#844."""
        self.assertIn("window.__WB_RESOLVE_LAYOUT__=function(requested,projection)", self.rendered)
        self.assertIn('if(requested!=="dagre")return requested;', self.rendered)
        self.assertIn('if(!(projection.nodes||[]).some((node)=>node.parent))return requested;', self.rendered)
        self.assertIn("dagre cannot lay out nested graphs", self.rendered)
        self.assertIn("window.__WB_RESOLVE_LAYOUT__(requestedLayout,data)", self.rendered)

    def test_multi_view_documents_resolve_the_layout_on_every_switch(self) -> None:
        """Switching views re-runs a layout, so the guard has to run there too."""
        document = render_graph_document(
            [project_view(self.canon, view) for view in list_views(EXAMPLE)[:2]],
            self.canon,
        )

        self.assertIn("window.__WB_RESOLVE_LAYOUT__(declared,projection)", document)

    def test_find_by_name_dims_instead_of_removing(self) -> None:
        """Hiding would move the survivors; dimming keeps the author's bearings."""
        self.assertIn('id="node-search"', self.rendered)
        self.assertIn('{selector:".wb-faded",style:{opacity:.07}}', self.rendered)
        self.assertIn(
            'cy.elements().not(matches.union(matches.ancestors())).addClass("wb-faded");',
            self.rendered,
        )
        # A search must survive a filter toggle, which rebuilds every element.
        self.assertIn("if(window.__WB_APPLY_NODE_SEARCH__)window.__WB_APPLY_NODE_SEARCH__()", self.rendered)

    def test_the_matched_set_outlives_the_query_text(self) -> None:
        """Emptying the box must not change two things at once: the set is the
        state, and a separate toggle decides whether it is painted."""
        self.assertIn('id="node-search-highlight"', self.rendered)
        self.assertIn('id="node-search-clear"', self.rendered)
        self.assertIn("let searchResults=[],searchActive=false;", self.rendered)
        # An empty query repaints; it never empties the set.
        self.assertIn('if(!query){paintSearch();return}', self.rendered)
        self.assertIn("function clearSearch(){\n    searchResults=[];searchActive=false;", self.rendered)
        self.assertIn(
            'if(!document.getElementById("node-search-highlight").checked)return;',
            self.rendered,
        )

    def test_viewport_rendering_is_cheap_while_panning(self) -> None:
        """Compound parents are re-measured every frame without these."""
        self.assertIn("textureOnViewport:true", self.rendered)

    def test_dropping_edges_while_moving_is_paid_only_by_big_graphs(self) -> None:
        """A small canon never had a frame-rate problem, so it should not lose
        its edges while panning to buy a fix for one it does not have."""
        self.assertIn("const BUSY_EDGES=60;", self.rendered)
        self.assertIn("const busy=data.edges.length>=BUSY_EDGES;", self.rendered)
        self.assertIn("hideEdgesOnViewport:busy", self.rendered)
        # The drag handler is guarded by the same measurement.
        self.assertIn('cy.on("grab","node",(event)=>{\n    if(!busy)return;', self.rendered)

    def test_dragging_quiets_the_edges_it_is_not_moving(self) -> None:
        """Cytoscape's viewport levers do not cover drags, so we cover them."""
        self.assertIn('cy.on("grab","node"', self.rendered)
        self.assertIn('cy.edges().not(touched).addClass("wb-quiet")', self.rendered)
        self.assertIn('touched.addClass("wb-hushed")', self.rendered)
        # A drag must leave no trace once it ends.
        self.assertIn('cy.on("free","node",()=>{cy.edges().removeClass("wb-quiet wb-hushed")})', self.rendered)
        self.assertIn('{selector:"edge.wb-quiet",style:{visibility:"hidden"}}', self.rendered)

    def test_search_results_are_a_navigable_list(self) -> None:
        self.assertIn('id="node-search-results"', self.rendered)
        self.assertIn("function renderSearchResults(ids)", self.rendered)
        self.assertIn('button.dataset.goto=id;', self.rendered)

    def test_inspector_lists_the_relations_an_artifact_is_in(self) -> None:
        """An artifact's connections are canon, so they come from the whole
        view rather than from whatever the filters currently leave visible."""
        self.assertIn("function connectionsFor(id)", self.rendered)
        self.assertIn("const projection=activeProjection,found=new Map();", self.rendered)
        self.assertIn("function renderConnections(id)", self.rendered)
        self.assertIn('relation.dataset.goto=item.relationId;', self.rendered)
        self.assertIn('other.dataset.goto=item.otherId;', self.rendered)

    def test_nesting_collapses_only_through_one_relation_type(self) -> None:
        """part_of composes, so hiding a county must not orphan its seat. A
        custom nesting type need not compose, so the run has to be unbroken."""
        self.assertIn("const next=chain.get(step.parent);", self.rendered)
        self.assertIn("if(!next||next.type!==type)return;", self.rendered)
        # The chain obeys the relation-type filter but not the cascade that
        # drops relations touching a hidden artifact — those are exactly the
        # ones it has to cross. See tests/test_filter_behaviour.py, which
        # executes this rather than reading it.
        self.assertIn(
            '(edge)=>edge.behavior==="nest"&&typeAllowed.has(edge.id.split("::member:")[0])',
            self.rendered,
        )
        self.assertIn("guard++<64", self.rendered)

    def test_going_to_an_artifact_is_decided_in_one_place(self) -> None:
        """The relation list, the search list and a graph click must agree."""
        self.assertIn("function goTo(id)", self.rendered)
        self.assertIn("cy.animate({center:{eles:element}},{duration:220});", self.rendered)
        self.assertEqual(self.rendered.count('event.target.closest("[data-goto]")'), 2)


class MultiViewRendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.canon = load_canon(ACCEPTANCE)
        cls.views = [
            load_view(ACCEPTANCE, "views/01-shared-overview.yaml"),
            load_view(ACCEPTANCE, "views/02-shared-beliefs.yaml"),
            load_view(ACCEPTANCE, "views/05-empty.yaml"),
        ]
        cls.projections = [project_view(cls.canon, view) for view in cls.views]

    def test_document_has_one_asset_copy_and_all_views(self) -> None:
        rendered = render_graph_document(
            self.projections,
            self.canon,
            explicit_layouts=["layout" in view.data for view in self.views],
            view_paths=[view.relative_path for view in self.views],
            vendor=True,
        )

        self.assertIn('id="view-picker"', rendered)
        self.assertIn('id="multi-view-data"', rendered)
        for filename, _ in ASSETS:
            self.assertEqual(rendered.count(f'data-vendor="{filename}"'), 1)
        payload = rendered.split('id="multi-view-data">', 1)[1].split("</script>", 1)[0]
        self.assertEqual(json.loads(payload)["views"], self.projections)
        self.assertLess(len(rendered.encode("utf-8")), 1_000_000)

    def test_multi_view_reuses_shared_directed_edge_rule(self) -> None:
        rendered = render_graph_document(
            self.projections,
            self.canon,
            explicit_layouts=["layout" in view.data for view in self.views],
            view_paths=[view.relative_path for view in self.views],
            vendor=True,
        )

        self.assertEqual(rendered.count('selector:"edge[directed = 1]"'), 1)
        self.assertIn("window.__WB_ELEMENTS_FOR__", rendered)

    def test_multi_view_resets_projection_derived_filters(self) -> None:
        rendered = render_graph_document(
            self.projections,
            self.canon,
            explicit_layouts=["layout" in view.data for view in self.views],
            view_paths=[view.relative_path for view in self.views],
            vendor=True,
        )

        self.assertIn("window.__WB_RESET_FILTERS__(projection)", rendered)
        self.assertIn("window.__WB_FILTERED_PROJECTION__()", rendered)

    def test_cli_multi_json_wraps_but_single_json_stays_bare(self) -> None:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(sys.path)
        base = [sys.executable, str(VIEWER_ROOT / "view.py"), str(ACCEPTANCE)]
        multi = subprocess.run(
            [
                *base,
                "--view",
                "views/01-shared-overview.yaml",
                "--view",
                "views/02-shared-beliefs.yaml",
                "--json",
            ],
            check=False,
            capture_output=True,
            env=environment,
            text=True,
        )
        single = subprocess.run(
            [*base, "--view", "views/01-shared-overview.yaml", "--json"],
            check=False,
            capture_output=True,
            env=environment,
            text=True,
        )

        self.assertEqual(multi.returncode, 0, multi.stderr)
        self.assertEqual(single.returncode, 0, single.stderr)
        self.assertEqual(set(json.loads(multi.stdout)), {"views"})
        self.assertEqual(len(json.loads(multi.stdout)["views"]), 2)
        self.assertIn("view", json.loads(single.stdout))
        self.assertNotIn("views", json.loads(single.stdout))

    def test_cli_all_views_is_path_ordered_and_keeps_v0_subset(self) -> None:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(sys.path)
        result = subprocess.run(
            [
                sys.executable,
                str(VIEWER_ROOT / "view.py"),
                str(ACCEPTANCE),
                "--all-views",
                "--json",
            ],
            check=False,
            capture_output=True,
            env=environment,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        names = [projection["view"]["name"] for projection in payload["views"]]
        expected = [view.name for view in list_views(ACCEPTANCE)]
        self.assertEqual(names, expected)
        empty = next(
            projection
            for projection in payload["views"]
            if projection["view"]["name"] == "Empty selection"
        )
        self.assertEqual(empty["nodes"], [])
        forbidden = {"aggregate_count", "collapsed", "hidden_children", "lifted_from", "series"}

        def visit(value: object) -> None:
            if isinstance(value, dict):
                self.assertTrue(forbidden.isdisjoint(value))
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(payload)


if __name__ == "__main__":
    unittest.main()
