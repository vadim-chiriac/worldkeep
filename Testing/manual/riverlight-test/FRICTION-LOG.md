# Riverlight live plugin test — observations

## Step 0 — new-world startup

- The first run stopped before writing because the installed KERNEL was v0.15
  while the seed declared v0.11. This exposed stale canonical and duplicate
  source copies.
- The repair established one canonical KERNEL/SCRIBE source and one canonical
  seed source, with generated distribution and installed copies produced by the
  build.

## Step 1 — geography and polities (drafts)

- The scribe wrote 18 drafts in three bundles. Bundle counts closed exactly
  (5 + 9 + 4), validation was clean, and the new `controls` vocabulary was
  surfaced for approval.
- `controls` earned a type file: it is used twice and its lens declares an
  explicit `controller -> domain` direction.
- “The Free Port of Veyra” became two entities: the place `Veyra` and the
  community/polity `The Free Port of Veyra`, located at Veyra. This is useful
  modelling, but the bundle did not surface that interpretive split.
- The claim that no stated power controls the entire basin was preserved as
  narrator prose on the basin rather than forced into a negative relation.
- Default projection results while all new artifacts are drafts:
  - `Everything`: 12 nodes, 5 edges; the only informative default view.
  - `Places`: 12 nodes, 0 edges. It excludes custom `controls` and bare
    geography relations; `where` anchors do not draw connections.
  - `People, groups, and command`: 12 nodes, 0 edges. It excludes custom
    `controls` and the bare clans-to-moot relation.
  - `Beliefs`: empty, expected before religions or ideas exist.
  - `Canon only`: empty, expected before approval.
- The apply payload `artifacts.json` remains in the canon root after a
  successful write. It is ignored by validation/view loading but is avoidable
  workspace clutter.
- After `ok all`, all 18 drafts were promoted in one apply call. Validation
  remained clean, no draft status lines remained, and `Canon only` projected
  the same 12 nodes and 5 edges as `Everything`.

## Design questions parked for later

- `subordinate_to` currently directs `superior -> subordinate`, although its
  predicate name naturally reads `subordinate -> superior`.
- Generic default views cannot anticipate open relation vocabulary. Test
  whether lightweight request-specific views are sufficient, and whether
  `where` needs a visual projection rather than only selection semantics.

## Step 2 — religions and practices (drafts)

- The scribe wrote 15 drafts in four bundles. Bundle counts closed exactly
  (8 + 4 + 1 + 2), validation was clean, and no unnecessary new type was
  introduced.
- The summary correctly surfaced two interpretive choices that affect the
  model: `Lume` became a place, and the River Covenant priesthood became a
  community distinct from the Covenant itself.
- The Covenant and Lantern teachings became ideas with typed `holds`
  relations. Priesthood membership uses `part_of/membership`; Orven ancestor
  rites became a `practice` connected through `participates`. Tolerance,
  distrust, regional strength, and popularity remained bare relations rather
  than forcing approximate types.
- Default projection results with step 2 still in draft:
  - `Beliefs`: 4 nodes, 2 `holds` edges. Coherent but deliberately omits the
    bare tolerance/distrust relations and ancestor practice.
  - `Everything`: 19 nodes, 13 edges. Complete and currently the only view
    that preserves the whole sketch.
  - `People, groups, and command`: 17 nodes, 2 edges. It includes nearly all
    places but hides control, tolerance, distrust, regional popularity, and
    doctrine holdings, so the picture is sparse and weakly focused.
  - `Places`: 16 nodes, 1 edge. The only edge is priesthood membership because
    `part_of/*` also matches `part_of/membership`; actual geography, `where`
    anchors, bare spatial relations, and custom `controls` are absent.
  - `Canon only`: remains the approved step-1 graph (12 nodes, 5 edges), as
    expected.
- A second apply payload, `religion-artifacts.json`, remains in the canon root,
  confirming that successful batches accumulate avoidable JSON work files.
- After approval, all 15 religion/practice drafts were promoted in one call.
  Validation remained clean, zero drafts remained, and `Canon only` advanced
  to the complete 19-node, 13-edge graph.

## Step 3 — important people (drafts)

- The scribe wrote 12 drafts in four bundles. Bundle counts closed exactly
  (4 + 3 + 2 + 3), validation was clean, and the summary explicitly kept
  titles on persons rather than inventing office entities.
- `leads` earned a type file because Queen Mara and Tomas both use it and its
  lens declares `leader -> body`. Religious affiliation uses ordinary
  `part_of/membership`; Old Eren's convening and Nalia's criticism remain bare
  relations rather than being forced into hierarchy or opposition.
- Default projection results with the people still in draft:
  - `Everything`: 23 nodes, 20 edges. It preserves all seven new person
    relations, including custom `leads` and both bare connections.
  - `People, groups, and command`: 21 nodes, 5 edges. It shows the three new
    person-to-religion memberships plus priesthood membership and the Orven
    practice, but hides both `leads` edges, Eren convening the moot, and
    Nalia's criticism. It also retains many unrelated place nodes.
  - `Places`: 20 nodes, 4 edges, all of them religious memberships. The
    misleading wildcard problem grows as persons are added.
  - `Beliefs`: unchanged at 4 nodes and 2 doctrine-holding edges; religious
    membership is deliberately not treated as holding every doctrine.
  - `Canon only`: remains the approved step-2 graph (19 nodes, 13 edges).
- A person belonging to both a family and a cult would project as two ordinary
  membership arrows in `Everything` and `People, groups, and command`. This is
  a reasonable basic default; the group names/types, not different edge
  behavior, carry the distinction. Custom relations remain the harder default
  view problem.
- A third payload, `people-artifacts.json`, remains in the canon root.
- After approval, all 12 person drafts were promoted in one call. Validation
  remained clean, zero drafts remained, and `Canon only` advanced to the full
  23-node, 20-edge sketch.

## Step 4 — request-specific political geography view

- The viewer correctly determined that no default view fit and created a new
  `dagre` view without editing canon.
- The focused projection has 16 nodes, 2 edges, and no warnings. Both control
  statements are present and correctly directed.
- The result only partially satisfies the request: selecting `place` and
  `community` necessarily includes the River Covenant, its priesthood, and the
  Lantern Way because polities, religions, priesthoods, clans, and the moot
  were all captured at the root `community` type.
- The current view schema cannot select explicit artifact IDs. With coarse
  root types, it cannot request only the Crown, Free Port, Orven clans, and
  relevant places. Request-specific views therefore do not by themselves
  compensate for restrained classification.
- This exposes a scribe/viewer coupling: hierarchical paths such as
  `community/polity`, `community/religion`, and `community/priesthood` could
  remain open vocabulary without leaf type files, while still enabling useful
  filtering. The scribe currently prefers the root type and loses that
  distinction.
- The render launcher rejected a direct `-o` argument as ambiguous; passing
  viewer arguments through its named `-ScriptArgs` parameter succeeded. The
  runtime stayed invisible in the user-facing response, but the documented
  canonical command remains unreliable on PowerShell.

## Step 5 — hierarchical community classification

- Seven approved entities were refined without adding type files: political
  bodies use `community/polity` paths, religions use `community/religion`,
  with separate `community/priesthood` and `community/assembly` categories.
  All inherit from the existing `community` definition.
- Narrowing the political view to `community/polity` and descendants reduced
  it from 16 to 12 nodes while retaining the same 2 control edges and all
  three polities. Religious and assembly communities no longer leak into the
  picture.
- Classification therefore solves category filtering with little ceremony.
  It does not solve connectivity: the Orven clans and most places remain
  isolated because `where` anchors are not projected as visible links.

## Visual acceptance

- The refined political-geography view was accepted: hierarchical community
  types removed irrelevant nodes and made it acceptably focused. Invisible
  `where` connectivity remains a limitation, but is not a blocker for this
  view.

## Design conclusion

- Default views should be fallbacks and examples, not constraints on canon
  modelling. `Everything` should faithfully show general entities, groups,
  directed relations, containment, and overlapping memberships. Agents and
  authors should create durable, named views tailored to the world and save
  them under `views/` until they are edited.

## People view acceptance

- The saved People — affiliations and leadership view was accepted: typed
  membership and `leads` relations composed into a readable durable view with
  no warnings. Old Eren's isolation shows that untyped relations are not
  precisely reusable in focused views; meaningful custom types are warranted
  when that specificity is later needed.

## Overlapping membership acceptance

- Visual confirmation: Tomas has separate Membership arrows to the Lantern
  Way and Veyra Merchants' Guild, plus a distinct Leads arrow to the Free
  Port. `Everything` is semantically correct but already hard to track at 24
  nodes and 21 edges, supporting its role as a general inspection/debug view
  rather than the main navigation view.
- The saved people view did not adapt to the new `community/guild` because it
  enumerates group type families. Durable semantic views may need
  relation-driven one-hop expansion rather than only explicit type families.
