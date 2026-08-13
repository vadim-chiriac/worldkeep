# User guide

Day-to-day work: how to talk, what to say to the replies, when to reach past
the agent and edit files yourself, and what the validator is and is not telling
you.

If you have not built a world yet, start with
[GETTING-STARTED.md](GETTING-STARTED.md).

---

## Talking

Talk as you would to a person who is taking minutes. Narration, argument,
tangents, bullet points, thinking aloud, changing your mind mid-sentence: all
of it is fine, and none of it needs to arrive in schema-shaped pieces.

The one thing worth being explicit about is **which folder**. Your working
directory is usually a project root rather than a world, and the scribe will
not seed a canon into it and scatter `entities/` among unrelated files. Name
the folder once at the start; after that it stays out of your way.

Nothing you say is committed while you talk. Every candidate is written to disk
immediately as a **draft**, so a session that dies loses nothing — but nothing
counts until you say so.

---

## Replying to a bundle

At a natural pause you get bundles: one per thing you said, with the file count
as a footnote.

```
Captured 11 artifacts in 3 bundles.

1. Marrow Reach, a fen village at the ford            — 2 files
2. The fever, and the village halving after it        — 5 files
     inferred: population modelled as two states (600 → 280)
3. Old Coll's ferry, and what it costs                — 4 files

ok · ok 1 3 · no 2 · 2: she's the ferryman's daughter · later 3 · show 2
```

| you say | what happens |
|---|---|
| `ok` | all of it becomes canon |
| `ok 1 3` | those bundles become canon; the rest stay drafts |
| `no 2` | that bundle's drafts are deleted |
| `2: she's the ferryman's daughter` | bundle 2 is corrected, in your words |
| `later 3` | stays a draft and is not mentioned again unless you ask |
| `show 2` | explodes into numbered files, then `2.3: no` addresses one |
| `drafts?` | lists what is parked |

**Read the footnotes, skim the rest.** The headline is your own sentence back
at you; the interesting lines are `inferred:`, `invented:`, `added prose:` and
anything about new vocabulary. Those are the places the agent made a decision
rather than a transcription, and they are surfaced precisely so you can catch
the one that is wrong.

**`later` is not a snooze.** A parked draft stays a draft indefinitely and will
not resurface on its own. Incompleteness is a supported state here, not a
backlog.

---

## Editing by hand

The agent is a convenience, not a gatekeeper. A canon is Markdown and YAML, and
editing it in your editor is a first-class way to work — fixing a typo through
a conversation is absurd.

Some things are easier by hand: renaming, bulk edits, reordering prose,
anything you can do faster with find-and-replace than with a sentence.

Two things to know.

**The index goes stale, and says so.** `INDEX.md` is generated. Add a file by
hand and the next session report tells you:

```
index:     stale (1 artifact(s) missing, 0 no longer present)
```

Ask the agent to reindex, or run it yourself:

```
wb reindex <world>
```
```
INDEX.md: regenerated (50 artifact(s))
```

Nothing breaks while it is stale. The index is a convenience for lookup, not a
source of truth — the files are.

**Provenance is stamped by the agent, not by you.** Artifacts the scribe writes
carry `scribe.origin` and `scribe.session`. If a world contains any stamped
artifacts, the validator will point out the ones without stamps, once:

```
WARNING: 28 artifact(s) have no scribe.origin/scribe.session in a world that
stamps provenance (actions/the-crossing, actions/the-fever, +26 more)
```

That is a note about a mixed-authorship world, not a fault. Ignore it, or stamp
by hand if you care.

---

## What validation is telling you

Validation runs automatically after every change. `Validation: clean` is the
usual answer, and it means exactly this much:

```
artifacts: 47

ERRORS: 0

WARNINGS: 0

NOTICE (fiat)S: 0
```

**Errors are mechanical, and they are real.** A dangling reference, a duplicate
id, a missing kind, an empty relation, or a constraint your own type file
declared:

```
ERRORS: 2
  ERROR: relations/bad-participation: role 'action' bound to type 'person', requires ['action']
  ERROR: relations/marrow-reach-in-the-fen: dangling reference 'entities/the-marsh'
```

Both of those are broken *files*, not disputed *facts*. The first points at a
member that is not what its own type demands; the second points at nothing at
all.

**Nothing about your world's sense is checked.** The validator will not notice
that your king died twice, that a battle happens before the war, or that two
doctrines contradict. That is deliberate: contested history and deliberate
ambiguity are content, and a tool that tidied them away would be deleting the
part worth keeping. The agent may mention a tension it noticed; you are free to
say it is intentional and move on.

### `fiat` — when you mean it

Sometimes the impossible thing is the point. Mark the artifact:

```yaml
fiat: true
```

and constraint violations on it are downgraded from errors to notices:

```
ERRORS: 1
  ERROR: relations/marrow-reach-in-the-fen: dangling reference 'entities/the-marsh'

NOTICE (fiat)S: 1
  NOTICE (fiat): relations/bad-participation: role 'action' bound to type 'person', requires ['action']
```

Note what did **not** move: the dangling reference is still an error. `fiat`
overrides *declared rules* — your own constraints, the world's own laws. It
does not make a pointer to a nonexistent file acceptable, because that is not
a claim about your world, it is a broken file.

---

## Drafts

Everything arrives as a draft. Three things can happen to one.

```
wrote 1 artifact(s) (session guide, status draft):
  entities/the-tollhouse
INDEX.md: regenerated (50 artifact(s))
Validation: clean
```

**Approved**, and it becomes canon — a single-field change, reported by name.
**Rejected**, and the file is deleted:

```
deleted 1 draft(s):
  entities/the-tollhouse
INDEX.md: regenerated (49 artifact(s))
Validation: clean
```

**Or neither**, and it stays. A world can carry drafts indefinitely; they show
up in the viewer and in `drafts?`, and nowhere else.

The session report always tells you where you stand:

```
artifacts: 50 (entity 14, idea 3, relation 14, type 19)
status:    canon 49, draft 1
```

---

## Several links that say one thing

If you tell the agent that three villages are in the same fen, that is **one**
relation with three `part` members, not three files. The picture is identical
either way — a relation is one addressable statement, not one edge — and one
file is easier to change.

The tooling notices when it happens anyway, because every graph format in
common use is binary and the pull toward one-edge-per-file is strong:

```
could be one relation (1):
  3 'part_of' relations share whole entities/the-fen with identical facets;
  one relation with 3 'part' members would say the same thing
```

It is a notice, never an error. Split when something actually differs: a
different date, a different status, a different source, or a link that
something else needs to point at. Those are common and legitimate. Habit is
not.

---

## Being asked less, or more

`scribe.yaml` beside your world controls how often you are consulted:

```yaml
approval: strict         # strict | material_only | deferred
prose: compose           # compose | quote | none
types: ask               # existing_only | ask | free
extraction: eager        # eager | stated_only
bundles: full            # full | terse | none
```

The defaults are the cautious ones. `approval: material_only` is the setting
most people reach for second: routine capture goes straight to canon, and you
are still stopped for new vocabulary, contradictions, `fiat` and deletions.

Full explanations are in [CONFIGURATION.md](CONFIGURATION.md).

---

## Seeing it

> Show me my world.

> Just who rules what.

> Only the religious conflicts, with the temples nested inside their cities.

The agent writes a view file for the question and renders it, so the question
is answerable again by name. `Everything` is always there as the neutral audit
— it ignores every style you have defined, and shows drafts — for when you need
to know what is in the folder rather than what you meant to put there.

[VIEWS.md](VIEWS.md) covers views in full.

---

## When something looks wrong

**An artifact is missing from a picture.** Render `Everything` first. If it is
there, your view is filtering it out; if it is not, it is not in the canon.
That is the whole diagnostic, and it takes ten seconds.

**The agent wrote something you did not say.** Bundles surface inferences on
purpose. Correct it in plain words — `2: no, she's his daughter` — rather than
editing the file, so the correction lands in the conversation the agent is
still holding.

**Something is broken.** [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
