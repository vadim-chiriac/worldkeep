# KERNEL.md — Worldbuilding Canon Kernel (v0.17)

> Spec language is English because the project targets a public audience.

> The kernel is deliberately small. Everything interesting must *emerge* from it.

---

## 1. Design principles

1. **Minimal closed kernel, open vocabulary.** The kernel defines four
   `kind`s and a small set of uniform *facets*. All domain concepts are
   user/AI-invented `type`s layered on top. **The kinds are closed for
   everyone — including module authors.** A model with different base kinds
   (say, `qualia`) is a different, possibly better system; it is a fork, not
   an extension. Extensions (§9) may add namespaced facets and lenses, never
   kinds.
2. **Universal addressability.** Every artifact has an ID. Any relation or
   idea may target *any* ID — including relations themselves.
3. **Flat ontology (generalized symmetry).** Persons, groups, tanks, texts,
   gods, materials, institutions: all just entities — potential actants.
   Whether something acts or is acted upon emerges from its relations.
4. **Idea and truth are separate axes** — refined in §5: existence and
   structure are canon-true for every artifact, ideas included; only an
   idea's *content* carries no truth value.
5. **Incompleteness is canon.** Loose ends, bare connections, unexpanded
   networks, and deliberate ambiguity are supported states. Formal
   validation covers base rules and *declared* type constraints only (§11).
   Inconsistencies are pointed out narratively, by the AI, as observations.
6. **Everything is presumed decomposable (§7).** Any artifact may turn out
   to be a network; none is obliged to. The world exists at whatever
   resolution has been written.
7. **The author outranks the rules (§5, `fiat`).** The user may declare
   anything true — against declared constraints, context, history, natural
   law. Tools may warn once; the AI's job is to correlate, not resist.
8. **Graceful degradation.** Unknown types, facets, or extensions are
   rendered/processed generically, never fatally.
9. **Plain files.** One artifact = one Markdown file with YAML frontmatter.
   Human-editable, git-versioned, no database.

---

## 2. Artifact format

```markdown
---
id: <unique-slug>            # required; stable; kebab-case
kind: <kernel kind>          # required; see §3
type: <free/hierarchical>    # optional; open vocabulary, e.g. community/tribe
name: <display name>         # optional (defaults to id)
tags: [..]                   # optional; free strings
# ...uniform facets (§4) and type-specific fields...
---

Free-form Markdown body: description, notes, quotes, images.
The body is narrative surface; the frontmatter is structure.
```

- **ID = relative file path without extension** by convention; explicit
  `id:` is authoritative if present.
- References always use IDs.

---

## 3. Kinds (closed set — for everyone)

| kind | meaning |
|---|---|
| `entity` | anything that *is* — person, group, particle, material, tank, text, place, god, institution. The single base type of being; all finer distinctions are open `type` vocabulary. |
| `idea` | conceptual or propositional content — doctrines, values, theories, concepts. Subjectivity is in being held (`holds`), not in the kind; no holders = dormant concept. |
| `relation` | a connection between artifacts; **always its own file**; participants via `members` (§6). A relation with no `type` is a *bare connection* — see §6. |
| `type` | the definition of an invented category (§8) |

**Kernel-mechanics test.** A distinction earns a kind only if kernel rules
treat it differently. Agent/object fails it. Qualia, for the
curious, passes *out*: a private experience is an idea with exactly one
holder — the kernel already files it.

**`action` failed it, and was retired in v0.17.** It is now the std type
`action`, with `action/practice` beneath it. Nothing in the kernel treated
happening differently: `when` and `where` are open to every artifact, periods
were already entities despite occupying time, and the instance/practice
distinction was delegated to types from the start. Its one mechanical claim —
that `participates` binds a real event — is now made by `role_types` (§11)
instead of by a kind, and its shape and colour by a lens on the type, where a
visual belongs.

**`idea` passes it, decisively, and is the reason four is the floor.** §5
carves out exactly one exception in the whole kernel: an idea's *content*
asserts nothing about the world. That rule cannot be stated about a type
without letting kernel semantics depend on open vocabulary anyone may
redefine — which would invert §1.1. Everything about belief, esotericism and
contested history hangs from it.

---

## 4. Uniform facets (optional, standardized semantics)

Facets are the only frontmatter fields whose meaning is fixed kernel-wide;
all other fields are free and mean something only if a `type` file says so.

| facet | applies to | semantics |
|---|---|---|
| `when` | any | temporal anchor: a string (`"Second Era, mid"`), an object `{start, end, sort}` (`sort`: optional number for ordering), **or the ID of any time-bearing artifact** — a period, but equally an action ("during the fever") or another dated artifact; time composes like everything else. `when` points at the **innermost** applicable anchor; the nesting itself lives in `part_of` chains *between the periods* (child period `part`, parent `whole`) — never in the anchor. Order between periods comes from `precedes` (§6), not from the anchor. **Avoid the bare string `"now"`** — point at the world's present period (§9). Vagueness is otherwise legal. |
| `where` | any | spatial anchor: ID(s) of place entities. Composes natively: a place `part_of` a district `part_of` a city — location inherits up the chain. |
| `valence` | mainly relations/ideas | `positive` \| `negative` \| `neutral` \| `ambivalent` — sign/flavor |
| `weight` | relations, members | intensity, `0.0–1.0`, dimensionless. On the relation: overall intensity. On a member entry: that participant's degree of involvement. |
| `members` | relations | the participants. A list where each entry is either a plain ID (participant, no role) or an object `{id, role?, weight?}`. `role` is a free string; std and custom types declare expected roles (§8). One relation is one addressable statement, not necessarily one edge: use one multi-member relation only when its facets and provenance apply to every member; split independently timed, statused, sourced, described, or addressable links. **Direction is expressed by role asymmetry**, aggregation by grouping on roles. |
| `status` | any | `canon` \| `draft` \| `deprecated` — workflow, not world-truth |
| `amount` | any (commonly relations, actions, ideas) | magnitude with units: one `{value, unit, per?, of?}` object **or a list of them**. `value` a number or `{min, max}`. A price attaches to the thing priced: a toll `action/practice` carries `amount: {value: 2, unit: silver, per: wagon}`; a price list is a list — `[{value: 3, unit: copper, per: head}, {value: 6, unit: copper, per: cart}]`. **Proportions:** with `of:` (free string or ID naming the basis), `value` is a ratio and `unit` is omitted — "a tenth of every melt" is `{value: 0.1, of: "melt yield", per: melt}`. Compare only within identical `unit`+`per` (or `of`+`per`). Aggregable over inclusion chains by lenses. |
| `fiat` | any | `true` marks an authorial decree: this stands *as written*, even against declared type constraints, established context, history, or natural law. The validator reports conflicts as notices, never errors; the AI correlates instead of resisting. |

**Modeling rule — anything that changes is not a field.** Entity frontmatter
is for stable identity only; mutable properties are relations with `when`
(and `amount` where numeric) — a **state** (§6) when no second party is
involved, an ordinary relation when one is.

---

## 5. Truth model

**Existence and structure are canon for every artifact — ideas included.**
If an idea artifact exists, then it is narrator-true that the idea itself
exists in the world; that whoever `holds` it holds it; that it is about
whatever a relation connects it to. Facets and relations of an idea are as
canon as anyone else's.

**The single exception: an idea's *content*.** The proposition itself —
carried by `name` and the body, or, for complex ideas, expressed as a whole
network of **idea** parts and the relations among them (§7) — asserts nothing
about the world. "The Three stole divinity" existing as an idea is true; the
theft is not thereby true, or false, or even necessarily truth-apt.

**What a false idea refers to is an idea, not an entity.** Writing an entity
artifact *is* the claim that the thing is in the world, so there is no way to
write one that does not exist, and none is needed. In a world without gods, the
god is an `idea`: a pantheon composes as idea parts (§7), believers `holds` it,
and real entities point at it — a temple that exists can be `dedicated_to` a
god that does not. What is lost by not writing the entity is exactly the
existence claim, which is the thing you did not want to make.

**Narrator prose** (bodies of non-idea artifacts) is world-true by fiat, as
before.

**Authorial decree (`fiat: true`).** The generality of the model makes some
simple things hard to state formally — and the author should never have to
fight their own tooling. Any statement, structured or prose, may be marked
`fiat`: it then stands even against declared constraints, accumulated
context, history, or the world's own natural laws. Tools may warn once
(notices, not errors); it is the AI's job to correlate the decree with the
rest of the canon — narratively, per §1.5 — not to enforce consistency.

**Stating a rule of the world.** A holderless idea is a dormant concept —
its content *still* asserts nothing; it is not a way to state truth. To
declare a law of the world, write a **narrator entity** (conventionally
`type: law`): its body is narrator prose, world-true as written, and being
typed, laws are findable by any lens. Like everything, decomposable —
corollaries and exceptions `part_of` the law when written.

```markdown
---
id: entities/marches-debt-law
kind: entity
type: law
name: "Only persons can be owed a debt"
---
In the Marches, debt binds persons only. Things, places, mountains — none
can be owed. Not opinion, not doctrine: how the world works, like weather.
```

**Contested vs fiat.** Contested is for parties *in the world* disagreeing
(two ideas, two `holds`); `fiat` is for the *author* overriding a rule —
declared constraints, accumulated context, the world's own laws. "It's
impossible and it happens anyway — don't smooth that out" is fiat, not a
dispute to be staffed with holders. A world-level decree is simply a law
entity carrying `fiat: true`; decrees thus have a home without touching
`world.yaml`. **Fiat is not contagious**: a law does not need `fiat` — its
body is already narrator-true; `fiat` marks what stands *against* the
rules, including against a law. Marking both the rule and its breach
defeats §11's downgrade, which exists for the breach alone.

**Esotericism, worked.** Secrecy about beliefs is ideas targeting
holds-relations — universal addressability (§1.2) doing its job. "Only the
Harbormistress knows what the Rope believes about the bell":

```markdown
---
id: relations/rope-holds-bell-doctrine    # the secret itself — canon
kind: relation
type: holds
members:
  - { id: entities/the-rope, role: holder, weight: 0.8 }
  - { id: ideas/bell-rings-for-the-drowned, role: held }
---
```
```markdown
---
id: ideas/rope-bell-secret                # knowledge OF the secret
kind: idea
name: "The Rope holds a doctrine about the bell"
---
```
```markdown
---
id: relations/secret-about-holding        # the idea targets the relation
kind: relation
members: [ideas/rope-bell-secret, relations/rope-holds-bell-doctrine]
---
```
```markdown
---
id: relations/harbormistress-knows        # who knows = who holds
kind: relation
type: holds
members:
  - { id: entities/harbormistress, role: holder }
  - { id: ideas/rope-bell-secret, role: held }
---
```

Who knows a fact = who `holds` the idea about it. Publicity and secrecy are
therefore never a facet value — they are the shape of the holds-network
around an idea. (A `weight` of `restricted` is a category error; see §4.)

Dormant ideas (the unread book), disputed existence (a god living only in
ideas and `holds`), and open mysteries (never write the narrator artifact)
remain supported.

---

## 6. Relations

Relations are always separate files; participants live in `members` (§4).

**A bare connection is not a type — it is a fact.** "Association" is what
the *existence* of a relation means when nothing more has been said. A
relation with no `type`:

- renders in any viewer as a connection (a line) — that alone is signal;
- means whatever the user and AI decide when they get to it: a marker for
  the future, something deducible from the connected artifacts' data (an
  object linked to many small parts probably doesn't need a label to be
  understood), or a mistake to delete;
- is a supported permanent state, per §1.5.

**A one-member relation is a state.** A relation with a single member is
legal and means: *a fact about that member*, carried by the relation's own
facets — `when`, `amount`, `valence`. This is how a changing scalar
property is written (the §4 modeling rule forbids fields): population then
and population now are two `state` relations on the same entity, each with
its `when` and `amount`.

**Name the property in the type.** A bare `state` says only "something
about X was so." Which property is the type's job: `state/population`,
`state/size`, `state/temper`. **Series identity is (subject, type)** — that
is what lets a lens chart 600-then-280 as one line and leave the boat count
out of it. The property type file declares the unit and anything else
formal:

```markdown
---
id: types/state/population
kind: type
name: Population
applies_to_kind: relation
constraints:
  roles_required: [subject]
---
Headcount of the subject at a time. `amount.unit: persons`.
```

A state with no property type is legal (incompleteness is canon) — it just
charts alone.

There is therefore no `associated` std type; the std library starts with
actually-meaningful vocabulary:

| std type | of | meaning |
|---|---|---|
| `part_of` | relation | **inclusion**: one `whole` with one or more `part` members (binary remains valid): parts of an object, provinces in a state, a doctrine in a religion. `whole` is unique; `part` is repeatable. Child `part_of/membership` covers agents belonging to communities or movements. The zoom edge (§7). |
| `subordinate_to` | relation | **hierarchy/order**: army command, feudal regimes, church ranks. Distinct from inclusion — a general is not a *part* of the colonel. Roles: `superior`, `subordinate`. |
| `holds` | relation | an entity holds an idea. Roles: `holder`, `held`. `weight` = conviction. |
| `opposes` | relation | generic negativity/opposition. Specialize (`opposes/moral`) or leave bare. **Always authored, never inferred.** |
| `participates` | relation | binds participants to one **action**. The unique `action` member must be typed `action` or a descendant (`role_types`, §11); all other roles are free vocabulary — `performer`, `target`, `instrument`, `witness`, … Agency is a role, not a type: whether something acts or is acted upon is stated per-member, per flat ontology. Several participants bundle into one file; `weight` per member = degree of involvement. |
| `action` / `action/practice` | entity | something that happens: an episodic occurrence / a recurrent pattern. Carries the lens that used to be a hard-coded shape. |
| `period` | entity | a span of time as an entity — era, reign, season, siege. `when` anchors point at periods (innermost applicable); periods nest via `part_of` (child period `part`, parent `whole`). |
| `state` | relation | a one-member relation: a fact about its member, carried by `when`/`amount`/`valence`. Role: `subject`. The home of every mutable scalar property — populations, sizes, prices-of-the-day. Specialize by property (`state/population`); series identity is (subject, type). |
| `precedes` | relation | temporal order between two artifacts that occupy time — periods, actions, states. Roles: `earlier`, `later`. Ordering is then **derived** (topological sort over the `precedes` graph); numeric `when.sort` remains an optional override for worlds with a real calendar. Authors say "after the fever, before the flood"; nobody should have to invent 1700. |

For example, provinces stated with the same time, status, source, and
description belong in one addressable inclusion statement:

```markdown
---
id: relations/provinces-of-the-river-kingdom
kind: relation
type: part_of
members:
  - { id: entities/northmarch, role: part }
  - { id: entities/reedlands, role: part }
  - { id: entities/river-kingdom, role: whole }
---
```

If one province joined later or needs its own provenance, it is a different
statement and therefore a separate relation file.

Close-bond types beyond these (alliances, friendships, patronage) are the
open vocabulary's job — see Appendix C for `alliance` as a user type. A
base viewer with no std library shows only connections; one with it shows
groups, chains of command, convictions, conflicts; one with user lenses
shows alliances. Meaning degrades gracefully, layer by layer.

Ideas need no relations; contradictory ideas may coexist unmarked. Belief
systems: a religion is an entity, doctrines link via `part_of`, adhesion is
`part_of/membership` — to the system or directly to an idea.

---

## 7. Networks & zoom (fractal composition)

**Everything is presumed decomposable.** ANT-informed: every artifact is
already treated as expressible as a composite, or as a member of one — so
compositeness is never marked, only *expressed*, through `part_of`
relations when and if parts get written.

- **Inner network of X** := artifacts related to X via `part_of`
  (transitively), plus all relations among them. May be empty forever.
- **Zoom** is a viewer/AI operation, not stored structure: any node — or
  relation, since relations have IDs and things can be `part_of` them —
  expands into whatever inner network exists. The alliance edge contains a
  treaty, a signing, obligations, and the envoys' friendship, when someone
  writes them.
- **Aggregates of aggregates**: `part_of` chains without depth limit.
- **Composable properties.** Composition is not only for things:
  *place* composes (`where` up a places chain), *time* composes (`when`
  pointing at period artifacts that nest), *magnitude* composes (lenses
  may aggregate `amount` over inclusion, within identical units), *content*
  composes (a complex idea expressed as a network of parts), *categories*
  compose (type hierarchies). One mechanism, many properties.

  **Content composition, worked.** When the author says a story can't be
  compressed — "five turns, every one load-bearing" — the idea's body does
  NOT get five paragraphs. Each turn becomes its own idea, `part_of` the
  whole; the parts may have their own relations, holders, and disputes:

  ```markdown
  ---
  id: ideas/first-debtor-story
  kind: idea
  name: "The story of the First Debtor"
  ---
  Told in five turns. Zoom in; the turns are the content.
  ```
  ```markdown
  ---
  id: relations/turn-one-in-story
  kind: relation
  type: part_of
  members:
    - { id: ideas/first-debtor-turn-one, role: part }
    - { id: ideas/first-debtor-story, role: whole }
  ---
  ```

  A sect can then hold turn three and reject turn five — schisms over a
  single verse fall out of the kernel, which is the point.
- **Lazy elaboration.** Complexity exists only at the level needed, wanted,
  or possible in context. Practical consequence for AI tooling: zoom levels
  are natural context-window management.

---

## 8. Type definitions

Users and AI freely invent types (never kinds); each SHOULD get a small
`kind: type` file.

```markdown
---
id: types/holds
kind: type
name: Holds
applies_to_kind: relation
constraints:                 # DECLARED formal constraints — enforced (unless fiat)
  roles_required: [holder, held]
  role_kinds: { held: [idea] }
---
An entity holds an idea. Weight on the holder member = strength of conviction.
```

- `type` values are hierarchical via parent paths (`community/tribe` implies
  `community`); types nest without limit.
- **Children inherit their parent's `constraints:` and may tighten them,
  never loosen.** If you need looser, you want a sibling, not a child.
  It follows that **a type counts as defined when any ancestor on its path
  has a file**: `community/guild/ferrymen` is legal and inherits with only
  `types/community.md` present. Write the leaf file when the leaf adds
  something — a tighter constraint, a distinct lens, a definition worth
  reading. Otherwise the path itself is the classification.
  (Multiple inheritance does not exist and is not missed: a second category
  is nearly always relations wearing a category costume — a guild that is
  also a cult is a guild that `holds` a creed. `tags` cover soft
  membership.)
- **Two tiers of type rules.** `constraints:` (including required roles,
  `roles_unique` role multiplicity, and role restrictions by kind
  (`role_kinds`) or by type path (`role_types`, which a descendant type
  satisfies)) are formal, enforced as errors — but only
  because the type *declared* them, and never against `fiat`. Everything
  else (`applies_to`, `suggested_fields`) is soft: warnings, never blocks.
  `roles_unique` is an optional list of distinct role names, each allowed at
  most once in an instance; it is deliberately declared only where the type
  needs that semantic (the std library uses it for `part_of.whole` and
  `participates.action`).
- A type file may carry a **`lens:` block** — how a viewer should display
  instances. It is structured data, never a name pointing at a module and
  never prose: a viewer reads keys, and a sentence tells it nothing.
  Without a lens, instances render generically (§1.8).

```markdown
---
id: types/rules
kind: type
name: Rules
applies_to_kind: relation
constraints:
  roles_required: [ruler, domain]
lens:
  as: edge          # edge | nest | chip | hide
  direction: [ruler, domain] # optional visual source, target roles
  width: weight     # a number, or the facet to scale by
  color: "#8a4"     # a hex colour, or: valence
  line: solid       # solid | dashed | dotted
  shape: hexagon    # nodes only
  label: name       # name | none | any facet name
---
Governance: one entity holds ruling authority over a place or group.
```

The load-bearing key is **`as`** — a *behavior*, not a style. `edge` draws
a line; `nest` draws the whole containing its parts; `chip` renders on a
member instead of between members; `hide` keeps the artifact in the data
and out of the picture. Everything else is decoration.

Every behavior in that list is one a renderer can honour by itself. Whether
a hierarchy reads top-to-bottom follows from the layout a **view** chooses,
not from the type: a type says what a relation *is*, a view says how that
reads on a page. A behavior that only some renderers can express is not a
behavior — it draws nothing and reports nothing in the ones that cannot,
which is why `rank` and `group` are unavailable behaviors.

Prose about how a type *should* look belongs in the body, where humans
read it. Only the block above reaches a viewer.

`direction` is optional presentation metadata for relation lenses. Its two
distinct, non-empty role names are `[source, target]`: a directed binary edge
points from the member carrying the first role to the member carrying the
second. A reified relation routes source-role members into the relation node
and from that node to target-role members. Omit it for an undirected relation.
**The order of `constraints.roles_required` never defines direction**; that
list only states roles that must occur. Invalid or unresolved direction
degrades to an undirected visible relation with a warning.

The built-in viewer directions are `subordinate_to` (`subordinate` →
`superior`), `holds` (`holder` → `held`), `part_of` and
`part_of/membership` (`part` → `whole`), and `precedes` (`earlier` →
`later`). `opposes`, `participates`, and bare relations are undirected.
In custom views `part_of` is shown through unarrowed `nest` parentage; the
part-to-whole arrow appears only when the relation is explicitly rendered,
including the built-in Everything audit projection.

---

## 9. World manifest & extensions

```yaml
kernel_version: "0.16"
name: "Vvardenfell-adjacent test world"
calendar: "Eras; sort key = era*1000 + year"
facets: [when, where, valence, weight, members, status, amount, fiat]
std_types: [part_of, subordinate_to, holds, opposes, participates, action, action/practice, period, state, precedes]
present: entities/the-long-thaw   # the world's "now" — a period entity
extensions: []               # namespaced FACETS and lenses only — never kinds
```

- Kinds are not listed because they are not configurable.
- **`present`** names the period artifact the world currently sits in. It is
  the referent of "now": states and relations anchored there move with the
  world when the present advances, instead of a bare `"now"` string whose
  meaning silently rots. Optional — a world with no present is a world
  outside time, which is legal.
- Extensions are namespaced, declared, versioned; unrecognized → §1.8.
- **Promotion rule** for facets unchanged: ≥2 lenses needing identical
  semantics (`fiat` qualifies: validator + AI correlation).

---

## 10. Repository layout (convention, not law)

```
my-world/
  world.yaml
  entities/
  ideas/
  actions/
  relations/
  types/
```

Folders are for humans; `kind` is authoritative. `actions/` is named after a
type rather than a kind — a convenience kept when `action` stopped being a
kind (v0.17), not a category.

---

## 11. Validator (declared form only, fiat-aware)

Checks base rules and declared constraints, never meaning. It will never
flag contradictory ideas, implausible timelines, unexplained bare
connections, unexpanded networks, or incomplete worlds.

Errors: duplicate IDs; dangling references; missing `kind`; relation with
empty `members`; violation of declared `constraints:` (including
`roles_unique`, inherited down the
type path, tightened by children) — *unless the artifact carries
`fiat: true`*, which downgrades constraint violations to notices.
Warnings: type with no file anywhere on its path; `applies_to_kind`
mismatch; declared `suggested_fields` absent; `weight` outside 0–1 or
non-numeric; `amount` missing `unit` without `of`; bare `"now"` as a `when`
value. Ordering is derived (§6 `precedes`), so a missing `sort` is never
itself a warning.

---

## 12. Viewer contract

The viewer core needs *only* the kernel: list artifacts, render bodies,
draw connections (typed or bare), order by `when` (sort keys or period
chains), color by `valence`, scale by `weight` (relation- and
member-level), group by `role`, and **zoom** any artifact into its inner
network, relations included. Lenses — std, type-provided (§8), or custom —
add richer renderings.

Ambiguity renders as legitimate state, never defect: drafts, dormant ideas,
bare connections, empty networks, fiat decrees (marked as such, discreetly)
all display as what they are. A "loose ends" lens may *list*; nothing may
nag, block, or demand resolution.

---

## Appendix A — Worked example: a religious schism (11 artifacts)

**`entities/tribunal-temple.md`**
```markdown
---
id: entities/tribunal-temple
kind: entity
type: community/church
name: Tribunal Temple
where: [entities/city-of-vvard]
---
State religion. Publicly serene, privately anxious about its own origins.
Its orders and offices exist; almost none are written. (§7: presumed
decomposable — no marker needed.)
```

**`entities/dissident-priests.md`**
```markdown
---
id: entities/dissident-priests
kind: entity
type: community/heretical-order
name: Dissident Priests
---
Splinter scholars. Small, literate, dangerous to doctrine rather than to bodies.
```

**`entities/apographa.md`**
```markdown
---
id: entities/apographa
kind: entity
type: text
name: The Apographa
where: [entities/hidden-archive]
---
The hidden writings. Restricted; most who guard them have never read them.
```

**`ideas/gods-earned-divinity.md`**
```markdown
---
id: ideas/gods-earned-divinity
kind: idea
name: "The Three earned divinity through virtue"
valence: positive
---
Apotheosis as reward. (§5: that this doctrine exists is canon; whether the
Three earned anything is not asserted.)
```

**`ideas/gods-stole-divinity.md`**
```markdown
---
id: ideas/gods-stole-divinity
kind: idea
name: "The Three stole divinity with a forbidden tool"
---
The esoteric counter-history.
```

**`relations/stole-in-apographa.md`**
```markdown
---
id: relations/stole-in-apographa
kind: relation
type: part_of
members:
  - { id: ideas/gods-stole-divinity, role: part }
  - { id: entities/apographa, role: whole }
---
Written down long before anyone now living held it. Dormant until the
Dissidents read it.
```

**`relations/temple-holds-earned.md`**
```markdown
---
id: relations/temple-holds-earned
kind: relation
type: holds
members:
  - { id: entities/tribunal-temple, role: holder, weight: 0.95 }
  - { id: ideas/gods-earned-divinity, role: held }
---
Doctrine since the First Council. Non-negotiable in public.
```

**`relations/dissidents-hold-stole.md`**
```markdown
---
id: relations/dissidents-hold-stole
kind: relation
type: holds
members:
  - { id: entities/dissident-priests, role: holder, weight: 0.7 }
  - { id: ideas/gods-stole-divinity, role: held }
---
Held with scholarly caution rather than fervor — which annoys the Temple more.
```

**`relations/doctrine-opposition.md`**
```markdown
---
id: relations/doctrine-opposition
kind: relation
type: opposes/doctrinal
members: [ideas/gods-earned-divinity, ideas/gods-stole-divinity]
valence: negative
weight: 0.85
---
The load-bearing theological dispute. A network in itself when zoomed:
councils, anathemas, book burnings — mostly unwritten.
```

**`actions/the-red-moment.md`**
```markdown
---
id: actions/the-red-moment
kind: entity
type: action
name: The Red Moment
when: { start: "1E 700", sort: 1700 }
where: [entities/red-mountain]
---
Something happened here; the canon deliberately does not say what. Both
doctrines connect to it by bare relations; the meaning of the connection is
exactly what they fight about.
```

**`relations/vela-joins-dissidents.md`**
```markdown
---
id: relations/vela-joins-dissidents
kind: relation
type: part_of/membership
members:
  - { id: entities/vela, role: part, weight: 0.4 }
  - { id: entities/dissident-priests, role: whole }
when: { start: "2E 410", sort: 2410 }
valence: ambivalent
---
She still lights candles at the Temple on feast days. Nobody asks.
```

---

## Appendix B — Domain stress tests

| Domain | Modeling | What emerges for free |
|---|---|---|
| **Economics** | resources/currencies/guilds as entities; `trades_with`, `owns`, `taxes` as user relation types with `amount`; a price attaches to the thing priced (a toll `action/practice` with `amount: {value: 2, unit: silver, per: wagon}`); a trade route is a relation whose inner network holds ports, caravans, tariffs | routes on maps; flows per `unit`+`per`; `amount` aggregation up inclusion chains |
| **Art** | artworks as entities; creation as `action`; `depicts` targeting any ID, including a faction's idea about history | propaganda as structure |
| **Magic** | hard laws as narrator entities (`type: law`) or `fiat` decrees; schools holding rival law-ideas at varying weight; casting as `action/practice` | hard/soft spectrum from §5; describes, never enforces |
| **Materials** | entities with `found_in`, `component_of` (a `part_of` child), `used_for`; disputed properties as ideas with rival holds | alchemists disagreeing natively |
| **Disease** | diseases as entities; infections as `afflicts` relations with `when`+`where`+`amount`; outbreaks as `action`; rites as `action/practice`; theories as ideas | epidemics as spreading patterns across lenses |

---

## Appendix C — Zoom walkthrough: the alliance

1. **Resolution 0** — two entities and one relation:
   ```markdown
   ---
   id: relations/redoran-indoril-alliance
   kind: relation
   type: alliance            # user-invented type, with its own type file & lens
   members:
     - { id: entities/house-redoran, weight: 0.6 }
     - { id: entities/house-indoril, weight: 0.35 }
   valence: positive
   ---
   ```
   Per-member weights native to one file: the lukewarm ally visible at a
   glance, no auxiliary artifacts. A perfectly complete world state.
2. **Zoom the edge**: a treaty, its signing, the mutual-defense idea, and
   the envoys' friendship, each `part_of` the alliance relation — when and
   if written.
3. **Zoom a node**: House Redoran as what political entities actually are —
   councils, garrisons, doctrines held at varying internal weights,
   factions opposing each other quietly. Aggregates of aggregates.
4. At every resolution the world is valid, viewable, and true — and a base
   viewer without the `alliance` type file still shows two houses and one
   positive, asymmetric bond. Meaning degrades gracefully; it never breaks.
