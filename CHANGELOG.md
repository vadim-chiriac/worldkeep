# Changelog

All notable project changes are recorded here. Add new work under `Unreleased`;
do not rewrite released history.

## [Unreleased]

### Added

- Added a public privacy policy that distinguishes Worldkeep's local storage
  from AI-host processing, optional viewer network assets, and GitHub support.
- Added concise public terms covering open-source licensing, user-controlled
  content, AI-output review, third-party hosts, availability, and support.
- Added the Worldkeep identity mark and transparent marketplace-ready icon
  sizes, and displayed the mark in the project README.

### Fixed

- Simplified Claude installation around direct upload of the complete
  `plugin.zip`, and documented that individual `.skill` archives are internal
  or advanced artifacts rather than separate end-user installs.
- Disabled pytest's cache provider in the build pipeline and made publication
  ignore declared transient directories, so permission-sensitive test caches
  cannot block the next public-clone sync.
- Made both skills' opening `wb session` example a runnable Windows command
  through the bundled launcher, and stopped recommending the viewer's `-o`
  alias through `run-python.ps1`, which PowerShell rejects as an ambiguous
  common parameter; `--output` is now used throughout.

## [0.3.0] - 2026-08-15

### Added

- Added an illustrated viewer guide covering navigation, search, temporary
  filters, relation cards, one-hop focus, the generated legend, Everything,
  and saved views; expanded the README onboarding to make semantic correction
  and iterative custom-view refinement explicit, linked the guide prominently
  from the start path and view reference, and refreshed the roadmap to
  distinguish the shipped visual legend from future rule provenance.

- `wb capture` now emits a non-blocking notice when an entity or idea created
  in the current batch is not a member of any relation, helping an agent catch
  accidentally disconnected facts before asking for approval without making
  standalone canon invalid.

- Added relation-driven pruning for the default Groups view, so it shows only
  members of the selected group relation families and keeps unrelated artifacts
  out of the graph.

- Refreshed `Examples/lower-fen` against the current specifications with 31
  approved world artifacts, a qualitative inundation state, shared
  multi-member containment, weighted beliefs, and a richer `The bell dispute`
  view, now shown by the current screenshot in the project README.
- `wb capture` now accepts an approval-batch envelope that verifies every
  artifact belongs to exactly one semantic bundle before writing, then reports
  computed structural counts, relation shapes, new type files, and
  reclassifications after a successful capture.
- View validation now reports deterministic match counts for every style rule
  and non-failing notices for unused rules or literal ancestor selectors that
  miss selected descendant types, without changing selector semantics.
- The viewer now groups inspector relations into readable member-and-role cards,
  supports one-hop temporary relation or neighborhood focus, and generates a
  legend from the styles currently shown after filters or focus.

### Changed

- Relation member order no longer invites accidental pairwise interpretation:
  the Kernel and Scribe now require correspondence-sensitive claims to remain
  atomic, permit higher-order relations to group those claims semantically,
  and warn when a directed relation repeats both endpoint roles.

- Everything now labels standard state relation nodes with their qualitative or
  numeric value; relation cards remain inspectable regardless of graph
  representation. Focus status and Clear now stay beside the focused artifact,
  the generated legend is collapsed until requested, and the desktop burger
  icon is gone while small screens retain a labelled Controls button.
- Tightened the first-release documentation into one newcomer path: install,
  create a real folder, approve a proposal, open the generated HTML, then move
  into the reference guides. The roadmap now distinguishes shipped 0.2.0 work
  from future work, and the examples page states exactly which demonstrations
  exist instead of implying a broader gallery.
- Unified the public marketplace identity as `worldkeep` across Claude and
  ChatGPT/Codex. Installation now uses the public GitHub marketplace directly,
  distinguishes repository distribution from OpenAI's reviewed universal
  directory, and gives users host-specific install, update and uninstall
  instructions without asking them to run the maintainer build pipeline.

### Fixed

- Qualitative one-member states now carry a structured top-level `value`, while
  numeric states keep `amount`. The viewer renders those values as chips and
  formats numeric ranges instead of exposing JavaScript's `[object Object]`.
  The Kernel, Scribe, seed world, and skill guidance now distinguish the two
  forms and retain one property series such as `state/exploration`.
- Public guides that name the current format version now track KERNEL v0.19 and
  SCRIBE v0.13, including the seed-manifest facet list.
- `CanonReader` no longer reports an unreadable body as an empty one.
  `body_of` turned any read failure into `""`, which the merge detector then
  read as "this relation has no prose" — so two files nobody could open looked
  like the same statement and were offered for folding on a comparison that
  never happened. `body_or_none` returns `None` for unreadable and the detector
  skips those relations; `body_of` keeps its old contract for callers that only
  display prose. The regression test runs the real path: frontmatter is read
  once and cached while bodies are read lazily afterwards, so a file can be
  gone by the time its prose is wanted.
- Pointed the install instructions at the public repository. Every one of them
  — the marketplace to add, the clone URL, and `repository`/`homepage` in both
  plugin manifests — named `vadim-chiriac/worldbuilder`, which is the private
  development repository. Anyone following the documentation would have got a
  404 on the very first step. They now name `vadim-chiriac/worldkeep`, and the
  Claude marketplace is `worldkeep` to match.
- `publish.py --update` syncs an existing clone instead of demanding an empty
  directory, and **deletes** files the allowlist no longer names. Without that
  half, publishing is append-only: a file withdrawn from the allowlist would
  stay public forever. It refuses a target that is not a git repository, so a
  mistyped path cannot be emptied, and it is idempotent.
- The merge detector could recommend folding relations that SCRIBE requires be
  kept apart. Its own docstring claimed it compared provenance; the signature
  compared seven facets and nothing else, so two links differing only in
  `scribe.origin`, in their description, or in a field the world invented
  looked identical to it. All three now count, provenance is read in either
  spelling the format allows, and a relation whose prose cannot be read is left
  alone rather than guessed at — a wrong hint trains authors to ignore the
  right ones.
- The same detector required three relations before saying anything, while
  SCRIBE says "two or more". A plain pair is exactly the case a reader is least
  likely to spot unaided, and it was the one case that went unmentioned.
- `wb view <world>` rendered only `Everything`, while the skill, the session
  report and the documentation all said the default was every view. Everything
  is the audit projection — it ignores every style the world declared — so it
  was the wrong thing to hand back to "show me my world". Fixing it exposed
  that `--everything` had only ever worked by being the fallback branch rather
  than by being read; it now has its own.
- Corrected texts left behind by KERNEL v0.17: `KERNEL` §1.1 and `SCRIBE` §4
  still said five kinds, `apply.py`'s schema comment still listed `action` as a
  kind, and `validate.py` still claimed alignment with v0.14.
- Reconciled the changelog with itself. One entry said the plugin id stays
  `worldbuilding-canon` while a later one renamed it; both were in the same
  unreleased section.
- Documentation said edge-dropping starts "above sixty" edges; the code uses
  sixty or more.
- `apply.py` and `validate.py` read files without closing them, which raised
  `ResourceWarning` under the test suite. The suites now pass with warnings
  promoted to errors.

### Added

- Added `publish.py`, which assembles the public repository from an explicit
  allowlist and prints what it withheld and why. The list is positive on
  purpose: a denylist lets the next stray file arrive in a public repository by
  default, which is how five megabytes of rendered HTML and a test canon built
  from a copyrighted setting ended up tracked here. It refuses to assemble into
  a non-empty directory or inside the source repository.

  Assembling into a clean tree immediately caught a documentation bug: the test
  commands in `DEVELOPMENT.md` did not work, because each suite resolves imports
  against its own package and has to be run from its own directory, which is
  what `build.py` does and what the document did not say.
- Made the build idempotent. Two runs over identical sources produced different
  bytes, because `BUILD.txt` recorded the wall-clock time and every archive
  member carried its own timestamp — so with `dist/` committed, four files were
  permanently dirty in git and `DEVELOPMENT.md`'s claim that the build is
  byte-reproducible was only true across platforms, not across runs. Archive
  members now use a fixed timestamp and mode, and the build date is left to the
  commit that carries it.
- `publish.py` copies content and sets a fixed file mode rather than using
  `copy2`. A filesystem that reports everything as `0755` — a Windows mount,
  for one — would otherwise land every Markdown file in the public repository
  marked executable.
- Recorded the private/public split in `AGENTS.md` and `CLAUDE.md`: a new file
  defaults to private, adding one the public repository needs means adding it
  to the allowlist in the same change, and no path joins the allowlist without
  someone checking what is inside it.
- Moved `SPEC-HISTORY.md` from `Internal/` to `Specification/`. It explains why
  the format changed, which is worth publishing beside the specifications it
  documents; `Internal/` is now private notes only.

### Changed

- Renamed the plugin id from `worldbuilding-canon` to `worldkeep`, so the name
  people are told and the name they type are the same one. It had been left
  alone while the public name was provisional; now that it is settled, before
  anyone has installed is the only cheap moment to change an id. The generated
  mirror moves to `plugins/worldkeep/` with it.
- Renamed the Claude marketplace to `worldbuilder`, after the repository that
  serves it. Naming the catalogue and the plugin both `worldkeep` produced
  `/plugin install worldkeep@worldkeep`, which tells a reader nothing about
  which half is which.

### Added

- Added `Documentation/RELEASE-NOTES.md`, the narrative counterpart to this
  file: what Worldkeep is, what is different about it, and what to know before
  relying on it, written for an announcement rather than for a diff.
- Added `Documentation/TROUBLESHOOTING.md`, built from the failures this
  session actually produced rather than from imagined ones: the launcher, the
  "which folder" question, each validator error class, the empty-view
  diagnostic, the wide-row layout, the layout typo, disappearing edges, and
  `lock: stale`. It ends by asking for the reports that matter most — the ones
  where nothing failed and the result was quietly wrong, which are the ones
  tests do not catch.
- Added `Documentation/CONFIGURATION.md` — every `scribe.yaml` and `world.yaml`
  key, checked against the shipped files rather than against SCRIBE §10 alone,
  with a "common changes" section for the settings people actually reach for
  and the trade each one makes.
- Added `Documentation/LIMITATIONS.md`, written to be believed rather than to
  reassure. It names the format's youth and the absence of migration tooling as
  the one limitation that can cost real work, and lists the four bugs this
  week's documentation work found in shipped code — a default view that
  excluded every belief, a layout typo that validated clean, nesting that
  collapsed into a row, and thirty warnings fired at a user for files they
  never touched — because none were caught by tests, and that says something
  about the tests that a user deserves to know.
- Added `Documentation/USER-GUIDE.md`: replying to bundles, editing by hand and
  what goes stale when you do, what validation does and does not claim, `fiat`,
  drafts, and the merge notice. Every quoted output was produced by running the
  case, including the error and `fiat` examples.
- Added `Documentation/ROADMAP.md`, organized by theme rather than date, with
  the non-goals stated as decisions rather than as things not yet done. It
  splits the "wiki" question in two: replacing your prose editor stays a
  non-goal, while a generated read-only browsable surface is on the roadmap —
  the `(yet)` that had crept into the Overview's non-goals was conflating them.
  Migration tooling is named as the largest gap between now and a format that
  could be called stable.
- Added `Documentation/VIEWS.md`: `Everything` and why it ignores your
  configuration, the full `select`/`edges`/`layout`/`emphasis` vocabulary taken
  from the code rather than from memory, the four module kinds and why the
  split is four-way, composition read as set arithmetic, `--explain-view`,
  locks, and what the rendered page can do. Every command in it was run; the
  draft had `--explain-view` as a flag on `wb validate`, which does not exist —
  it is `wb explain`.
- Added `Examples/lower-fen`, a worked 16-artifact canon and the source for the
  README screenshot. It is built from the fragments already scattered through
  KERNEL and SCRIBE — Marrow Reach, the Fen, Old Coll's ferry, the Rope, the
  bell that rings for the drowned — so the specification's examples and the
  demonstration world are one world. Its `the-bell-dispute` view shows the four
  things a fixed-category tool cannot do: two-level place nesting, two rival
  doctrines as ideas rather than prose, `holds` edges weighted by conviction,
  and an action drawn as a hexagon because its type declares that lens.

### Fixed

- Collapsed the provenance warning into one line. The check is all-or-nothing —
  if any artifact carries a `scribe.*` stamp, every artifact without one is
  reported — so capturing a single artifact into a hand-written world produced
  a warning per untouched file, thirty of them on a sixteen-artifact example,
  burying anything real. Same information, one line, first three named. The
  mixed hand-written and captured world is the case the project advertises, and
  it was the case this handled worst.
- Merged three near-identical `part_of` relations in `Examples/lower-fen` into
  one with three `part` members, because the tooling's own merge notice fired
  on the project's own example. The rendered picture is unchanged — sixteen
  nodes, fourteen edges — which is the point the notice is making.
- A misspelt `layout` is now reported instead of swallowed. The renderer falls
  back to `fcose` for any value it does not know, and the compiler validated
  any string at all, so `layout: dagr` produced a clean `VALID` and a picture
  laid out by something other than what was asked for. The known layouts now
  live beside the compiler and a wrong one is a warning naming the alternatives.
- Stopped small graphs paying for a problem they do not have. Dropping edges
  during a pan, a zoom or a drag was applied unconditionally, so a 14-edge
  canon lost its relations while being moved to buy smoothness it never
  lacked. Both measures now switch on at 60 edges or more; below that
  everything stays drawn, and `textureOnViewport`, which costs nothing, stays
  on throughout.
- Removed the retired `action` kind from the shipped `Groups` view, which still
  selected `kinds: [entity, action, relation]` after v0.17 — naming a kind that
  can no longer match, while excluding `idea` entirely.
- Settled how a world represents something its people believe in but that does
  not exist — a god in a godless world. KERNEL §5 said an idea's content could
  be "a network of **entities**/relations/parts", which contradicted the same
  section's first rule that an artifact's existence is canon, and pointed
  readers at writing an entity for a thing that is not there. It now says idea
  parts, matching §7's worked example, and states the case outright: writing an
  entity *is* the existence claim, so a god without existence is an `idea` —
  a pantheon composes as idea parts, believers `holds` it, and a temple that
  exists can be `dedicated_to` a god that does not.
- Shipped `types/law.md` in the seed world. KERNEL §5 recommends `type: law`
  for narrator-stated rules, but the type was never shipped, so every world
  that followed the specification earned a warning for it.
- Stopped marking a verse of a held doctrine as `dormant`. The badge means
  nobody entertains the idea, and an idea `part_of` a doctrine somebody holds
  is in a head — it arrived with the whole. Holding a whole still does not
  commit a holder to every part, which is what lets a sect keep one turn of a
  story and reject another; this only decides whether a concept is live at all.

### Changed

- **Retired the `action` kind (KERNEL v0.17).** Four kinds remain: `entity`,
  `idea`, `relation`, `type`. Things that happen are `kind: entity` with the
  std type `action`; recurrent ones are `action/practice`. The two replace the
  former `instance` and `practice` type roots.

  This applies the kernel's own test — a distinction earns a kind only if
  kernel rules treat it differently — and `action` failed it. `when` and
  `where` are open to every artifact; periods were already entities despite
  occupying time, so the old split was an inconsistency rather than a
  principle; and instance-versus-practice was delegated to types from the
  start. Its one mechanical claim, that `participates` binds a real event, is
  now made by a new constraint, `role_types`, which pins a role to a type path
  and is satisfied by any descendant of it. `idea` was examined at the same
  time and kept: §5's carve-out for an idea's content cannot be stated about a
  type without letting kernel semantics depend on open vocabulary.

  The viewer's hard-coded hexagon and colour for actions moved into a `lens:`
  on `types/action`, so a visual now lives in canon rather than in the
  renderer. The validator names the retired kind and states the replacement,
  which is the only migration aid that exists. `actions/` stays in the folder
  convention, now noted in KERNEL §10 as a convenience named after a type
  rather than a kind, so a careful reader does not mistake it for an oversight.
- Made the multi-member relation the **default** in SCRIBE (v0.10), rather than
  a permission with a condition attached. Links that share a type, share a
  member in the same role, and differ in nothing else are one relation with
  several members; splitting is now the exception, for links that genuinely
  differ in time, status, provenance, description, or addressability.

  This corrects a measured bias rather than changing the model — the kernel
  always allowed it. Splitting is always legal, so a scribe weighing an
  uncertain condition splits every time, and every graph formalism in a model's
  training is binary. Prose alone had not moved that, so `wb session` and
  `wb capture` now report the groups left behind: relations of one type
  sharing one target with identical facets, with the count of members a single
  relation would carry. It is a notice, never an error — splitting is often
  deliberate, and the author decides. Relations that something else points at
  are never suggested for folding, because that would break the reference.

### Added

- Added `src/viewer/tests/test_filter_behaviour.py`, which extracts the filter
  functions from a rendered document and executes them under Node against a
  real canon. It writes and reads that document with explicit `\n`: the harness
  finds the bundle by splitting on a literal newline, so on Windows the file
  arrived CRLF and every split missed — the same platform fault the build
  itself carried, reintroduced by the test that was meant to catch faults. It
  also reports Node's own stderr on failure instead of raising through
  `check=True`, which turned a one-line JS error into a page of Python
  traceback saying nothing. The filter panel lives entirely in the browser, and asserting on
  the bundle's source text proved able to pass while the behaviour was wrong —
  the containment-collapse bug above shipped past a green suite. The tests skip
  when Node is unavailable rather than pretending to have checked something.
- Added **Find by name** to every rendered view: a search over names, ids and
  types that dims everything except matching artifacts and their containing
  boxes, and lists the hits in a scrollable panel. It dims rather than hides so
  positions stay put and a match can be read in the context that explains it,
  and it survives a filter toggle, which rebuilds every element. The match set
  is the state rather than the text in the box: emptying the query leaves the
  list standing, a **Highlight in graph** toggle decides whether the set is
  painted, and **Clear results** discards it. Clearing the query therefore
  cannot silently change two things at once, and a kept set can be re-lit
  without retyping it.
- Hiding an intermediate container with a filter no longer orphans what was
  inside it: the contents re-attach to the nearest visible container. Hiding
  the nine historical regions of a 40-county world moves each county straight
  into the country and leaves every seat inside its county, with nothing
  orphaned. Tracing the chain deliberately obeys the relation-type filter but
  not the cascade that drops relations touching a hidden artifact — those are
  precisely the relations it has to cross, and using the cascaded set instead
  meant the collapse never fired at all. The collapse only crosses a hidden
  level along an unbroken run of
  one relation type — `part_of` composes, so a seat inside a county inside a
  region really is inside the region, but a custom nesting type need not: the
  seat of a county is not the seat of its region, and drawing it there would
  assert something the canon never said. Unticking the relation itself still
  removes the nesting rather than rerouting it.
- The inspector now lists the relations an artifact takes part in, naming the
  role it plays and the artifact at the other end, both clickable. The list is
  built from the whole view rather than the filtered picture: an artifact's
  connections are canon, and hiding some behind a filter would quietly
  misreport what the world says. Selecting from the relation list, from the
  search results, or by clicking the graph all go through one function, so they
  cannot drift apart.

### Fixed

- Stopped `dagre` being used on a view that nests. dagre has no compound-node
  support — it ranks every node as if the graph were flat — so a nested canon
  collapsed into one very wide row inside stretched parent boxes. On a
  40-county administrative world that is 89 of 90 nodes rendered as a single
  line. The viewer now substitutes `fcose`, which is built for compound graphs,
  and says so in the warnings rather than drawing a picture that misrepresents
  the world. The shipped `Groups` view asks for `fcose` directly, since it
  always includes `part_of` and so would always have needed rescuing.
- Made panning, zooming and dragging cheap on nested views. Every compound
  parent was being re-measured and every edge label re-laid out on each frame,
  which is why an uncustomized `Everything` stayed smooth on a canon where a
  nesting view crawled. Panning and zooming now use Cytoscape's viewport
  levers; dragging, which those levers do not cover, hides the edges not being
  moved and drops the labels on the ones that are. All of it applies only
  during interaction, so the idle picture keeps full fidelity.

- Nesting now honours the role names a type declares, so a world can draw
  containment in its own vocabulary. `as: nest` reads the same `direction`
  pair an edge would — `[contained, container]` — instead of matching the
  literal strings `part` and `whole`. A `seat_of` declaring
  `direction: [seat, territory]` nests seats inside territories; a lens with no
  `direction` still means `part` and `whole`, so no existing canon changes.

  The role pair counts only when the **type file itself** declares `as: nest`.
  A view module may still override `as` to nesting, but it cannot reinterpret a
  relation's roles as inside/outside — a `direction` declared to orient an
  arrow is not a containment claim, and letting a view promote it to one would
  make the shape of the graph depend on who drew it. That is the same reasoning
  KERNEL v0.13 used to remove the renderer-dependent `group` behavior.

  The failure warning now names the roles the type actually declared rather
  than always saying "whole" and "part".

### Added

- Added `Documentation/INSTALLATION.md` and `Documentation/GETTING-STARTED.md`.
  Installation covers both hosts with the real marketplace files, plus
  verifying, updating, uninstalling, and why macOS and Linux are not claimed.
  Getting Started walks a first world from prompt to approved canon to a
  rendered view; every command and every line of quoted output in it was run
  against the tooling, which is how the relation example got corrected from
  flow-style YAML to the block style `apply.py` actually writes.
- Corrected `README.md` and `OVERVIEW.md`, both written before KERNEL v0.17:
  they described five kinds and the retired `instance`/`practice` type roots.
- Added the first public-facing documentation: `Documentation/OVERVIEW.md`
  (philosophy, mental model, audiences, architecture, non-goals, first-release
  status and the privacy nuance that the project has no server but the host AI
  still processes what you say), and `Documentation/DEVELOPMENT.md`, which
  takes the build, test, versioning and cleanup instructions out of the README.
- Rewrote `README.md` as a public pitch rather than a repository map: the
  promise, three ways to start, a five-minute quickstart, the supported-host
  table, a documentation index, and the licence. Its worked artifact example
  was validated against the real validator rather than written from the spec.
- Added `.claude-plugin/marketplace.json`, the catalogue Claude reads from a
  repository root. Without it the plugin could only be installed by hand: the
  existing `.agents/plugins/marketplace.json` is the Codex equivalent and
  Claude does not read it. Both point at the same generated mirror, and the
  entry deliberately carries no `version` — Claude silently prefers the one in
  `plugin.json`, so a second copy could only ever be wrong.
- Added `LICENSE` (MIT) and `THIRD-PARTY-NOTICES.md` covering the vendored
  PyYAML and the five Cytoscape components, all likewise MIT. MIT was chosen
  over a noncommercial source-available licence because the Claude plugin
  directory does not accept closed-source plugins, and directory distribution
  matters more here than reserving a commercial option that neither host
  ecosystem currently has the billing infrastructure to exercise.

### Changed

- Set the first public release version to `0.2.0` and the user-visible product
  name to Worldkeep in both plugin manifests. The plugin id was left alone at
  this point because the name was still provisional; it was renamed to
  `worldkeep` once the name settled, in the entry at the top of this section.

- Reorganized the repository so the source layout mirrors the shipped layout.
  Everything that ships now lives under `src/` — both skill manifests with the
  seed world and views library beside them, the canon runtime (`apply.py`,
  `validate.py`), the viewer, `wb`, and one `src/runtime/` holding the Python
  launchers and the single vendored PyYAML copy. The normative specifications
  moved to `Specification/`, leaving `Documentation/` for user documentation;
  `PROJECT-BRIEF.md` and `SPEC-HISTORY.md` moved to `Internal/`, which is not
  distributed. The three worlds the viewer suite asserts against moved from
  `Examples/` to `Testing/fixtures/`, since they were acceptance fixtures rather
  than examples; `Examples/` now holds example worlds only. Tests stay beside
  the code they test. `build.py` is correspondingly a near one-to-one copy
  rather than a collection from four unrelated folders.

  The shipped bundle is unchanged apart from six source-tree fallback paths and
  comments: 105 of 111 files are byte-identical to the previous build, and the
  six that differ do so only in the branches that fire when running from the
  repository, never from an installed plugin.

  The two PowerShell entrypoints moved with it: `update-plugins.ps1` and
  `Testing/test_run_python.ps1` both resolved the bundled launcher through the
  old `skill/` path and failed immediately after the move.

### Fixed

- Made the plugin build byte-reproducible across operating systems. The two
  generated plugin manifests were the only build outputs written rather than
  copied, so on Windows they picked up CRLF line endings while every other file
  kept the bytes `copy2` preserved. `dist/plugin.zip` therefore hashed
  differently depending on the machine that produced it, and `build.py --check`
  failed anywhere but Windows. Both manifests are now written with an explicit
  `newline="\n"`; no manifest content changed apart from the line endings and
  the licence field below. The generated local Codex mirror is normalized the
  same way after its cachebuster version is stamped, whichever writer produced
  it, because `plugins/` is tracked and was otherwise re-churned on every run
  from a different operating system.

### Changed

- Backed the `MIT` licence declaration in the Claude plugin manifest with an
  actual `LICENSE` file and third-party notices. The field had been asserting a
  licence the repository did not carry.
- Reduced the shipped default views from four to three and gave them plain
  names: built-in `Everything`, `Canon only`, and `Groups`. `Beliefs — who
  holds what, and what fights what` and `Places — nesting and what sits where`
  are gone, and `People, groups, and command` is now `Groups` with the same
  recipe. `Groups` carries an explicit caveat, in the view file and in the
  canon-viewer skill, that it covers only the default group vocabulary
  (`part_of/membership`, `subordinate_to`, `participates`, `part_of`) and will
  look empty in a world whose grouping lives in custom relation types. Applied
  to the views library, the seed world new canons are created from, and the
  HelloWorldia example; retained manual-test worlds keep their evidence.
- Viewing a world now defaults to rendering every available view — built-in
  `Everything` plus the defaults and any custom views saved under `views/` —
  in one document. A single view is rendered only when the author asks for
  one, when a new view is being previewed before saving, or when the request
  plainly names one. `wb session --task view` suggests `--all-views` first.
- The scribe now warns the author once, in one sentence, before its first
  KERNEL/SCRIBE reference read of a session, so the pause for loading those
  documents reads as setup rather than as a stalled reply. Reference loading
  itself stays lazy.
- Moved cumulative KERNEL and SCRIBE release histories into the repository-only
  `Documentation/SPEC-HISTORY.md`, leaving the bundled specifications focused
  on current normative behavior while retaining their versioned headings.
- Changed the default Scribe type policy from `existing_only` to `ask`: the
  scribe still reuses existing types first and may leave one-off artifacts
  untyped, but now proposes useful new vocabulary for author approval when a
  type earns its file. `existing_only` remains an explicit opt-in.

### Added

- Added `wb`, one agent-facing entrypoint shipped in both skills from a single
  canonical source, so an assistant can start a canon session and do ordinary
  work without locating scripts, managing plugin-relative paths, or reading
  whole reference documents first. `wb session <path>` resolves a canon (or a
  bounded root containing exactly one, listing candidates rather than guessing
  when there are several) and reports in one bounded, deterministic read: world
  name and path, Kernel/Scribe/tool versions with any compatibility problem,
  the effective `scribe.yaml` settings and whether each came from the file or
  the documented default, artifact counts by kind and status, the type
  vocabulary, named views and view modules, whether `INDEX.md` is current, the
  operations worth running next, and anything needing attention. On the
  Riverlight world that is roughly 2 KB in place of the ~74 KB an assistant
  previously read across SKILL.md, KERNEL.md, SCRIBE.md, and the index.
- Added `wb context`, a read-only selective view of a canon: search ids, names
  and tags; look one artifact up exactly; list an artifact's direct neighbours
  with the relations and roles connecting them; filter by kind, type, or
  status. It returns summaries and short prose snippets by default, states why
  each result matched, reports totals and omitted counts when truncating, never
  widens beyond one hop, never invents an artifact, and stays correct whether
  `INDEX.md` is fresh, stale, or absent.
- Added the rest of the unified CLI — `find`, `capture`, `approve`, `reject`,
  `reindex`, `validate`, `view`, `explain`, and `doctor` — as a thin
  orchestration layer over the existing tools. Canon changes still go through
  the same deterministic apply-and-validate boundary, capture still creates
  drafts without promoting them, approval and rejection remain separate
  explicit operations, and the viewer commands preserve the `Everything`
  contract and projection JSON unchanged. Child exit codes and diagnostics are
  passed through, `capture` accepts JSON on stdin or `--input-file`, and
  `--json` gives a stable envelope. The low-level `apply.py`, `validate.py`,
  and `view.py` interfaces are unchanged.

### Fixed

- Made the `wb` packaging regressions portable. The installed-layout tests
  asserted on trailing path text with POSIX separators, so they failed on
  Windows even though path resolution was correct. They now compare whole
  resolved paths against the staged bundle, which is separator-independent and
  additionally proves the resolver never escapes to the repository source tree.
  No production path handling changed.

### Changed

- Both skills now open with `wb session` as the normal fast path and load
  KERNEL.md and SCRIBE.md when a decision needs them rather than mechanically
  before every first reply. The reference documents remain authoritative and
  unchanged; only the instruction to pre-read them wholesale is gone.

- KERNEL v0.16 keeps named-view `part_of` containment unarrowed when it is
  rendered as nesting, while the Everything audit retains explicit
  part-to-whole arrows for reified containment. Added regressions and viewer
  guidance for the distinction.

- KERNEL v0.16 corrects standard hierarchy arrows to subordinate → superior
  and makes explicitly rendered `part_of` links point part → whole. Named
  custom views retain unarrowed `part_of` containment; Everything/audit now
  displays the part-to-whole direction. Focused binary, reified, audit, and
  nesting regressions cover the contract.
- Fixed the bundled Windows launcher to forward piped input, clarified that
  skill paths are skill-directory-relative, and made viewer PowerShell examples
  use the unambiguous `--output` option.
- Added a narrower Riverlight people-membership view that reuses the existing
  people selection, community colours, and ordinary membership-link modules.
- Added the Ash Harbor live-test world, confirming that one shared family
  statement is captured as a single multi-member membership relation.
- Refined the Riverlight people-centred view selection to retain only direct
  person-neighbour communities, excluding unrelated group-to-group membership.
- Added a reusable Riverlight people, affiliation/leadership, community-colour,
  and membership-link view composition for the Stage 4 live test.
- Documented that routine read-only verification and validation reporting
  should use the cheapest capable subagent, with primary-agent review.
- SCRIBE v0.8 replaces presets with five explicit author settings, reports
  their effective values at session start, and uses the closest defensible
  existing type by default rather than inventing vocabulary or leaving a
  reasonable broader type unused. Validation is now an unconditional
  post-mutation-batch invariant, including promotion and rejection; the seed,
  examples, tests, documentation, and generated plugin surfaces were refreshed.
- Migrated canonical and active-world former `Everything` YAML recipes to the
  viewer-owned audit contract: the canonical copies were removed, four active
  fixture/manual recipes now remain available as `Styled world overview`, and
  viewer guidance directs durable styling or selection to approved named views.
- The manual gallery now renders only active/current worlds and excludes
  retained `Testing/runs` evidence with legacy view recipes.
- Viewer type filters now retain each node's last on-screen position during a
  session and preserve the current pan/zoom viewport: filtering refits the
  retained layout rather than randomizing it, returning nodes resume their
  earlier location, and the canonical viewer guidance documents the behavior.
- Added a single canonical collaboration policy for all agents: close work in
  small steps, delegate bounded tasks cost-consciously with central review,
  avoid workaround loops, escalate external setup blockers to the user, and
  test proportionately.
- Viewer views can now anchor direct-neighbour selection by exact type paths
  via `connected_to_types`, and every graph projection has resettable local
  artifact/relation type filters with logical visible counts. The controls keep
  exact artifact keys and active inspector data in sync, preserve reified,
  containment, hidden, and state relations whole, while `Everything`
  remains an independent audit surface; viewer guidance and generated plugin
  surfaces were refreshed with the canonical sources.
- KERNEL v0.15 adds explicit, presentation-only relation-lens direction.
  Projection now carries a boolean `directed` on every edge, resolves declared
  role endpoints independently of member order, safely falls back with
  warnings, and routes directed reified spokes through relation nodes. The
  graph viewer renders target arrowheads using the projected edge color;
  documentation, acceptance canon, tests, and both generated plugin surfaces
  were updated together.
- KERNEL v0.14 lets one `part_of` relation state one whole and multiple
  parts, while retaining binary containment. Added inherited, fiat-aware
  `roles_unique` validation for the unique whole and `participates` action;
  the viewer now nests every valid part and preserves invalid containment as
  inspectable generic reification. Updated scribe guidance, examples, tests,
  and both generated plugin surfaces; direction and arrowheads remain queued.
- KERNEL v0.13 removes the renderer-dependent `rank` and `group` lens
  behaviors. The behavior vocabulary is now `edge`, `nest`, `chip`, `hide`;
  `subordinate_to` and `part_of/membership` render as ordinary edges.
  Hierarchy that reads top-to-bottom is a property of the view's `layout`,
  not of the type. A type file still declaring `as: rank` or `as: group`
  degrades to `edge` with a warning. Spec, both skill documents,
  the packaging brief and the acceptance-world README updated to match; the
  v0 viewer brief keeps its original wording as history, with a pointer.
- Removed `rank` from the viewer in the same change as the spec, because
  `test_spec_sync.py` holds KERNEL §8 and `project.BEHAVIORS` equal by
  design — a spec-only edit turns the build, and therefore both plugin
  rebuilds, red. A world modelled entirely in std types now draws its
  relations: the checked-in Seven Kingdoms fixture goes from 0 visible
  edges to 9.

### Fixed

- Fixed interactive viewer filters stopping before relayout and count refresh
  because their inspector reset was out of scope, and made artifact filter keys
  safely round-trip through DOM attributes so toggles can be restored reliably.

- Packaging now assembles specs and seed assets only from their canonical
  documentation and testing sources. Removed obsolete source-skill copies and
  retained an early canonical seed-version check before either plugin surface
  is refreshed.
- `where_under` now follows every relation resolved as `nest`, including
  hierarchical `part_of` descendants while excluding edge-lensed membership;
  generated root `INDEX.md` files are ignored without a frontmatter warning.
  Added targeted n-ary containment/reification coverage and repaired obsolete
  manual-evidence references after `Testing/manual/got-world` replaced the
  earlier fixtures.

### Added

- Named custom views can now compose reusable, independently useful modules.
  A world may keep typed `selection`, `relation`, `style`, and `lens` units
  under `view-modules/` and combine them from a view's `compose` block. Views
  compile to one normalized, provenance-bearing plan before projection, so
  selection set algebra, relation include/exclude, the property-by-property
  style cascade, and lens overlays resolve deterministically and are explained
  rather than guessed. Exclusion always wins, a view-local `select` may only
  narrow, and disagreeing anchor policies or structural `as`/`direction`
  declarations fail instead of silently picking a winner; an unresolved
  structural conflict still renders but only through a prominent unvalidated
  fallback that cannot be locked. Existing views without `compose` and the
  viewer-owned `Everything` audit projection are unchanged, and the renderer
  keeps consuming the same projection element shapes.
- Composed views now distinguish an explicit relation include from the
  implicit relation default. Naming modules under `compose.relations.include`,
  or a non-empty view-local `edges.include`, stays independent of artifact
  selection and may pull a relationship's far endpoint onto the page as a
  reported endpoint completion. Without one, the relation set is only a
  default and resolves to the induced subgraph: relations whose endpoints are
  already selected, completing nothing. A style-only composition narrows no
  artifacts and so still shows the full graph, while `any_of: [people]` alone
  now shows people and the links among them instead of reaching the rest of
  the world through every other relation. Exclusions still win in both modes,
  and legacy views and `Everything` are unaffected.
- Composed views now complete relation endpoints as a projection-integrity
  step, so a relation a recipe selected is drawn whole instead of silently
  omitted when its endpoint fell outside the artifact selection. Completion
  keeps the semantic selection result separate: completed endpoints are
  displayed and styled, are reported through `endpoint_completions` and a
  diagnostic, and are explained as displayed only because an independently
  selected relation requires them — they never become selection results, never
  alter selection provenance, and never resurrect an excluded relation. Missing
  or policy-excluded endpoints are still not invented and keep failing
  validation for composed views; legacy views, `Everything`, and one-hop anchor
  behaviour are unchanged.
- Added `--validate-view` and `--explain-view`, which check determinism and
  renderability or trace one artifact's inclusion, style, lens, and nesting
  back to the module or local rule responsible. Both work without generating
  HTML and emit human-readable or stable JSON output. `--validate-view
  --write-lock` records dependency fingerprints in an adjacent
  `views/<stem>.view.lock.yaml`, written only on request and only after a
  clean result; a changed view, module, relevant type lens, or schema marks a
  lock stale and names what moved, while ordinary canon edits do not.
- Extended the canon-viewer skill with guidance for classifying a request into
  selection, relation, style, and lens concerns, and for previewing,
  validating, and explaining a composition before asking the author to approve
  saving any durable view, module, or lock. A style-only request now becomes a
  differently named custom view rather than a change to `Everything`.
- Added `Examples/composition-acceptance`, a small readable world whose single
  view demonstrates composition, overlapping membership, property-specific
  style precedence with named winning and losing sources, and one structural
  lens conflict resolved by an exact view-local rule.
- Added an Opus-oriented Phase 2 implementation handoff for modular custom
  views, with sequential delivery stages, bounded cheap-subagent roles,
  explicit stop-and-ask boundaries, focused validation gates, and a final
  user-review package tied to the normative custom-views specification.
- Viewer-owned `Everything` is now an always-available, unshadowable audit
  projection: it lists first, works without world view files, selects the
  active general graph with neutral marks, and ignores custom view/type lenses
  and emphasis while retaining every safely renderable relation visibly.
- Added `Orchestration/CUSTOM-VIEWS-BRIEF.md`, a phased implementation design
  that reserves an uncustomized, viewer-owned `Everything` audit projection
  before adding typed, provenance-bearing composition for reusable named view
  selection, relation, style, and lens modules with validation and explanation.
- Added `Orchestration/RELATION-DRIVEN-VIEWS-BRIEF.md`, an implementation brief
  for durable views built from typed anchors and selected relation types, plus
  projection-derived interactive type filters that keep `Everything` useful
  as an author-controlled audit surface. It specifies backward-compatible
  `select.connected_to_types`, direct-neighbor expansion, complete filtering
  across edges, reification, nesting, and state chips, visible/total counts,
  agent guidance, and focused regressions. Bounded evidence paths, semantic
  inference, and a generated custom-type legend are parked as separate future
  designs.
- Added `Orchestration/RELATION-CARDINALITY-BRIEF.md`, a proposal prompted by
  33 observed binary `part_of` files and zero n-ary examples. It defines one
  addressable relation as a statement rather than necessarily one edge,
  proposes one-whole/many-parts containment, a minimal `roles_unique` formal
  constraint, scribe batching rules, and matching validator/viewer acceptance.
  Its approved cardinality scope is implemented; the direction brief remains
  explicitly queued as separate work.
- Added `Orchestration/VIEWER-DIRECTION-BRIEF.md`, a bounded implementation
  brief for explicit role-based edge direction, arrowheads, safe undirected
  fallback, reified/n-ary direction, projection and renderer tests. It
  supersedes addendum 2's earlier proposal to infer direction from
  `roles_required` order; diagnostics remain a separate next item.
- Added `Orchestration/VIEWER-BRIEF-ADDENDUM-2.md` — implementation brief
  for removing `rank` and `group`, deriving edge
  direction from roles rather than member order, and reporting how much of
  a view renders no visible mark.
- Added `Orchestration/SCRIBE-QUESTIONS.md` — six open modelling questions
  raised by the manual runs (std-type coercion vs type reluctance,
  person-vs-office, hierarchy skipping, relation naming, extraction of
  process versus structure, declared inference). Questions only.
- Added the project summary, mandatory changelog policy, and one-command
  Claude/Codex plugin update pipeline.
- Added ignore rules for generated Python caches, viewer scratch output, and
  obsolete build directories.

## [0.1.2] - 2026-08-10

### Added

- Added a dual-host plugin bundle with Claude and Codex manifests and two
  bundled skills: Worldbuilding Scribe and Canon Viewer.
- Bundled a self-contained Python/YAML runtime path and quiet launchers so canon
  operations do not depend on the broken system Python launcher.
- Added writer regression coverage to the packaging build alongside the viewer
  test suite.

### Fixed

- Corrected YAML serialization for one-item collection fields such as `where`,
  preventing invalid inline output such as `where: - entities/kings-landing`.
