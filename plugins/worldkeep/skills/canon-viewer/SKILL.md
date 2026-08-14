---
name: canon-viewer
description: >-
  Turn a worldbuilding canon folder (one containing world.yaml) into a
  rendered picture — a graph you can open in a browser. Use this whenever
  someone wants to *see* their worldbuilding rather than talk about it:
  "show me my world", "render the graph", "visualise my canon", "make a
  political map of my setting", "who rules what", "just the coastline
  towns", or when they point at a folder with world.yaml and ask what's in
  it. Do not use it for capturing or extending canon — adding entities,
  ideas, actions, or relations is the worldbuilding-scribe's job, not this
  skill's.
---

# Canon viewer

All `assets/` and `scripts/` paths in this skill are relative to the directory
containing this `SKILL.md`.

You turn a sentence into a picture. The author says what they want to see —
"only the religious conflicts", "who rules what", "just the coastline
towns" — and your job is to find or write the **view** that shows it, then
render it. Running `view.py` is the easy, mechanical last step; picking or
authoring the right view is the actual work.

**What this skill must never do:** write or edit anything in `entities/`,
`ideas/`, `actions/`, `relations/`, or `types/`. Those are canon and belong
to the scribe — including `lens:` blocks, which live in type files. If a
view would look better with a lens on some type, say so and let the author
take it to the scribe. The only files this skill creates are `views/*.yaml`,
reusable `view-modules/*.yaml`, and — only when explicitly asked — an
adjacent `views/<stem>.view.lock.yaml`.

## Start with one command

```
scripts/wb session <path> --task view
```

`wb` is the agent-facing entrypoint; run it through the same bundled launcher
as everything else here. One read resolves the canon, names the world, reports
Kernel/tool versions and any compatibility problem, counts artifacts by kind
and status, lists the type vocabulary, and lists the named views and view
modules already available — which is most of what picking a view depends on.
Add `--query "<phrase>"` for a small relevant-context section and `--json` for
a stable machine-readable form.

Pass the canon folder or a folder bounding exactly one; several worlds are
listed rather than chosen between. It is read-only.

Then use `wb` for the work itself:

```
& scripts/run-python.ps1 wb.py view <canon> --all-views --vendor -o <out>.html
& scripts/run-python.ps1 wb.py view <canon> --everything --vendor -o <out>.html
& scripts/run-python.ps1 wb.py view <canon> --view views/<name>.yaml --vendor -o <out>.html
& scripts/run-python.ps1 wb.py view <canon> --list-views
& scripts/run-python.ps1 wb.py validate <canon> --view views/<name>.yaml
& scripts/run-python.ps1 wb.py explain <canon> --view views/<name>.yaml --artifact entities/<id>
& scripts/run-python.ps1 wb.py context <canon> --query "<name>"
```

These wrap the viewer below without changing any of its behaviour, including
the built-in `Everything` contract. The lower-level `view.py` invocations
remain valid and unchanged if you need them.

## Which folder, which view

Find the canon folder the same way the scribe would: a folder containing
`world.yaml`. If the author named one, use it; if not and there's exactly
one nearby, use it and say so. `wb session` does this resolution for you and
reports what it chose.

**Default to every view.** "Show me my world" and anything like it renders
`--all-views`: built-in Everything plus every view saved under `views/` —
the defaults that shipped with the world and any custom ones the author has
saved since. One document, all tabs, no choosing on the author's behalf.

Render a **single** view only when the author expressly asks for one, when a
new view is being previewed before it is saved, or when the request obviously
names one ("just the canon", "who's in what group"). If it isn't clear, render
all of them and say which one answers the question.

The three defaults are deliberately few:

- **Everything** — built in, always exists, selected with `--everything`. It
  needs no `views/` folder or copied recipe and is uncustomized: it ignores
  view/type-file lenses, styles, emphasis, and direction, and its filters are
  temporary to the browser session. Do not save filters into it.
- **Canon only** — the same world with drafts dropped.
- **Groups** — membership and command over the *default* group vocabulary
  only (`part_of/membership`, `subordinate_to`, `participates`, `part_of`).
  Say this out loud when it looks emptier than the author expects: a world
  whose grouping lives in custom relation types will not appear here, and the
  fix is a new named view, not widening this one.

Then check `views/` beside `world.yaml` for durable interpretations:

- **No `views/` folder** — render `--everything`; create a named view only
  after the author approves a durable custom interpretation.
- **Views exist** — render `--all-views` by default; run `--list-views` first
  only when you need to name what's there or pick one deliberately.
- **Nothing existing fits** — write a new `views/<name>.yaml`. This is the
  main path, not a fallback: most interesting requests ("just the coastline
  towns", "who rules what") don't match a pre-made view.

## Rendering

Keep runtime discovery invisible. The YAML dependency is bundled. On Windows
invoke the viewer through `scripts/run-python.ps1`; on macOS/Linux use
`sh scripts/run-python.sh`. Do not mention Python, launchers, dependencies, or
setup while either bundled route remains available. Only surface the
launcher's single blocker after it has exhausted every candidate.

```
& scripts/run-python.ps1 view.py <canon> --all-views --vendor --output <out>.html   # default
& scripts/run-python.ps1 view.py <canon> --everything --vendor --output <out>.html
& scripts/run-python.ps1 view.py <canon> --view views/<name>.yaml --vendor --output <out>.html
& scripts/run-python.ps1 view.py <canon> --list-views
& scripts/run-python.ps1 view.py <canon> --json   # inspect the projection, no render
& scripts/run-python.ps1 view.py <canon> --validate-view views/<name>.yaml
& scripts/run-python.ps1 view.py <canon> --explain-view views/<name>.yaml --artifact entities/<id>
```

`--validate-view` and `--explain-view` never generate HTML, so they are cheap
to run while iterating. Both accept `--json` for a stable machine-readable
form. `--validate-view` exits `1` when the view is invalid.

Read the style-rule match counts in validation too. A literal type such as
`place` intentionally does not style `place/settlement`; validation notices
selected descendants that a literal rule misses and suggests a separate
`place/*` rule, without widening anything automatically.

Always pass `--vendor` for skill-driven renders — the HTML should still
open with no network in ten years. Use `--json` to diagnose a missing node
without a browser: it dumps the exact node/edge set that would render.

## Writing a view file

A view is YAML in `<canon>/views/`. **It is not a canon artifact** — no
`kind`, never validated by `validate.py`. Compact schema:

```yaml
name: "Political map — who rules what"
render: graph
select:
  kinds: [entity, relation]        # optional; default: everything
  types: [place/*, community/*]    # glob on the type path
  status: [canon, draft]           # default: canon + draft
  where_under: entities/the-realm  # optional: place-chain filter
  connected_to_kinds: [idea]       # optional: keep these kinds even isolated
  connected_to_types: [person, person/*] # optional: typed anchors plus direct neighbours
edges:
  include: [subordinate_to, part_of/membership]
  exclude: []
layout: dagre                      # dagre | fcose | concentric | preset
emphasis:
  color_by: valence
  size_by: weight
```

Unspecified keys take sane defaults: everything selected, all relation
types included, `fcose` layout. Start from the closest file in
`views-library/` — `canon-only.yaml` or `groups.yaml` — and narrow
`select`/`edges` rather than writing one from nothing.

Use ordinary `select.types` for a category view. Use
`connected_to_types` when the request is anchors plus their direct related
artifacts: people and affiliations, polities and what they control, or texts
and ideas they discuss. Make `select.types` broad enough to admit anchors and
possible neighbours, use `edges.include` to name the relation meanings, then
let the typed anchors prune unrelated eligible artifacts. The field accepts the
same exact paths/globs as `types`; use both `person` and `person/*` when both
are wanted. It is one hop only and does not justify changing canon, tags, or
types just to force a viewer result. Save the outcome as an ordinary durable
view and explain its selection in plain language.

Every rendered view has a local **Filter this view** panel with exact types
used in that projection. It is presentation-only and resets on a named-view
switch. During the viewer session, filtering preserves known node positions
and the current pan/zoom viewport; restored nodes return to their prior
locations. Hiding an intermediate container keeps what was inside it nested:
the contents re-attach to the nearest visible container, but only along an
unbroken run of one relation type, because a custom nesting type need not
compose the way `part_of` does. Every view also has **Find by name**, which
dims all but the matches and lists them; the match set survives an empty query,
and a toggle controls whether it is painted on the graph. Use `Everything` plus its filters as the independent audit tool; a
custom view is a saved interpretation, not a claim to contain all relevant
artifacts. If a request adds any durable selection, style, emphasis, layout,
or lens behavior, preview a differently named custom view, explain it, and
ask for approval before saving it. Never create `views/everything.yaml` (or
`.yml`) or name a view `Everything` in any casing: that reserved built-in
cannot be customized. Migrate an old such recipe to a descriptive name (for
example `Styled world overview`) and retain its named-view lens behavior.

The inspector groups each connection into one relation card, preserving the
canon member order and roles; every relation card opens even when its relation
is represented as an edge, chip, or hidden structural rule. **Focus relation** temporarily draws only that
relation and its participants; **Focus neighborhood** draws an artifact, its
direct relations, and their participants. Both are one-hop browser-only aids:
they honour the active view and filters, never reveal excluded canon, and clear
from the right-hand inspector or on a view switch. The collapsible legend
describes the final styles actually on screen; never treat it as a statement of
canon meaning or provenance. Everything labels standard state relation nodes
with their structured value or amount without applying any custom lens.

## Composing reusable modules

When a request keeps reappearing — "the same people set again", "our faction
colours" — lift that one concern into a **view module** and compose it. A
module is a flat, typed YAML file directly under `<canon>/view-modules/`.
Modules never import each other and never reach outside that folder.

**Classify the request before writing anything.** Almost every viewer request
is a mix of four independent concerns, and each belongs to a different module
kind:

| the author is asking about | concern | module `kind` | payload |
|---|---|---|---|
| *which artifacts* are on the page | selection | `selection` | `select:` |
| *which relationships* are drawn | relation policy | `relation` | `edges:` |
| what things *look like* | style | `style` | `rules:` |
| how a relation is *structured* — nested, chipped, directed | lens | `lens` | `overlays:` |

Say the classification out loud before composing. "Only guild members, in
faction colours, with leadership nested" is three concerns, not one request,
and it composes as three modules.

```yaml
# view-modules/people.yaml
schema: wb.view-module/v1
id: people
version: 1
kind: selection
select:
  kinds: [entity, relation]
  types: [person, person/*]
```

A named view then composes them by id:

```yaml
name: "People — affiliations and leadership"
compose:
  selection:
    any_of: [people, organizations]   # union
    all_of: [active-subjects]         # intersect the union
    exclude: [private-notes]          # subtract; nothing resurrects these
  relations:
    include: [affiliations, leadership]
    exclude: [superseded-links]
  styles: [faction-colors]            # applied in this order
  lenses: [organization-containment]
select:                               # optional: narrows only, never widens
  status: [canon]
```

Rules worth stating to the author because they surprise people:

- **Exclusion always wins.** A view-local `select` or `edges.include` can only
  narrow a composed result; it can never bring back something a module
  excluded. The compiler warns when you try.
- **Selection and relation policy are separate.** A selection module scoped to
  entities does not suppress the relation modules you composed.
- **Naming a relation module is what widens the picture.** With no explicit
  include, the relation set is just a default and you get the *induced
  subgraph* — the relations whose endpoints you already selected, and nothing
  else. So `any_of: [people]` alone draws people and the links among them, not
  every organization and place they touch. Add `relations: include: [...]`
  (or a view-local `edges.include`) when you do want the relationship to pull
  its far endpoint onto the page; those endpoints are reported as endpoint
  completions, not as things the selection chose. A style-only composition
  narrows nothing, so it still shows the whole graph.
- **Styles settle presentation last; lenses own structure.** `as` and
  `direction` may only appear in a `lens` module or the view's own `lenses:`.
- **Two lens modules that disagree on `as` or `direction` are an error**, not a
  silent winner. Resolve it with a view-local `lenses:` rule naming that exact
  relation type — a `*` wildcard deliberately does not count. Until it is
  resolved, the view still renders, but through a loud `UNVALIDATED FALLBACK`
  warning, and it cannot be locked.

### Before you save anything

Compose and preview first, then validate, then ask. In order:

1. Classify the request into the four concerns and say so.
2. Compile and preview a named view — never touch `Everything`.
3. Run `--validate-view`. Fix errors; do not weaken the recipe to dodge them.
4. Run `--explain-view --artifact <id>` for anything that surprised the author
   — a missing node, an unexpected colour, a relation that vanished. The trace
   names the module or local rule responsible for each decision.
5. **Ask before saving.** Durable view files, reusable modules, and lock files
   are all things the author has to live with. Save only what they approved,
   and report where each piece came from.

A lock (`--write-lock`) records the modules, view, and type-lens inputs behind
a successful validation. It is written only on request and only after a clean
result. Later, a changed module, view, relevant type lens, or schema marks it
stale and names what moved; ordinary canon edits do not.

### A style-only request is still a new view

If the author only wants recoloring — "make the polities blue" — that is a
**style module plus a differently named custom view over the whole world**,
for example `Everything — faction colours`. It is never a change to built-in
`Everything`, which ignores every style, lens, and emphasis by design. Offer
the named view; say plainly that the audit view stays neutral on purpose.

## The lens vocabulary

A relation's `lens.as` (set in its **type file**, not here) declares a
*behavior*, not a style — know these before writing a view that depends on
one:

| behavior | what it draws |
|---|---|
| `edge` | a line between the two members (default) |
| `nest` | one container member as a compound node holding one or more contained members |
| `chip` | rendered on the member rather than between members (states) |
| `hide` | present in the projection, never drawn |

State chips show the property from their type and either its qualitative
`value` (for example `Exploration: unexplored`) or numeric `amount`. Ranges
remain numeric state data; they render as a readable lower bound, upper bound,
or interval.

**A nest reads its role names from the same `direction` an edge would.** The
pair is `[contained, container]`, which is why the standard `part_of` lens
declares `["part", "whole"]`. A world that nests by its own vocabulary declares
both keys together in the type file — `as: nest` with
`direction: [seat, territory]` puts seats inside territories. With no
`direction`, nesting means `part` and `whole`, as it always did.

Two limits worth stating to an author before they ask:

- **Only the canon may declare containment.** A lens module may still override
  `as: nest` for some other relation, but it does not get to reinterpret that
  relation's role names as inside/outside — the declared pair counts only when
  the type file itself says `as: nest`. Otherwise the shape of the graph would
  depend on who drew it.
- **Naming a direction is not the same as meaning containment.** `seat_of`
  says "is the capital of", which is not "is inside". If the author wants the
  geography drawn, that is usually a second `part_of` relation, not a nesting
  lens on the first. Say so, and let them choose.

`part_of/membership` renders as an ordinary edge. Earlier versions used a
layout-dependent `group` behavior; KERNEL v0.13 removed it because the same
canon could look materially different across renderers.

**`dagre` and nesting are mutually exclusive.** dagre has no compound-node
support: it ranks every node as if the graph were flat, so a nested canon
collapses into one very wide row inside stretched parent boxes. The viewer
substitutes `fcose` and says so in the warnings rather than drawing that. If a
view nests anything, choose `fcose` yourself and spare the author the notice.

Hierarchy is not in that list, and deliberately so. Whether a superior
reads as sitting *above* a subordinate comes from the view's `layout` — a
`dagre` view ranks top-to-bottom, `fcose` has no vertical axis to rank
along. If an author wants a chain of command to read as a tree, change the
view's layout; there is no type-level behavior for it. (`rank` was that
behavior until KERNEL v0.13, and drew nothing outside dagre.)

For an asymmetric relation, use an explicit relation lens declaration such
as `direction: [subordinate, superior]`. The two role names mean visual
source then target; the viewer follows them even if `members` are authored in
the opposite order and draws one target arrowhead. Do not infer direction
from `constraints.roles_required`: its order is not semantic. Omit
`direction` for an undirected relation; invalid or unresolved declarations
warn and safely render as ordinary lines.

These lens rules apply to named views only; built-in Everything ignores them.
Everything still applies standard directions: `subordinate_to` is
`subordinate` to `superior`, and explicitly rendered `part_of` and
`part_of/membership` are `part` to `whole`. In a named view, ordinary
`part_of` stays unarrowed nesting.
If the picture the author wants needs a behavior a type doesn't have yet,
that's a lens change — tell them, don't add it yourself.

## Reading the output honestly

- **Warnings on stderr are usually the world's, not the viewer's.** An
  undefined type degrades to a kind default and warns; that's the canon
  missing a type file, not a bug here.
- **An empty graph almost always means `select` filtered everything out** —
  check `types`/`kinds`/`status` before assuming the canon is empty.
- Report warnings verbatim once; don't paraphrase or drop them.

## What this skill is not for

Modeling questions — what a type should be, whether a relation needs a
`lens:` block, what facets mean — are the scribe's and `KERNEL.md`'s
territory, not restated here.
