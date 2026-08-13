"""Render a Viewer v0 projection as one browser-openable HTML file."""

from __future__ import annotations

from html import escape
import json
from pathlib import Path
import re
from typing import Any, Mapping

from .load import Canon


class RenderError(ValueError):
    """The graph cannot be rendered with the requested assets."""


ASSETS = (
    (
        "cytoscape.min.js",
        "https://unpkg.com/cytoscape@3.34.0/dist/cytoscape.min.js",
    ),
    ("layout-base.js", "https://unpkg.com/layout-base@2.0.1/layout-base.js"),
    ("cose-base.js", "https://unpkg.com/cose-base@2.2.0/cose-base.js"),
    (
        "cytoscape-fcose.js",
        "https://unpkg.com/cytoscape-fcose@2.2.0/cytoscape-fcose.js",
    ),
    (
        "cytoscape-dagre.min.js",
        "https://unpkg.com/cytoscape-dagre@4.0.0/dist/cytoscape-dagre.min.js",
    ),
)


def _safe_json(value: Any) -> str:
    """Serialize data for an application/json script without closing the tag."""
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _inline_markup(text: str) -> str:
    safe = escape(text, quote=False)
    safe = re.sub(r"`([^`]+)`", r"<code>\1</code>", safe)
    safe = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", safe)
    safe = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", safe)
    return safe


def render_markdown(text: str) -> str:
    """Render the small safe Markdown subset needed by the inspector."""
    lines = text.splitlines()
    output: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            output.append(f"<p>{_inline_markup(' '.join(paragraph))}</p>")
            paragraph.clear()

    def flush_list() -> None:
        if list_items:
            output.append("<ul>" + "".join(f"<li>{item}</li>" for item in list_items) + "</ul>")
            list_items.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            flush_list()
            continue
        heading = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            flush_list()
            level = len(heading.group(1)) + 2
            output.append(f"<h{level}>{_inline_markup(heading.group(2))}</h{level}>")
        elif stripped.startswith(("- ", "* ")):
            flush_paragraph()
            list_items.append(_inline_markup(stripped[2:].strip()))
        elif stripped.startswith("> "):
            flush_paragraph()
            flush_list()
            output.append(f"<blockquote>{_inline_markup(stripped[2:].strip())}</blockquote>")
        else:
            flush_list()
            paragraph.append(stripped)
    flush_paragraph()
    flush_list()
    return "".join(output) or "<p class=\"empty\">No description.</p>"


def _details(canon: Canon) -> dict[str, dict[str, Any]]:
    return {
        artifact.id: {
            "id": artifact.id,
            "name": artifact.name,
            "kind": artifact.kind,
            "type": artifact.type,
            "status": artifact.frontmatter.get("status", "canon"),
            "frontmatter": artifact.frontmatter,
            "body_html": render_markdown(artifact.body),
        }
        for artifact in canon.artifacts.values()
    }


def _script_tags(vendor: bool, vendor_dir: Path) -> str:
    tags: list[str] = []
    for filename, url in ASSETS:
        if vendor:
            path = vendor_dir / filename
            if not path.is_file():
                raise RenderError(f"vendored browser asset is missing: {path}")
            try:
                source = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                raise RenderError(f"cannot read vendored browser asset {path}: {exc}") from exc
            source = source.replace("</script", "<\\/script")
            tags.append(f"<script data-vendor=\"{escape(filename)}\">{source}</script>")
        else:
            tags.append(f"<script src=\"{escape(url, quote=True)}\"></script>")
    return "\n".join(tags)


HTML_TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
:root{color-scheme:dark;--bg:#0d1217;--panel:#171d23;--panel2:#11171d;--line:#303943;--text:#f0ede6;--muted:#9ba6af;--accent:#78a96b}
*{box-sizing:border-box}html,body{height:100%;margin:0;background:var(--bg);color:var(--text);font:16px/1.45 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;overflow:hidden}
body:before{content:"";position:fixed;inset:0;pointer-events:none;background:radial-gradient(circle at 50% 38%,rgba(61,88,111,.11),transparent 44%),linear-gradient(120deg,rgba(255,255,255,.018),transparent 38%)}
.shell{display:grid;grid-template-columns:238px minmax(0,1fr) 328px;height:100%}.panel{position:relative;z-index:3;background:rgba(22,28,34,.94);backdrop-filter:blur(14px)}
.left{border-right:1px solid var(--line);padding:28px 24px;overflow:auto}.right{border-left:1px solid var(--line);padding:30px 26px;overflow:auto}.stage{position:relative;min-width:0}.title{margin:0 0 26px;font-size:27px;line-height:1.1;letter-spacing:-.025em}.menu{width:46px;height:46px;border:1px solid #3a444e;border-radius:9px;background:#1b2229;color:var(--text);font-size:23px;cursor:pointer}.menu:hover{border-color:#66737e}.filters,.legend{margin-top:28px}.filters summary,.legend h2,.inspector h2{font-size:12px;text-transform:uppercase;letter-spacing:.14em;color:var(--muted);margin:0 0 15px}.filter-actions{display:flex;gap:7px;margin:9px 0}.filter-actions button{border:1px solid #3a444e;border-radius:6px;background:#1b2229;color:var(--text);font:12px inherit;padding:4px 7px;cursor:pointer}.filter-search{width:100%;margin:5px 0 9px;padding:6px 8px;border:1px solid #3a444e;border-radius:6px;background:#11171d;color:var(--text);font:12px inherit}.filter-group h3{margin:13px 0 5px;font-size:11px;color:var(--muted)}.filter-row{display:flex;gap:7px;align-items:start;margin:5px 0;font-size:12px;overflow-wrap:anywhere}.filter-row input{margin:3px 0 0}.filter-count{color:var(--muted);font-size:11px}.filter-summary{margin:8px 0;color:#c8d0d6;font-size:12px}.finder{margin-top:26px}.finder label{display:block;margin:0 0 8px;font-size:12px;text-transform:uppercase;letter-spacing:.14em;color:var(--muted)}.finder-toggle{display:flex;gap:7px;align-items:center;margin:7px 0 4px;color:#c8d0d6;font-size:12px;cursor:pointer}.finder-clear{margin-top:7px;padding:4px 7px;border:1px solid #3a444e;border-radius:6px;background:#1b2229;color:var(--text);font:12px inherit;cursor:pointer}.finder-clear:hover{border-color:#66737e}.finder-summary{min-height:15px;margin:2px 0 0;color:var(--muted);font-size:11px}.finder-results{list-style:none;max-height:220px;overflow-y:auto;margin:8px 0 0;padding:0}.finder-results:empty{margin:0}.finder-hit{display:flex;flex-direction:column;gap:1px;width:100%;padding:5px 7px;border:1px solid transparent;border-radius:6px;background:none;color:var(--text);font:12px/1.3 inherit;text-align:left;cursor:pointer}.finder-hit:hover{border-color:#3a444e;background:#1b2229}.finder-hit-name{overflow-wrap:anywhere}.finder-hit-type{color:var(--muted);font-size:10px}.relation-list{list-style:none;margin:0;padding:0}.relation-list li{display:flex;flex-wrap:wrap;gap:6px;align-items:baseline;margin:0 0 6px}.relation-link,.relation-other{padding:3px 7px;border:1px solid #3a444e;border-radius:6px;background:#1b2229;color:#c7d2da;font:12px inherit;cursor:pointer;overflow-wrap:anywhere}.relation-link{color:#9fb4c4}.relation-link:hover,.relation-other:hover{border-color:#66737e;color:#ffffff}.legend{margin-top:28px}.legend-row{display:flex;gap:10px;align-items:center;margin:10px 0;color:#c8d0d6;font-size:13px}.swatch{width:24px;height:3px;border-radius:3px;background:#8d99a3}.swatch.dashed{background:repeating-linear-gradient(90deg,#5f8fc9 0 6px,transparent 6px 10px)}.swatch.hidden{opacity:.25}.legend-note{margin-top:22px;color:#7f8b95;font-size:12px}.warnings{position:absolute;left:18px;bottom:17px;z-index:4;padding:8px 11px;border:1px solid #765f33;border-radius:8px;background:#231f17;color:#d9bd82;font-size:12px;display:none}
#cy{position:absolute;inset:0}.inspector-title{margin:14px 0 8px;font-size:27px;line-height:1.2;letter-spacing:-.02em}.inspector-id{font:11px/1.4 ui-monospace,SFMono-Regular,Consolas,monospace;color:#7f8b95;overflow-wrap:anywhere}.divider{height:1px;background:var(--line);margin:22px 0}.meta{display:grid;grid-template-columns:72px 1fr;gap:9px 10px;margin-bottom:22px}.meta dt{color:#87939d}.meta dd{margin:0;overflow-wrap:anywhere}.body-copy{color:#d2d8dc}.body-copy p{margin:.8em 0}.body-copy h3,.body-copy h4,.body-copy h5,.body-copy h6{margin:1.2em 0 .45em}.body-copy blockquote{margin:1em 0;padding-left:13px;border-left:3px solid #596a77;color:#adb8c0}.body-copy code{padding:2px 5px;border-radius:4px;background:#0e1419;color:#d7e6ef}.body-copy .empty{color:#7f8b95;font-style:italic}.frontmatter{white-space:pre-wrap;overflow-wrap:anywhere;padding:14px;border:1px solid #303943;border-radius:8px;background:#0f151a;color:#aeb8bf;font:12px/1.55 ui-monospace,SFMono-Regular,Consolas,monospace}.empty-state{margin-top:45%;color:#7f8b95;text-align:center}.chip-list{display:flex;flex-wrap:wrap;gap:7px;margin:12px 0}.chip{padding:4px 8px;border:1px solid #4b5963;border-radius:999px;background:#202830;color:#c7d2da;font-size:12px}
@media(max-width:900px){.shell{grid-template-columns:minmax(0,1fr) 290px}.left{position:absolute;left:12px;top:12px;width:220px;border:1px solid var(--line);border-radius:12px;padding:17px;transform:translateX(calc(-100% - 22px));transition:transform .2s}.left.open{transform:none}.title{font-size:21px;margin-bottom:14px}.right{padding:22px 20px}.stage{grid-column:1}.right{grid-column:2}.menu{position:fixed;left:14px;top:14px;z-index:6}.left .menu{position:static}}
@media(max-width:640px){.shell{display:block}.right{position:absolute;z-index:5;right:0;bottom:0;left:0;height:42%;border-left:0;border-top:1px solid var(--line)}.stage{height:58%}.left{z-index:7}}
</style>
__SCRIPT_TAGS__
</head>
<body>
<div class="shell">
  <aside class="panel left" id="left-panel">
    <h1 class="title">__TITLE__</h1>
    <button class="menu" id="menu" aria-label="Toggle legend">☰</button>
    <section class="finder"><label for="node-search">Find by name</label><input class="filter-search" id="node-search" type="search" placeholder="Name, id or type" aria-label="Find artifacts by name"><label class="finder-toggle"><input type="checkbox" id="node-search-highlight" checked> Highlight in graph</label><div class="finder-summary" id="node-search-summary"></div><ul class="finder-results" id="node-search-results"></ul><button type="button" class="finder-clear" id="node-search-clear" hidden>Clear results</button></section>
    <details class="filters" id="filters" open><summary>Filter this view</summary><div class="filter-actions"><button type="button" data-filter-action="all" disabled>All / Reset</button><button type="button" data-filter-action="none" disabled>None</button></div><input class="filter-search" id="filter-search" type="search" placeholder="Search filter types" aria-label="Search filter types" disabled><div class="filter-summary" id="filter-summary"></div><div id="filter-catalogue"></div></details>
    <section class="legend" id="legend"><h2>Relations in view</h2></section>
    <p class="legend-note">Pan by dragging the background. Scroll to zoom. Click a node or edge to inspect its canon file.</p>
  </aside>
  <main class="stage"><div id="cy" role="img" aria-label="Interactive canon graph"></div><div class="warnings" id="warnings"></div><output id="runtime-status" hidden data-state="loading"></output></main>
  <aside class="panel right inspector" id="inspector"><div class="empty-state">Select something in the graph.</div></aside>
</div>
<script type="application/json" id="projection-data">__DATA_JSON__</script>
<script type="application/json" id="artifact-details">__DETAILS_JSON__</script>
<script>
(function(){
  "use strict";
  const data=JSON.parse(document.getElementById("projection-data").textContent);
  const details=JSON.parse(document.getElementById("artifact-details").textContent);
  const inspector=document.getElementById("inspector");
  const runtimeStatus=document.getElementById("runtime-status");
  const fallback={entity:"#8b949c",idea:"#a884c6",relation:"#5f8fc9"};
  const typeLabel=(value)=>String(value||"relation").split("/").pop().replace(/[-_]/g," ").replace(/\b\w/g,(c)=>c.toUpperCase());
  const amountLabel=(amount)=>{if(!amount)return "state";const one=Array.isArray(amount)?amount[0]:amount;if(!one||typeof one!=="object")return String(amount);if(one.of)return String(one.value)+" of "+String(one.of);return [one.value,one.unit].filter((x)=>x!==undefined&&x!==null).join(" ")||"state"};
  let activeProjection=data,artifactTypes=new Set(),relationTypes=new Set(),positionMemory=new Map(),filtersReady=false;
  let searchResults=[],searchActive=false;
  const exactType=(value)=>value||"(untyped)";
  const artifactKey=(kind,type)=>JSON.stringify([kind,exactType(type)]);
  const artifactKeyParts=(key)=>{try{const parts=JSON.parse(key);return Array.isArray(parts)&&parts.length===2?parts:["unknown",key]}catch(error){return ["unknown",key]}};
  function relationModel(projection){
    const relations=new Map();
    const ensure=(id,type)=>{if(!relations.has(id))relations.set(id,{id,type:exactType(type),members:new Set()});return relations.get(id)};
    projection.nodes.filter((node)=>node.kind==="relation").forEach((node)=>ensure(node.id,node.type));
    projection.edges.forEach((edge)=>{const id=edge.id.split("::member:")[0],item=ensure(id,edge.type);if(edge.source!==id)item.members.add(edge.source);if(edge.target!==id)item.members.add(edge.target)});
    projection.nodes.forEach((node)=>(node.chips||[]).forEach((chip)=>{const item=ensure(chip.source,chip.type);item.members.add(node.id)}));
    return relations;
  }
  function filteredProjection(projection){
    const relations=relationModel(projection),base=new Map(projection.nodes.filter((node)=>node.kind!=="relation").map((node)=>[node.id,node]));
    const visibleBase=new Set(Array.from(base.values()).filter((node)=>artifactTypes.has(artifactKey(node.kind,node.type))).map((node)=>node.id));
    // typeAllowed is the relation-type filter alone. valid additionally drops
    // relations whose members are hidden, which is right for drawing an edge
    // and wrong for tracing containment: the chain has to cross the very
    // artifacts the author just hid.
    const typeAllowed=new Set(Array.from(relations.values()).filter((item)=>relationTypes.has(item.type)).map((item)=>item.id));
    const valid=new Set(typeAllowed);
    let changed=true;while(changed){changed=false;relations.forEach((item,id)=>{if(!valid.has(id))return;for(const member of item.members){if((base.has(member)&&!visibleBase.has(member))||(!base.has(member)&&relations.has(member)&&!valid.has(member))){valid.delete(id);changed=true;break}}})}
    const nodes=projection.nodes.filter((node)=>node.kind!=="relation"?visibleBase.has(node.id):valid.has(node.id)).map((node)=>({...node,parent:null,chips:(node.chips||[]).filter((chip)=>valid.has(chip.source))}));
    const nodeIds=new Set(nodes.map((node)=>node.id)),edges=projection.edges.filter((edge)=>valid.has(edge.id.split("::member:")[0])&&nodeIds.has(edge.source)&&nodeIds.has(edge.target));
    // Re-parent across a hidden container, but only along an unbroken run of
    // one relation type. part_of composes — a seat inside a county inside a
    // region really is inside the region — so hiding the county should not
    // orphan the seat. A custom nesting type need not compose: the seat of a
    // county is not the seat of its region, and drawing it inside one would
    // assert something the canon never said. Same type all the way up is the
    // condition that keeps the picture truthful.
    const byId=new Map(nodes.map((node)=>[node.id,node]));
    const chain=new Map();
    // The chain spans hidden artifacts but still obeys the relation-type
    // filter: unticking part_of must remove the nesting, not merely reroute it.
    projection.edges.filter(
      (edge)=>edge.behavior==="nest"&&typeAllowed.has(edge.id.split("::member:")[0])
    ).forEach((edge)=>{
      if(!chain.has(edge.source))chain.set(edge.source,{parent:edge.target,type:edge.type||""});
    });
    nodes.forEach((node)=>{
      let step=chain.get(node.id),guard=0;
      if(!step)return;
      const type=step.type;
      while(step&&guard++<64){
        if(byId.has(step.parent)){node.parent=step.parent;return}
        const next=chain.get(step.parent);
        if(!next||next.type!==type)return;
        step=next;
      }
    });
    return {projection:{...projection,nodes,edges},artifacts:visibleBase.size,relations:valid.size,totalArtifacts:base.size,totalRelations:relations.size};
  }
  function renderFilters(projection){
    activeProjection=projection;const catalogue=document.getElementById("filter-catalogue"),artifactRows=new Map(),relationRows=new Map(),relations=relationModel(projection);
    projection.nodes.filter((node)=>node.kind!=="relation").forEach((node)=>{const key=artifactKey(node.kind,node.type);artifactRows.set(key,(artifactRows.get(key)||0)+1);artifactTypes.add(key)});
    relations.forEach((item)=>{relationRows.set(item.type,(relationRows.get(item.type)||0)+1);relationTypes.add(item.type)});
    catalogue.innerHTML="";const addGroup=(title,rows,kind)=>{const group=document.createElement("section");group.className="filter-group";const heading=document.createElement("h3");heading.textContent=title;group.appendChild(heading);Array.from(rows).sort((a,b)=>a[0].localeCompare(b[0])).forEach(([key,count])=>{const path=kind==="artifact"?artifactKeyParts(key)[1]:key;const row=document.createElement("label");row.className="filter-row";row.dataset.filterText=(path+" "+kind).toLowerCase();const input=document.createElement("input");input.type="checkbox";input.checked=kind==="artifact"?artifactTypes.has(key):relationTypes.has(key);input.disabled=!filtersReady;input.dataset.filterKind=kind;input.dataset.filterKey=key;input.title=path;const text=document.createElement("span");text.textContent=(path==="(untyped)"?"(untyped)":typeLabel(path))+" ";const amount=document.createElement("span");amount.className="filter-count";amount.textContent="("+count+")";text.appendChild(amount);row.append(input,text);group.appendChild(row)});catalogue.appendChild(group)};
    const grouped=new Map();artifactRows.forEach((count,key)=>{const [kind]=artifactKeyParts(key);if(!grouped.has(kind))grouped.set(kind,new Map());grouped.get(kind).set(key,count)});Array.from(grouped).sort((a,b)=>a[0].localeCompare(b[0])).forEach(([kind,rows])=>addGroup("Artifacts · "+kind,rows,"artifact"));addGroup("Relations",relationRows,"relation");updateFilterSummary();
  }
  function updateFilterSummary(){const result=filteredProjection(activeProjection);document.getElementById("filter-summary").textContent=result.artifacts+" of "+result.totalArtifacts+" artifacts · "+result.relations+" of "+result.totalRelations+" relations visible"}
  function clearFilterSearch(){const search=document.getElementById("filter-search");search.value="";document.querySelectorAll(".filter-row").forEach((row)=>row.hidden=false)}
  function clearInspector(){inspector.innerHTML='<div class="empty-state">Select something in the graph.</div>'}
  function setFilterControlsReady(ready){filtersReady=ready;document.querySelectorAll("#filters button,#filters input").forEach((control)=>control.disabled=!ready);document.querySelectorAll(".finder input,.finder button").forEach((control)=>control.disabled=!ready)}
  function rememberNodePositions(){cy.nodes().forEach((node)=>{const position=node.position();if(Number.isFinite(position.x)&&Number.isFinite(position.y))positionMemory.set(node.id(),{x:position.x,y:position.y})})}
  function restoreViewport(viewport){cy.zoom(viewport.zoom);cy.pan(viewport.pan)}
  function resetFilters(projection){artifactTypes=new Set();relationTypes=new Set();clearFilterSearch();const search=document.getElementById("node-search");if(search)window.__WB_CLEAR_SEARCH__();renderFilters(projection)}
  function applyCurrentFilters(){const pan=cy.pan(),viewport={zoom:cy.zoom(),pan:{x:pan.x,y:pan.y}};rememberNodePositions();const result=filteredProjection(activeProjection);window.__WB_DATA__=result.projection;cy.elements().remove();cy.add(elementsFor(result.projection,positionMemory));clearInspector();if(!cy.nodes().length){restoreViewport(viewport);updateFilterSummary();return}const options={name:"preset",animate:false,fit:false,padding:58};try{cy.layout(options).run()}catch(error){console.warn("Filter layout fallback",error)}restoreViewport(viewport);updateFilterSummary();if(window.__WB_APPLY_NODE_SEARCH__)window.__WB_APPLY_NODE_SEARCH__()}
  document.getElementById("filter-catalogue").addEventListener("change",(event)=>{const input=event.target;if(!input.matches("input[data-filter-kind]"))return;const set=input.dataset.filterKind==="artifact"?artifactTypes:relationTypes;if(input.checked)set.add(input.dataset.filterKey);else set.delete(input.dataset.filterKey);applyCurrentFilters()});
  document.querySelectorAll("[data-filter-action]").forEach((button)=>button.addEventListener("click",()=>{const enabled=button.dataset.filterAction==="all";document.querySelectorAll("input[data-filter-kind]").forEach((input)=>{input.checked=enabled;const set=input.dataset.filterKind==="artifact"?artifactTypes:relationTypes;if(enabled)set.add(input.dataset.filterKey);else set.delete(input.dataset.filterKey)});if(enabled)clearFilterSearch();applyCurrentFilters()}));
  document.getElementById("filter-search").addEventListener("input",(event)=>{const query=event.target.value.toLowerCase();document.querySelectorAll(".filter-row").forEach((row)=>row.hidden=!!query&&!row.dataset.filterText.includes(query))});
  // Finding dims rather than removes: positions stay put, so the eye keeps its
  // bearings and a match can be read in the context that explains it. A parent
  // of a match stays lit, otherwise a nested hit would be hidden by its own box.
  //
  // The matched set is the state, not the text in the box. Typing replaces it;
  // emptying the box leaves it alone; the toggle decides whether it is painted.
  // Keeping those separate means clearing the query cannot silently change two
  // things at once, and a kept set can be re-lit without retyping it.
  function runSearch(){
    const cy=window.__WB_CY__;
    if(!cy)return;
    const query=(document.getElementById("node-search").value||"").trim().toLowerCase();
    if(!query){paintSearch();return}
    searchResults=cy.nodes().filter((node)=>{
      const detail=details[node.data("detailId")]||{};
      return [node.data("label"),node.id(),node.data("type"),detail.name].some(
        (value)=>typeof value==="string"&&value.toLowerCase().includes(query)
      );
    }).map((node)=>node.id());
    searchActive=true;
    paintSearch();
  }
  function clearSearch(){
    searchResults=[];searchActive=false;
    document.getElementById("node-search").value="";
    paintSearch();
  }
  function paintSearch(){
    const cy=window.__WB_CY__;
    if(!cy)return;
    const summary=document.getElementById("node-search-summary"),clear=document.getElementById("node-search-clear");
    cy.elements().removeClass("wb-faded wb-found");
    renderSearchResults(searchResults);
    clear.hidden=!searchActive;
    if(!searchActive){summary.textContent="";return}
    summary.textContent=searchResults.length?searchResults.length+(searchResults.length===1?" match":" matches"):"no match";
    if(!document.getElementById("node-search-highlight").checked)return;
    const present=searchResults.map((id)=>cy.getElementById(id)).filter((element)=>element.length);
    if(!present.length){cy.elements().addClass("wb-faded");return}
    const matches=cy.collection(present);
    cy.elements().not(matches.union(matches.ancestors())).addClass("wb-faded");
    matches.addClass("wb-found");
  }
  function applyNodeSearch(){paintSearch()}
  function renderSearchResults(ids){
    const list=document.getElementById("node-search-results");
    list.innerHTML="";
    ids.slice().sort((a,b)=>{
      const left=(details[a]||{}).name||a,right=(details[b]||{}).name||b;
      return String(left).localeCompare(String(right));
    }).forEach((id)=>{
      const detail=details[id]||{},row=document.createElement("li");
      const button=document.createElement("button");
      button.type="button";button.className="finder-hit";button.dataset.goto=id;
      const name=document.createElement("span");name.className="finder-hit-name";name.textContent=detail.name||id;
      const type=document.createElement("span");type.className="finder-hit-type";type.textContent=detail.type?typeLabel(detail.type):(detail.kind||"");
      button.append(name,type);row.appendChild(button);list.appendChild(row);
    });
  }
  window.__WB_APPLY_NODE_SEARCH__=applyNodeSearch;
  window.__WB_CLEAR_SEARCH__=clearSearch;
  document.getElementById("node-search").addEventListener("input",runSearch);
  document.getElementById("node-search-highlight").addEventListener("change",paintSearch);
  document.getElementById("node-search-clear").addEventListener("click",clearSearch);
  resetFilters(data);
  function elementsFor(projection,positions=positionMemory){
    const elements=[];
    projection.nodes.forEach((node)=>{
      const chipText=(node.chips||[]).map((chip)=>typeLabel(chip.type)+": "+amountLabel(chip.amount));
      let label=node.kind==="relation"?typeLabel(node.type):node.label;
      if((node.badges||[]).includes("fiat"))label+="  ◆";
      if(chipText.length)label+="\n"+chipText.map((x)=>"▰ "+x).join("\n");
      const item={data:{id:node.id,detailId:node.id,label:label,kind:node.kind||"unknown",type:node.type||"",shape:node.style.shape,color:node.style.color||fallback[node.kind]||"#8b949c",opacity:node.style.opacity,dormant:(node.badges||[]).includes("dormant")?1:0,practice:(node.badges||[]).includes("practice")?1:0}};
      const position=positions.get(node.id);if(position)item.position=position;
      if(node.parent)item.data.parent=node.parent;
      elements.push(item);
    });
    projection.edges.forEach((edge)=>elements.push({data:{id:edge.id,detailId:edge.id.split("::member:")[0],source:edge.source,target:edge.target,type:edge.type||"",label:edge.id.includes("::member:")?"":typeLabel(edge.type),behavior:edge.behavior,directed:edge.directed?1:0,color:edge.style.color,width:edge.style.width,line:edge.style.line}}));
    return elements;
  }
  const elements=elementsFor(data);

  if(typeof window.cytoscape!=="function"){
    inspector.innerHTML='<h2>Viewer error</h2><p class="body-copy">Cytoscape could not be loaded. Use <code>--vendor</code> for an offline file.</p>';
    window.__WB_VIEWER_READY__=false;
    runtimeStatus.dataset.state="error";
    return;
  }
  // Interaction costs scale with the graph, so the measures against them are
  // spent only where they buy something. textureOnViewport is cheap and always
  // on. Dropping edges while the viewport moves, and while a node is dragged,
  // is what a big nested canon needs and what a small one should never pay:
  // below this many edges everything stays drawn, because there was never a
  // frame-rate problem to fix.
  const BUSY_EDGES=60;
  const busy=data.edges.length>=BUSY_EDGES;
  const cy=window.cytoscape({container:document.getElementById("cy"),elements:elements,layout:{name:"preset"},minZoom:.18,maxZoom:3.5,textureOnViewport:true,hideEdgesOnViewport:busy,motionBlur:false,style:[
    {selector:"node",style:{label:"data(label)",shape:"data(shape)",width:"170px",height:"86px",padding:"10px","background-color":"data(color)","background-opacity":.18,"border-color":"data(color)","border-width":"2px",opacity:"data(opacity)",color:"#f0ede6","font-size":"17px","font-weight":600,"text-wrap":"wrap","text-max-width":"160px","text-valign":"center","text-halign":"center","overlay-opacity":0}},
    {selector:"node[kind = 'relation']",style:{width:"94px",height:"72px","font-size":"13px",padding:"8px","text-max-width":"88px"}},
    {selector:"node[dormant = 1]",style:{"border-style":"dashed"}},
    {selector:"node[practice = 1]",style:{"outline-width":"2px","outline-color":"data(color)","outline-offset":"4px"}},
    {selector:":parent",style:{"background-opacity":.06,"border-style":"dashed",padding:"32px","text-valign":"top","text-margin-y":"-10px"}},
    {selector:"node:selected",style:{"border-width":"4px","overlay-color":"#ffffff","overlay-opacity":.06}},
    {selector:".wb-faded",style:{opacity:.07}},
    {selector:"edge.wb-quiet",style:{visibility:"hidden"}},
    {selector:"edge.wb-hushed",style:{label:""}},
    {selector:"node.wb-found",style:{"border-width":"4px","border-color":"#e8c37a",color:"#ffffff"}},
    {selector:"edge",style:{label:"data(label)",width:"data(width)","line-color":"data(color)","line-style":"data(line)","curve-style":"bezier",color:"data(color)","font-size":"12px","font-weight":600,"text-background-color":"#0d1217","text-background-opacity":.95,"text-background-padding":"4px","text-rotation":"autorotate","overlay-opacity":0}},
    {selector:"edge[directed = 1]",style:{"target-arrow-shape":"triangle","target-arrow-color":"data(color)","target-arrow-fill":"filled","arrow-scale":.9}},
    {selector:"edge[behavior = 'nest']",style:{opacity:0,label:""}},
    {selector:"edge[behavior = 'hide']",style:{display:"none"}},
    {selector:"edge:selected",style:{"overlay-color":"#ffffff","overlay-opacity":.08}}
  ]});
  runtimeStatus.dataset.nodes=String(cy.nodes().length);
  runtimeStatus.dataset.edges=String(cy.edges().length);
  window.__WB_CY__=cy;
  window.__WB_DATA__=data;
  // dagre has no compound-node support: it ranks every node as if the graph
  // were flat, so a nested canon collapses into one very wide row inside
  // stretched parent boxes. See cytoscape.js#844 and cytoscape.js-dagre#14.
  // fcose is built for compound graphs, so we substitute it and say why rather
  // than drawing a picture that misrepresents the world.
  window.__WB_RESOLVE_LAYOUT__=function(requested,projection){
    if(requested!=="dagre")return requested;
    if(!(projection.nodes||[]).some((node)=>node.parent))return requested;
    const note="Laid out with fcose: this view nests artifacts, and dagre cannot lay out nested graphs.";
    if(Array.isArray(projection.warnings)&&!projection.warnings.includes(note))projection.warnings.push(note);
    return "fcose";
  };
  window.__WB_ELEMENTS_FOR__=elementsFor;
  window.__WB_RESET_FILTERS__=resetFilters;
  window.__WB_FILTERED_PROJECTION__=()=>filteredProjection(activeProjection).projection;
  setFilterControlsReady(false);

  const requestedLayout=["fcose","dagre","concentric","preset"].includes(data.view.layout)?data.view.layout:"fcose";
  const layoutName=window.__WB_RESOLVE_LAYOUT__(requestedLayout,data);
  const options={name:layoutName,animate:false,fit:true,padding:58,nodeDimensionsIncludeLabels:true};
  if(layoutName==="fcose")Object.assign(options,{quality:"default",randomize:true,packComponents:false,idealEdgeLength:150,nodeRepulsion:7000});
  if(layoutName==="dagre")Object.assign(options,{rankDir:"TB",rankSep:95,nodeSep:70});
  if(layoutName==="concentric")Object.assign(options,{minNodeSpacing:80});
  const layoutElements=cy.elements().filter((element)=>!element.isEdge()||element.data("behavior")!=="hide");
  function markViewerReady(state){rememberNodePositions();setFilterControlsReady(true);window.__WB_VIEWER_READY__=true;runtimeStatus.dataset.state=state;runtimeStatus.dataset.positions=JSON.stringify(cy.nodes().map((node)=>({id:node.id(),position:node.position(),visible:node.visible()})))}
  try{const layout=layoutElements.layout(options);layout.on("layoutstop",()=>markViewerReady("ready"));layout.run()}catch(error){const fallback=layoutElements.layout({name:"grid",fit:true,padding:50});fallback.on("layoutstop",()=>markViewerReady("fallback"));fallback.run();console.warn("Layout fallback",error)}

  function chipsFor(id){const node=window.__WB_DATA__.nodes.find((item)=>item.id===id);return node?(node.chips||[]):[]}
  // Built from the whole view, not the filtered picture: an artifact's
  // connections are canon, and hiding some behind a filter would quietly
  // misreport what the world says. Entries whose other end is not on screen
  // are still listed, just not navigable.
  function connectionsFor(id){
    const projection=activeProjection,found=new Map();
    const add=(relationId,type,role,otherId)=>{
      const key=relationId+"|"+otherId+"|"+role;
      if(!found.has(key))found.set(key,{relationId,type,role,otherId});
    };
    (projection.edges||[]).forEach((edge)=>{
      const relationId=edge.id.split("::member:")[0],roles=edge.roles||{};
      if(edge.source===id&&edge.target!==id)add(relationId,edge.type,roles.source,edge.target);
      else if(edge.target===id&&edge.source!==id)add(relationId,edge.type,roles.target,edge.source);
    });
    (projection.nodes||[]).forEach((node)=>{
      (node.chips||[]).forEach((chip)=>{if(node.id===id)add(chip.source,chip.type,null,null)});
    });
    return Array.from(found.values());
  }
  function renderConnections(id){
    const items=connectionsFor(id);
    if(!items.length)return null;
    const section=document.createElement("section");
    const heading=document.createElement("h2");heading.textContent="Relations ("+items.length+")";section.appendChild(heading);
    const list=document.createElement("ul");list.className="relation-list";
    items.forEach((item)=>{
      const row=document.createElement("li");
      const relation=document.createElement("button");
      relation.type="button";relation.className="relation-link";
      relation.textContent=typeLabel(item.type)+(item.role?" · as "+item.role:"");
      relation.dataset.goto=item.relationId;
      row.appendChild(relation);
      if(item.otherId){
        const other=document.createElement("button");
        other.type="button";other.className="relation-other";
        const detail=details[item.otherId];
        other.textContent=detail?detail.name:item.otherId;
        other.dataset.goto=item.otherId;
        row.appendChild(other);
      }
      list.appendChild(row);
    });
    section.appendChild(list);
    return section;
  }
  function inspect(id){
    const item=details[id];if(!item)return;
    const chips=chipsFor(id);
    const meta=[["kind",item.kind],["type",item.type||"—"],["status",item.status||"canon"]];
    inspector.innerHTML="";
    const heading=document.createElement("h2");heading.textContent="Canon artifact";inspector.appendChild(heading);
    const title=document.createElement("h3");title.className="inspector-title";title.textContent=item.name;inspector.appendChild(title);
    const artifactId=document.createElement("div");artifactId.className="inspector-id";artifactId.textContent=item.id;inspector.appendChild(artifactId);
    const divider=document.createElement("div");divider.className="divider";inspector.appendChild(divider);
    const dl=document.createElement("dl");dl.className="meta";meta.forEach((pair)=>{const dt=document.createElement("dt");dt.textContent=pair[0];const dd=document.createElement("dd");dd.textContent=pair[1];dl.append(dt,dd)});inspector.appendChild(dl);
    if(chips.length){const holder=document.createElement("div");holder.className="chip-list";chips.forEach((chip)=>{const span=document.createElement("span");span.className="chip";span.textContent=typeLabel(chip.type)+": "+amountLabel(chip.amount);holder.appendChild(span)});inspector.appendChild(holder)}
    const body=document.createElement("div");body.className="body-copy";body.innerHTML=item.body_html;inspector.appendChild(body);
    const connections=renderConnections(id);
    if(connections){const dividerR=document.createElement("div");dividerR.className="divider";inspector.append(dividerR,connections)}
    const divider2=document.createElement("div");divider2.className="divider";inspector.appendChild(divider2);
    const fmTitle=document.createElement("h2");fmTitle.textContent="Frontmatter";inspector.appendChild(fmTitle);
    const pre=document.createElement("pre");pre.className="frontmatter";pre.textContent=JSON.stringify(item.frontmatter,null,2);inspector.appendChild(pre);
  }
  window.__WB_INSPECT__=inspect;
  // One place decides what "go to this artifact" means, so the relation list,
  // the search results and a graph click all behave identically.
  function goTo(id){
    if(!details[id])return;
    const element=cy.getElementById(id);
    if(element.length&&element.visible()){
      cy.elements().unselect();element.select();
      cy.animate({center:{eles:element}},{duration:220});
    }
    inspect(id);
  }
  window.__WB_GO_TO__=goTo;
  inspector.addEventListener("click",(event)=>{
    const button=event.target.closest("[data-goto]");
    if(button)goTo(button.dataset.goto);
  });
  document.getElementById("node-search-results").addEventListener("click",(event)=>{
    const button=event.target.closest("[data-goto]");
    if(button)goTo(button.dataset.goto);
  });
  cy.on("tap","node,edge",(event)=>{cy.elements().unselect();event.target.select();inspect(event.target.data("detailId"))});
  // Dragging a node in a compound graph re-measures every ancestor box and
  // redraws every edge label on each frame; Cytoscape's viewport levers do not
  // cover drags. So for the duration of one, keep only the edges being moved
  // and drop their labels — the author still sees what they are rearranging.
  cy.on("grab","node",(event)=>{
    if(!busy)return;
    const moving=event.target.union(event.target.descendants());
    const touched=moving.connectedEdges();
    cy.edges().not(touched).addClass("wb-quiet");
    touched.addClass("wb-hushed");
  });
  cy.on("free","node",()=>{cy.edges().removeClass("wb-quiet wb-hushed")});
  const first=data.nodes.find((node)=>node.kind!=="relation")||data.nodes[0];if(first){cy.getElementById(first.id).select();inspect(first.id)}

  const behaviorInfo={edge:["solid","edge"],nest:["dashed","containment"],hide:["hidden","hidden"]};
  const behaviors=new Set(data.edges.map((edge)=>edge.behavior));if(data.nodes.some((node)=>node.parent))behaviors.add("nest");
  const legend=document.getElementById("legend");Array.from(behaviors).sort().forEach((behavior)=>{const info=behaviorInfo[behavior]||["solid",behavior];const row=document.createElement("div");row.className="legend-row";const swatch=document.createElement("span");swatch.className="swatch "+info[0];const label=document.createElement("span");label.textContent=info[1];row.append(swatch,label);legend.appendChild(row)});
  if(data.warnings.length){const warning=document.getElementById("warnings");warning.style.display="block";warning.textContent=data.warnings.length+" projection warning"+(data.warnings.length===1?"":"s");warning.title=data.warnings.join("\n")}
  document.getElementById("menu").addEventListener("click",()=>document.getElementById("left-panel").classList.toggle("open"));
})();
</script>
</body>
</html>
'''


MULTI_VIEW_CSS = r'''
.view-picker{display:block;margin:-10px 0 20px}.view-picker span{display:block;margin:0 0 6px;color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.12em}.view-picker select{width:100%;padding:8px 10px;border:1px solid #3a444e;border-radius:7px;background:#11171d;color:var(--text);font:13px/1.3 inherit}.multi-loading #cy{opacity:0}
'''


MULTI_VIEW_SCRIPT = r'''
<script type="application/json" id="multi-view-data">__MULTI_JSON__</script>
<script>
(function(){
  "use strict";
  const bundle=JSON.parse(document.getElementById("multi-view-data").textContent);
  const views=bundle.views,explicit=bundle.explicit_layouts;
  const picker=document.getElementById("view-picker"),cy=window.__WB_CY__;
  const runtimeStatus=document.getElementById("runtime-status");
  const inspector=document.getElementById("inspector");
  const allowedLayouts=new Set(["fcose","dagre","concentric","preset"]);
  let unionPositions=new Map(),currentPositions=new Map(),activeAlgorithm=null;
  let selectedId=cy.nodes(":selected").length?cy.nodes(":selected")[0].id():null;
  document.body.classList.add("multi-loading");

  function positionMap(){return new Map(cy.nodes().map((node)=>[node.id(),{x:node.position("x"),y:node.position("y")}]))}
  function unionProjection(){
    const nodes=new Map(),edges=new Map();
    views.forEach((projection)=>{
      projection.nodes.forEach((node)=>{
        if(!nodes.has(node.id))nodes.set(node.id,node);
        else if(!nodes.get(node.id).parent&&node.parent)nodes.set(node.id,{...nodes.get(node.id),parent:node.parent});
      });
      projection.edges.forEach((edge)=>{if(!edges.has(edge.id))edges.set(edge.id,edge)});
    });
    const ids=new Set(nodes.keys());
    return {view:{name:"Union layout",layout:"fcose",render:"graph"},nodes:Array.from(nodes.values()),edges:Array.from(edges.values()).filter((edge)=>ids.has(edge.source)&&ids.has(edge.target)),warnings:[]};
  }
  function replaceElements(projection,positions){
    cy.elements().remove();
    cy.add(window.__WB_ELEMENTS_FOR__(projection));
    if(positions)cy.nodes().forEach((node)=>{const position=positions.get(node.id());if(position)node.position(position)});
  }
  function optionsFor(name,fixed){
    const options={name,animate:false,fit:true,padding:58,nodeDimensionsIncludeLabels:true};
    if(name==="fcose")Object.assign(options,{quality:"default",randomize:!fixed.length,packComponents:false,idealEdgeLength:150,nodeRepulsion:7000,fixedNodeConstraint:fixed});
    if(name==="dagre")Object.assign(options,{rankDir:"TB",rankSep:95,nodeSep:70});
    if(name==="concentric")Object.assign(options,{minNodeSpacing:80});
    return options;
  }
  function runLayout(name,fixed=[]){
    return new Promise((resolve)=>{
      if(!cy.nodes().length){resolve();return}
      const elements=cy.elements().filter((element)=>!element.isEdge()||element.data("behavior")!=="hide");
      try{
        const layout=elements.layout(optionsFor(name,fixed));
        layout.on("layoutstop",resolve);layout.run();
      }catch(error){
        console.warn("Layout fallback",error);
        const fallback=elements.layout({name:"grid",fit:true,padding:50});
        fallback.on("layoutstop",resolve);fallback.run();
      }
    });
  }
  function clearInspector(){inspector.innerHTML='<div class="empty-state">Select something in the graph.</div>'}
  function renderLegend(projection){
    const behaviorInfo={edge:["solid","edge"],nest:["dashed","containment"],hide:["hidden","hidden"]};
    const behaviors=new Set(projection.edges.map((edge)=>edge.behavior));if(projection.nodes.some((node)=>node.parent))behaviors.add("nest");
    const legend=document.getElementById("legend");legend.innerHTML="<h2>Relations in view</h2>";
    Array.from(behaviors).sort().forEach((behavior)=>{const info=behaviorInfo[behavior]||["solid",behavior];const row=document.createElement("div");row.className="legend-row";const swatch=document.createElement("span");swatch.className="swatch "+info[0];const label=document.createElement("span");label.textContent=info[1];row.append(swatch,label);legend.appendChild(row)});
  }
  function renderWarnings(projection){
    const warning=document.getElementById("warnings");
    warning.style.display=projection.warnings.length?"block":"none";
    warning.textContent=projection.warnings.length+" projection warning"+(projection.warnings.length===1?"":"s");
    warning.title=projection.warnings.join("\n");
  }
  async function activate(index,initial=false){
    if(!initial){const selected=cy.nodes(":selected");selectedId=selected.length?selected[0].id():null}
    const projection=views[index];
    const declared=allowedLayouts.has(projection.view.layout)?projection.view.layout:"fcose";
    const requested=window.__WB_RESOLVE_LAYOUT__(declared,projection);
    const ownLayout=explicit[index];
    let seed=null,fixed=[];
    if(!ownLayout){seed=unionPositions}
    else if(!initial&&requested==="fcose"&&activeAlgorithm==="fcose"){
      seed=currentPositions;
      fixed=projection.nodes.filter((node)=>seed.has(node.id)).map((node)=>({nodeId:node.id,position:seed.get(node.id)}));
    }
    window.__WB_RESET_FILTERS__(projection);
    replaceElements(window.__WB_FILTERED_PROJECTION__(),seed);
    window.__WB_DATA__=projection;
    if(ownLayout)await runLayout(requested,fixed);else await runLayout("preset");
    currentPositions=positionMap();activeAlgorithm=ownLayout?requested:"fcose";
    document.querySelector(".title").textContent=projection.view.name;
    document.title=projection.view.name;
    picker.value=String(index);renderLegend(projection);renderWarnings(projection);
    if(selectedId&&cy.getElementById(selectedId).length){cy.getElementById(selectedId).select();window.__WB_INSPECT__(selectedId)}else{selectedId=null;clearInspector()}
    runtimeStatus.dataset.state="ready";runtimeStatus.dataset.view=String(index);runtimeStatus.dataset.layout=ownLayout?requested:"union";runtimeStatus.dataset.nodes=String(cy.nodes().length);runtimeStatus.dataset.edges=String(cy.edges().length);runtimeStatus.dataset.positions=JSON.stringify(cy.nodes().map((node)=>({id:node.id(),position:node.position(),visible:node.visible()})));
    document.body.classList.remove("multi-loading");
  }
  async function start(){
    if(!window.__WB_VIEWER_READY__){setTimeout(start,20);return}
    const union=unionProjection();replaceElements(union,null);await runLayout("fcose");unionPositions=positionMap();
    await activate(0,true);
    picker.addEventListener("change",()=>activate(Number(picker.value)));
    window.__WB_MULTI_READY__=true;
  }
  start();
})();
</script>
'''


def render_graph(
    projection: Mapping[str, Any],
    canon: Canon,
    *,
    vendor: bool = False,
    vendor_dir: str | Path | None = None,
) -> str:
    """Render projection plus non-contract inspection details to one HTML string."""
    view = projection.get("view")
    if not isinstance(view, dict):
        raise RenderError("projection has no view object")
    raw_title = view.get("name", "Canon View")
    title = str(raw_title)
    assets = Path(vendor_dir) if vendor_dir is not None else Path(__file__).parents[1] / "vendor"
    return (
        HTML_TEMPLATE.replace("__TITLE__", escape(title))
        .replace("__SCRIPT_TAGS__", _script_tags(vendor, assets))
        .replace("__DATA_JSON__", _safe_json(projection))
        .replace("__DETAILS_JSON__", _safe_json(_details(canon)))
    )


def render_graph_document(
    projections: list[Mapping[str, Any]],
    canon: Canon,
    *,
    explicit_layouts: list[bool] | None = None,
    view_paths: list[str] | None = None,
    vendor: bool = False,
    vendor_dir: str | Path | None = None,
) -> str:
    """Render multiple projections into one switchable, self-contained document."""
    if len(projections) < 2:
        raise RenderError("multi-view rendering requires at least two projections")
    if any(not isinstance(projection.get("view"), dict) for projection in projections):
        raise RenderError("every projection must have a view object")
    flags = explicit_layouts if explicit_layouts is not None else [False] * len(projections)
    paths = view_paths if view_paths is not None else [""] * len(projections)
    if len(flags) != len(projections) or len(paths) != len(projections):
        raise RenderError("multi-view metadata must match the projection count")

    document = render_graph(
        projections[0],
        canon,
        vendor=vendor,
        vendor_dir=vendor_dir,
    )
    options = "".join(
        f'<option value="{index}" title="{escape(path, quote=True)}">'
        f'{escape(str(projection["view"].get("name", path or f"View {index + 1}")))}</option>'
        for index, (projection, path) in enumerate(zip(projections, paths))
    )
    picker = (
        '<label class="view-picker"><span>View</span>'
        f'<select id="view-picker">{options}</select></label>'
    )
    bundle = {
        "views": projections,
        "explicit_layouts": flags,
        "paths": paths,
    }
    script = MULTI_VIEW_SCRIPT.replace("__MULTI_JSON__", _safe_json(bundle))
    return (
        document.replace("</style>", MULTI_VIEW_CSS + "\n</style>", 1)
        .replace('</h1>\n    <button class="menu"', f"</h1>\n    {picker}\n    <button class=\"menu\"", 1)
        .replace("</body>", script + "\n</body>", 1)
    )
