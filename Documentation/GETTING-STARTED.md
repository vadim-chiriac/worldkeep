# Getting started

You need the plugin installed — see [INSTALLATION.md](INSTALLATION.md).

---

## 1. Say where the world lives

Open your AI host and say something like:

> Let's start a world in `Worlds/Hask`.

Naming the folder matters. Your working directory is usually a project root
rather than a world, and the scribe will not scatter `entities/` and
`relations/` among unrelated files. If you don't name one, it looks for a
folder containing `world.yaml`, and asks rather than guesses when it finds
several or none.

The scribe copies a seed world into place (manifest, starter type library and two ready-made views) and asks what the world is called. Answer, and you're
started. That is the whole of the setup.

---

## 2. Talk

Describe your world however you like. Narration, rambling, a list, an
in-character monologue: none of it needs to be in schema-shaped sentences.

> Marrow Reach is a fen village at the ford, half of it on stilts. It sits in
> the Fen — wet country, slow water, few roads. There was a fever a while back
> that cut the village roughly in half.

Nothing is committed while you talk. Every candidate is written straight to
disk as a **draft**, so a session that dies mid-sentence loses nothing, but
nothing counts as canon yet.

---

## 3. Approve decisions, not files

At a natural pause the scribe shows you **bundles**: one per thing you
actually said, with the file count as a footnote:

```
Captured 4 artifacts in 3 bundles.

1. Marrow Reach, a fen village at the ford      — 2 files
2. Where it sits: inside the Fen                — 1 file
3. The fever, and the village halving after it  — 1 file
     inferred: recorded as an event anchored at Marrow Reach

New vocabulary: none
Validation: clean

ok · ok 1 3 · no 2 · 2: it's downstream of the ford · later 3 · show 2
```

For a bundled capture, those file counts are checked from the draft batch
before anything is written: an artifact cannot be absent from a bundle or
appear in two. The scribe reports the resulting structure as well (new versus
updated artifacts, new type files, relation member counts, and any changed
kind/type). That is an audit aid, not a judgment that a classification is
correct. The prose summary also says what was left prose-only or deferred.

The reply line is the whole interface:

| you say | what happens |
|---|---|
| `ok` | everything becomes canon |
| `ok 1 3` | bundles 1 and 3 become canon; the rest stay drafts |
| `no 2` | bundle 2's drafts are deleted |
| `2: it's downstream of the ford` | bundle 2 is corrected, in your words |
| `later 3` | bundle 3 stays a draft, unmentioned until you ask |
| `show 2` | bundle 2 explodes into its files, individually addressable |

Anything the scribe invented, inferred, or composed itself is named in the
bundle that contains it. It never arrives silently.

Under the hood, approval is a single-field change, and the tooling says exactly
what it touched:

```
promoted 4 to canon:
  entities/marrow-reach
  entities/the-fen
  relations/marrow-reach-in-the-fen
  actions/the-fever
INDEX.md: regenerated (21 artifact(s))
Validation: clean
```

---

## 4. Optional: what you now own

This is the structure under the conversation. If you would rather see the
result first, skip to [Look at it](#6-look-at-it) and come back when you want
to edit or inspect the files yourself.

```markdown
---
id: entities/marrow-reach
kind: entity
type: place
name: Marrow Reach
status: canon
scribe.origin: mixed
scribe.session: getting-started
---

A fen village at the ford, half of it on stilts.
```

One artifact, one file, readable in any editor. `scribe.origin: mixed` records
that the agent chose some of this rather than transcribing you word for word —
provenance is stamped as it writes, because nobody adds it afterwards.

The village being *in* the Fen is its own file, not a field:

```markdown
---
id: relations/marrow-reach-in-the-fen
kind: relation
type: part_of
members:
- id: entities/marrow-reach
  role: part
- id: entities/the-fen
  role: whole
status: canon
scribe.origin: mixed
scribe.session: getting-started
---
```

That is the one structural idea worth absorbing early. **Connections are
artifacts.** Because a relation is a file with an ID, another relation can
point at it, and an idea can be *about* it — which is how contested history and
secrecy get modelled without any special machinery.

---

## 5. Ask what's there

> What's in this world?

```
world: Hask
versions: kernel 0.19 (doc v0.19), scribe v0.13, wb 0.2
artifacts: 21 (entity 3, relation 1, type 17)
status:    canon 21
scribe:    approval=strict, prose=compose, types=ask, extraction=eager, bundles=full
std types: action, action/practice, holds, opposes, part_of, participates,
           period, precedes, state, subordinate_to
views:     Everything (built in) + 2 named
index:     fresh (21 artifact(s))
```

Most of those 21 are the type library that came with the seed. Three entities
and one relation are yours.

---

## 6. Look at it

> Show me my world.

The agent returns a link to a generated, self-contained `.html` file. Your
canon remains in `Worlds/Hask`; the HTML is a disposable view of it. One file,
no network, it opens in any browser now and in ten years. Click any node to
read its canon file; use **Find by name** to locate something in a large world;
use the filters to hide a whole category and watch what survives.

Ask for something narrower and the viewer writes a view for it:

> Just show me who rules what.

> Only the religious conflicts, with the temples nested inside their cities.

A **view** is a small YAML file saved in `views/` beside your world, so the
question you asked once is answerable again by name. `Everything` is always
there too: the neutral audit that ignores every style you've defined, including
drafts, for when you want to see what is actually in the folder rather than
what you meant to put there.

---

## 7. Keep it in git

```powershell
cd Worlds\Hask
git init
git add -A
git commit -m "Marrow Reach and the fever"
```

This is the honest backup, and it costs nothing: the canon is plain text, so a
commit before a long session is a complete snapshot you can diff and revert.
The format is young and may still change — see [LIMITATIONS.md](LIMITATIONS.md)
— and a commit is what makes that a nuisance instead of a loss.

---

## Where to go next

| you want to | read |
|---|---|
| know why it is shaped this way | [OVERVIEW.md](OVERVIEW.md) |
| work with it day to day | [USER-GUIDE.md](USER-GUIDE.md) |
| get exactly the picture you want | [VIEWS.md](VIEWS.md) |
| be asked less often, or more | [CONFIGURATION.md](CONFIGURATION.md) |
| model something awkward | `Specification/KERNEL.md` |
| inspect a finished small world | [`Examples/lower-fen`](../Examples/lower-fen) |
