# Views

A view is a saved answer to "show me this". It is a small YAML file beside your
world, so a question you asked once is askable again by name — and so a picture
you liked is a thing you own rather than a thing you have to reconstruct.

Most of the time you never write one: you ask the agent for what you want and
it writes the file. This document is for when you want to know what it wrote,
or write one yourself.

---

## `Everything`, and why it ignores you

Every canon has one view you did not write and cannot edit. `Everything` shows
every artifact with `status: canon` or `draft`, drawn in neutral viewer-owned
styling, and it **deliberately ignores every `select`, `edges`, `emphasis`,
`lenses`, `styles` and `compose` block in your world.**

That is the point of it. Every other view is an argument — a set of choices
about what matters. `Everything` is the instrument you check the argument
against: when a named view looks wrong, the first question is whether the
artifact is missing from the canon or merely missing from the view, and only a
projection that obeys nothing can answer it.

It shows drafts too, which no named view has to.

---

## A minimal view

```yaml
name: "The bell dispute"
render: graph
select:
  kinds: [entity, idea, relation]
  status: [canon]
edges:
  include: [part_of, part_of/membership, holds, opposes, participates]
layout: fcose
emphasis:
  size_by: weight
```

That is a real view, from [`Examples/lower-fen`](../Examples/lower-fen). It
selects entities, ideas and relations; draws five relation types; scales edge
width by `weight`, so conviction has a thickness.

Save it as `views/the-bell-dispute.yaml` and it appears in the view picker.

---

## `select:` — which artifacts

| key | value | meaning |
|---|---|---|
| `kinds` | list | `entity`, `idea`, `relation`, `type`. Exact match, no globs. |
| `types` | list | type paths, **globs allowed** — `place/*`. `<untyped>` matches artifacts with no type. |
| `status` | list | defaults to `[canon, draft]` |
| `tags` | list | keeps artifacts carrying at least one of these tags |
| `where_under` | one id | keeps only what is inside that artifact, down the `part_of` chain |
| `when_range` | `{from, to}` | keeps artifacts whose `when.sort` falls in range, endpoints included |
| `connected_to_kinds` | list | **anchor**: keep these, plus whatever an included relation ties to them |
| `connected_to_types` | list | the same, by type path; globs allowed |

The two `connected_to_*` keys are anchors rather than filters. They answer "the
guilds, and whoever deals with them" — a question a plain filter cannot express,
because you do not know the names of the neighbours in advance.

## `edges:` — which relations

| key | value |
|---|---|
| `include` | relation type paths, globs allowed |
| `exclude` | the same; **exclusion always wins** |

## `layout:` and `render:`

`layout` is one of `fcose`, `dagre`, `concentric`, `preset`; anything else is
reported and falls back to `fcose`. `render` is `graph`.

**`dagre` cannot lay out a view that nests.** dagre has no compound-node
support, so a nested canon collapses into one very wide row. The viewer
substitutes `fcose` and says so. If your view nests anything — anything with a
`part_of` drawn as containment — choose `fcose` yourself.

## `emphasis:`

| key | value | effect |
|---|---|---|
| `color_by` | `valence` or `#rrggbb` | colours nodes; an explicit lens colour still wins |
| `size_by` | `weight` | scales width by the `weight` facet |

---

## Checking a view before you trust it

```
wb validate <world> --view views/the-bell-dispute.yaml
```

```
view: The bell dispute (views/the-bell-dispute.yaml)
result: VALID
projected: 16 node(s), 14 edge(s)
fingerprint: 620b24fe80797355…
lock: absent
```

It compiles and projects the view without rendering, so you learn that a view
is broken in a second rather than by squinting at a picture. A broken one says
what is wrong and exits non-zero:

```
view: Broken view with missing selection module (views/broken-missing-module.yaml)
result: INVALID
lock: absent

errors (1):
  [compose.invalid] compose.selection.any_of[2]: no module with id
  'nonexistent_module_xyz' in view-modules/ (known ids: active-subjects,
  affiliations, base-palette, containment, faction-palette, ...)
```

Warnings do not make a view invalid — they tell you the view is doing something
you might not have meant:

```
warnings (1):
  [view.unknown-layout] views/typo.yaml: unknown layout 'dagr'; using fcose
  (known: concentric, dagre, fcose, preset)
```

---

## Modules: when the same concern keeps coming back

Write enough views and you will write the same five lines repeatedly — the same
cast of people, the same faction colours. A **view module** lifts one of those
into a file of its own, in `view-modules/` beside your world.

There are four kinds, and the split is the point: **which artifacts**, **which
relationships**, **what things look like**, and **how a relation is
structured** are four independent questions, so they are four independent
files. A palette does not know what it is colouring.

| kind | payload key | answers |
|---|---|---|
| `selection` | `select:` | which artifacts |
| `relation` | `edges:` | which relationships |
| `style` | `rules:` | colour, shape, label, line, width |
| `lens` | `overlays:` | `as`, `direction` — structure |

Each module declares a schema, an id and a version:

```yaml
schema: wb.view-module/v1
id: base-palette
version: 1
kind: style
rules:
  - match: {kind: entity, type: person}
    set: {color: "#7a8ba6", shape: ellipse}
  - match: {kind: entity, type: community/*}
    set: {color: "#8d9c86"}
```

A `match:` takes `kind`, `type`, or both; `type` accepts globs. A `set:` takes
`color`, `label`, `line`, `shape`, `width` for a style, and additionally `as`,
`direction` and `collapse_default` for a lens.

### Composing them

```yaml
name: "Composed overview — people, guilds, and places"
compose:
  selection:
    any_of: [people, organizations, places]
    all_of: [active-subjects]
    exclude: [retired-figures]
  relations:
    include: [leadership, affiliations, containment]
  styles: [base-palette, faction-palette]
  lenses: [nest-containment]
```

Read it as set arithmetic: the union of `any_of`, narrowed by `all_of`, minus
`exclude`. Styles and lenses apply in the order listed, so a later module
overrides an earlier one — which is how `faction-palette` recolours what
`base-palette` painted.

**Every override is reported.** Silence would let a palette quietly lose a
fight it never knew it was in:

```
[style.overlap] entities/merchants-guild.md: 'color' set to '#c9a227' by module
'faction-palette' styles[2], overriding '#8d9c86' from module 'base-palette'
styles[2]
```

Structural conflicts are stricter than cosmetic ones. Two lenses disagreeing
about `as` is not a matter of order: containment is a claim about the world.
The compiler resolves it only if exactly one rule matches the artifact's exact
type, and says which won; otherwise it drops the property and reports an error.

---

## Why a view drew what it drew

The question that matters when a picture surprises you is not "what is in this
view" but "why is *that* in it". `--explain-view` answers for one artifact:

```
wb explain <world> --view views/composed-overview.yaml \
    --artifact entities/merchants-guild
```

```
artifact: entities/merchants-guild
view: Composed overview — people, guilds, and places
kind/type: entity / community/polity

selection:
  semantically selected: yes
  shown in the projection: yes
  selection outcome: selected
  matched any_of module(s): notable-figures, organizations
  matched all_of module(s): active-subjects

style:
  color = '#c9a227'  <- module 'faction-palette' styles[2]

projection:
  drawn as node: yes
  nest parent: entities/free-port

diagnostics:
  [warning] entities/merchants-guild.md: 'color' set to '#c9a227' by module
  'faction-palette' styles[2], overriding '#8d9c86' from module 'base-palette'
  styles[2]
```

Every line names the module and the rule index that caused it. This is the
difference between a composed view and a pile of overrides you are afraid to
touch.

---

## Locks: knowing when a view has drifted

A composed view depends on things that can move underneath it — the modules it
names, the type vocabulary it matches against, the kernel version. A lock
records what it depended on when you last blessed it.

```
wb validate <world> --view views/composed-overview.yaml --write-lock
```

This writes `views/composed-overview.view.lock.yaml`, recording a content hash
for the view and for every module, the kernel version, and a fingerprint of the
whole compilation. Afterwards, validation tells you whether the view still
compiles to what it did:

```
result: VALID
fingerprint: e44e9ddaad8f5302…
lock: stale
  changed: module 'people'
```

Note that it stayed **valid**. A stale lock is not an error — it is the
difference between "this broke" and "this changed, and here is what changed".
The view still works; you are simply being told that `people` is not the module
it was, so if the picture looks different, that is why.

---

## Rendering

```
wb view <world> --view views/the-bell-dispute.yaml -o out.html
wb view <world> --all-views -o out.html
wb view <world> --everything -o out.html
```

`--all-views` puts every view in one document with a picker, which is usually
what you want: switching views keeps positions where they were, so you are
comparing pictures rather than re-reading them.

Add `--vendor` to inline the browser assets. The result opens with no network,
now and in ten years, which is the only durability claim this project makes
about anything it renders.

---

## In the rendered page

**Find by name** searches names, ids and types, dims everything else, and lists
the matches. The match set outlives the query text, and a toggle controls
whether it is painted on the graph — so you can keep a list of results while
looking at an unhighlighted picture.

**Filter this view** switches whole types on and off. Hiding a container keeps
what was inside it nested, re-attaching the contents to the nearest visible
container — but only along an unbroken run of one relation type, because a
custom nesting type need not compose the way `part_of` does.

**Clicking anything** opens its canon file: frontmatter, body, and the
relations it takes part in, each one clickable. That list comes from the whole
view rather than the filtered picture, because an artifact's connections are
canon and a filter should not be able to misreport them.

---

## Where to go next

| you want to | read |
|---|---|
| the modelling behind what you are drawing | [OVERVIEW.md](OVERVIEW.md) |
| the normative rules for lenses and types | `Specification/KERNEL.md` §8 |
| a worked composed view | `Testing/fixtures/composition-acceptance` |
| a small readable world | [`Examples/lower-fen`](../Examples/lower-fen) |
