# Overview

Worldkeep is a local-first system for building a fictional world as **structured
canon**: plain Markdown and YAML files you own, written for you by an AI agent
that proposes and never decides, and rendered into graphs you can actually look
at.

This document explains what it is, why it is shaped this way, and, just as
importantly, what it is not. If you want to start using it instead, go to
[GETTING-STARTED.md](GETTING-STARTED.md).

---

## The mental model

One sentence carries the whole design:

> Conversation or hand-edited files → structured canon → validation →
> view `Everything`, or your own reusable views.

Everything else is detail. You talk about your world, or you write the files
yourself. Either way you end up with the same thing: a folder of artifacts with
enough structure to be inspected, validated, reused, and drawn.

The promise is not "an AI generates a knowledge graph for you." It is narrower
but maybe more useful:

- **Freedom to describe almost anything.** No fixed taxonomy of races, realms,
  or character sheets. Four kernel kinds and an open vocabulary on top.
- **Enough structure to do something with it.** Validate it, query it,
  reuse it, render it, and still read it in a text editor in ten years.
- **Several doors in.** Talk naturally; or edit Markdown and YAML directly; or
  go further and define your own types, relation semantics, and composable
  views — this is where the real power is, and the agent can do it for you.
- **The author stays the author.** Nothing enters canon without your approval.

---

## Why it exists

Two things already exist, and both are frustrating in opposite directions.

**Prose notes** — a folder of documents, a wiki, a pile of Markdown; they are
infinitely flexible and completely opaque. You can write anything, and you can
find nothing. There is no way to ask "who currently rules what," because
nothing in the notes distinguishes a ruler from a sentence containing the word
"rules."

**Worldbuilding databases** are queryable precisely because they decided in
advance what a world contains. Character, location, organization, item. That
works beautifully until your world contains a contested doctrine, a river that
is also a legal person, or a famine that changes a village's population over
two centuries — and then you are fighting the schema instead of writing.

Most of them do let you customise: custom fields, custom article templates,
sometimes CSS and a templating language if you are willing to learn one. But
categories still usually frame the world: you are adding fields to a Character,
not deciding whether "character" is a useful distinction in your setting. And customising is a thing you stop and go
configure, which means you only do it when the friction has already become
annoying enough to interrupt you.

Worldkeep aims at the space between: **structured freedom**. A kernel small
enough that it does not presume what your world is made of; structure uniform
enough that tools can still act on it; and a process that never asks you to
touch the technical layer unless you want to.

The bet is that the interesting complexities of a setting, like esotericism,
propaganda, contested histories, institutions that outlive their founders,
should *emerge* from a tiny set of primitives rather than ship as a feature
list. If a modelling need shows up, the first question is whether the kernel
already expresses it. Usually it does.

---

## How it works

### Four kinds, open vocabulary

Every artifact is one file with YAML frontmatter and a free-form Markdown body.
Every artifact has exactly one **kind**, and there are only four:

| kind | what it covers |
|---|---|
| `entity` | anything that *is* — a person, a guild, a mountain, a book, a god, a tank |
| `idea` | propositional content — doctrines, theories, values, rumours |
| `relation` | a connection between artifacts, always its own file |
| `type` | the definition of a category you invented |

The kinds are closed. Everything else (what counts as a `place`, a `guild`, a
`heresy`, a `trade-route`) is open vocabulary you or the agent invent as you
go, and it is declared in `type` files that live in the canon like any other
artifact.

Things that *happen* are entities too, typed `action` (or `action/practice` for
a recurring one). There was a fifth kind for them until recently; it was
retired because nothing in the kernel actually treated happening differently —
`when` and `where` are open to every artifact anyway. That is the test a kind
has to pass, and only these four do.

Two consequences are worth stating plainly (they can be surprising):

**The ontology is flat.** People, institutions, objects and deities are all
entities. Whether something acts or is acted upon is not baked into what it is;
it emerges from the relations it participates in. A river can hold a legal
right without becoming a special case.

**Relations are first-class.** A relation is a file with an ID, which means a
relation can be the target of another relation or the subject of an idea. That
one property is what lets secrecy, disputed accounts, and beliefs *about*
beliefs be modelled without any dedicated machinery.

### Draft, then approve

The scribe extracts liberally and commits nothing. Everything it hears becomes
a candidate written to disk immediately as `status: draft` — nothing is lost,
including to a session that dies mid-sentence — and it is presented back to you
in **bundles**: one bundle per thing you actually said, with the file count as
a footnote rather than the content.

```
Captured 11 artifacts in 3 bundles.

1. Marrow Reach, a fen village at the ford            — 2 files
2. The fever, and the village halving after it        — 5 files
     inferred: population modelled as two states (600 → 280)
3. Old Coll's ferry, and what it costs                — 4 files

ok · ok 1 3 · no 2 · 2: she's the ferryman's daughter · later 3 · show 2
```

You approve decisions, not files. Only approval promotes a draft to
`status: canon`. What the agent invented, inferred, or composed on its own is
surfaced in the bundle that contains it, rather than smuggled in.

This is configurable (`scribe.yaml` sets how often you are consulted) but the
default is the strict one, and the direction of the default is deliberate.

### Validation is formal, and only formal

The validator checks what can be checked mechanically: duplicate IDs, dangling
references, missing kinds, empty relations, and the constraints your own type
files declare. It runs automatically after every change.

It does **not** check whether your world makes sense. Semantic tension is
surfaced narratively by the agent, as an observation, and you are free to
ignore it. `fiat: true` on any artifact means *this stands as written* — against
declared constraints, against established context, against the world's own
physics. Tools may note the conflict once; they may not enforce it.

Incompleteness is a supported permanent state. Loose ends, dormant ideas,
connections with no stated meaning, unanswered mysteries: these are content,
not a to-do list, and nothing in the system nags you toward resolving them.

### Two ways to see it

**`Everything`** is the built-in audit view. It always exists, needs no
configuration, and deliberately ignores every style, lens and emphasis you
have defined. It is the neutral instrument you use to check what is actually
there, including drafts.

**Named views** are saved interpretations, written as small YAML files in
`views/` beside your world. A view selects artifacts, decides which relations
are drawn, and how things look. When the same concern keeps recurring (the
same cast of people, your faction colours) you lift it into a reusable
**module** under `view-modules/` and compose views out of them.

Renders are self-contained HTML: one file, no network, opens in ten years.

---

## Who it is for

**Writers who want to talk.** You describe your world in whatever register
suits you: narration, rambling, in-character monologue, bullet points. Then you
approve what gets written down. You never have to think in schemas, and the
interface never makes you work at file resolution.

**Hands-on worldbuilders.** The canon is plain files in a git repository. Edit
them in any editor, diff them, branch them, revert them. The agent is a
convenience, not a gatekeeper; nothing about the format requires it.

**Systems people.** Define your own types with declared constraints and viewer
semantics. Compose views from selection, relation, style and lens modules.
Validate and explain a view before saving it, and lock the inputs behind it so
you find out when one moves.

You do not have to pick one. Most sessions drift between the first two.

---

## Architecture

Worldkeep is **agent-native rather than "AI-powered."** It ships as a plugin
containing two skills, and what a skill contains is instructions plus local
tools. The AI you already use becomes the runtime; the plugin tells it how to
behave and gives it deterministic scripts to do the actual writing.

That distinction matters in practice:

- **No server, no account, no SaaS.** There is no backend to sign up for and
  nothing to keep paying for.
- **No separate database or ontology tool.** The canon is the folder.
- **Not built into Claude or ChatGPT.** It is a plugin you install, not a
  feature of those products, and it works the same way in both.
- **Canon writes go through one deterministic boundary.** The agent does not
  hand-write files one tool call at a time; it calls an apply-and-validate
  script that stamps provenance, runs the validator, and reports exactly which
  paths it wrote. That report is what the bundle's arithmetic is checked
  against.

The pieces:

| piece | what it does |
|---|---|
| **scribe skill** | the conversation → canon loop, plus the canon runtime and a seed world |
| **viewer skill** | turns a request for a picture into a view, and renders it |
| **`wb`** | one agent-facing command shipped in both skills: resolve a canon, report its state, search it, capture, approve, validate, render |
| **KERNEL.md** | the normative data model, shipped verbatim inside the plugin |
| **SCRIBE.md** | the normative behaviour of the capture loop, likewise |

The specifications ship *verbatim* rather than being summarized into the skill
files. Nothing has to be kept in sync, because no rule is written twice.

---

## Extensibility

The kernel is closed; everything above it is not.

- **Standard semantics ship with it.** A starter library of relation types —
  `part_of`, `holds`, `opposes`, `subordinate_to`, `participates`, `action`,
  `action/practice`, `period`, `state`, `precedes` — plus six entity types to
  start from (`place`, `person`, `object`, `text`, `community`, `law`). Useful
  defaults, not a required ontology.
- **Worlds add their own types.** A type file can declare expected roles,
  constraints the validator will enforce, and a `lens:` block telling viewers
  how relations of that type should be drawn.
- **Views compose.** Four independent concerns — which artifacts, which
  relationships, what things look like, how a relation is structured — are four
  separate module kinds, and a view names the modules it wants.

What extensions may **not** do is add kinds. A system with different base kinds
is a different system expressing a different view of what a world is made of —
a fork rather than an extension, and a legitimate thing to build.

---

## What it is not

- **Not a writing application.** It has no editor and no page templates. It
  stores structure; your prose can live wherever you like writing it, including
  in the artifact bodies. That one is a decision, not a gap — see
  [ROADMAP.md](ROADMAP.md). A *generated, read-only* browsable surface is a
  different question, and that one is on the roadmap.
- **Not a map or timeline generator.** Spatial and temporal anchors are in the
  model, and views can filter on them, but there is no cartography and no
  chronology rendering yet.
- **Not a continuity engine.** It will not detect that your king died twice
  (because maybe he did). Formal validation is formal; contradiction is a
  narrative observation you are free to ignore, and sometimes the contradiction
  is the point.
- **Not a predefined fantasy ontology.** There is no shipped model of races,
  classes, magic systems or kingdoms, and there are no genre templates yet.
- **Not an autonomous author.** It proposes; you dispose. It will not fill gaps
  you did not ask it to fill, and it will not resolve ambiguity you left on
  purpose.
- **Not a stable format yet.** See below.

---

## First-release status

This is an early release. It is functional and tested — the writer, viewer and
CLI suites run on every build, and the pipeline refuses to package a drifted
bundle — but it has been used by very few people on very few worlds.

Concretely, what that means for you:

- **The schema may evolve.** The kernel is at v0.19 and the capture spec at
  v0.13. Both have changed in response to real use, and both may change again.
- **There is no migration tooling yet.** If a future version changes how
  something is written, you may have to adjust files by hand.
- **Keep your worlds in git.** This is the honest mitigation, and it costs
  nothing: the canon is plain text, so a commit before a long session is a
  complete, cheap backup.

Supported hosts for this release are Claude and ChatGPT/Codex, on Windows.
The launchers for macOS and Linux exist in the bundle but are not yet verified,
so they are not claimed. See [INSTALLATION.md](INSTALLATION.md).

---

## Privacy

There is no server in this project, no telemetry, and no account. The canon is
a folder on your disk and nothing in the tooling sends it anywhere.

That is not the same as saying your worldbuilding is private. **Whatever you
say to the agent, and whatever it reads out of your canon, is processed by
whichever AI host you are running it through** — Anthropic or OpenAI — under
that vendor's terms, not this project's. If that matters for a particular
world, the files are just files: you can edit them without an agent at all.

---

## Where to go next

| you want to | read |
|---|---|
| build your first world | [GETTING-STARTED.md](GETTING-STARTED.md) |
| install or update it | [INSTALLATION.md](INSTALLATION.md) |
| know what to say to the agent day to day | [USER-GUIDE.md](USER-GUIDE.md) |
| get the picture you actually want | [VIEWS.md](VIEWS.md) |
| tune how often you are consulted | [CONFIGURATION.md](CONFIGURATION.md) |
| know the current boundaries | [LIMITATIONS.md](LIMITATIONS.md) |
| fix something that broke | [TROUBLESHOOTING.md](TROUBLESHOOTING.md) |
| know what is coming, and what never is | [ROADMAP.md](ROADMAP.md) |
| model something the hard way | `Specification/KERNEL.md` |
