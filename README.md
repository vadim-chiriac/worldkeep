# Worldkeep

**Build a fictional world as structured canon. You write; an agent gives what
you wrote structure, proposing and never deciding; it lands in plain files you
own, and renders into graphs you can look at.**

Talk about your world however you like. Worldkeep turns the conversation into a
folder of Markdown and YAML artifacts, validates them, and draws them. Nothing
enters your canon without your approval, nothing leaves your disk, and every
file stays readable in a text editor long after any tool stops working.

![A rendered view of the Lower Fen: places nested inside the Fen, two rival
doctrines about what the bell is for, and an inspector panel showing the
selected doctrine's canon file and everyone who holds
it.](Documentation/assets/viewer.png)

*Two communities, one bell, no agreement — and the panel on the right answering
who believes what. Every node is a file you own.
([the world](Examples/lower-fen))*

There is no fixed taxonomy of races, realms or character sheets. There are four
kernel kinds and an open vocabulary you invent as you go. Which is why a
contested doctrine, a river with legal rights, and a famine that halves a
village over two centuries all fit without fighting a schema.

> **Early release.** Functional and tested, but young. The format may still
> change and there is no migration tooling yet — keep your worlds in git.

---

## Three ways to start

**Talk.** Point the agent at a folder and describe your world — as a writer, as
a worldbuilding nerd, or both on the same afternoon. It captures candidates as
drafts, presents them back as decisions rather than file lists, and writes
canon only when you approve.

**Write the files yourself.** A canon is a folder with a `world.yaml` and some
Markdown. Create artifacts by hand, run the validator, render a view. The agent
is a convenience, not a gatekeeper.

**Go further.** Define your own types with declared constraints and viewer
semantics, then compose reusable view modules — selection, relations, style,
lens — into exactly the picture you want.

---

## Five-minute start

Once the plugin is installed (see [INSTALLATION.md](Documentation/INSTALLATION.md)):

**1. Say what you want.** In Claude or Codex, point at a folder and start:

> Let's start a world in `Worlds/Hask`.

The scribe copies a seed world into place — the manifest, a starter type
library, and ready-made views — and asks what the world is called.

**2. Talk.** Describe a village, a feud, a doctrine, whatever is in your head.
At a natural pause the scribe shows you bundles:

```
Captured 11 artifacts in 3 bundles.

1. Marrow Reach, a fen village at the ford            — 2 files
2. The fever, and the village halving after it        — 5 files
     inferred: population modelled as two states (600 → 280)
3. Old Coll's ferry, and what it costs                — 4 files

ok · ok 1 3 · no 2 · 2: she's the ferryman's daughter · later 3 · show 2
```

**3. Approve.** `ok` promotes everything; `ok 1 3` promotes two bundles;
`no 2` deletes those drafts; plain text corrects them. Validation runs on
every change.

**4. Look at it.**

> Show me my world.

You get self-contained HTML (one file, no network) that opens in any
browser. Ask for something narrower ("just who rules what", "only the religious
conflicts") and the agent writes a view for it.

---

## Why these four kinds

Most worldbuilding tools start from a list of things a world contains, and
you spend your time deciding which box a thing goes in. Worldkeep starts
somewhere else: **connection is the primary fact.** A person is interesting
because of who they answer to and what they believe; a river matters because
of what it separates and who crosses it. So relations are not links between
the real content — they *are* content, each one its own addressable file.

Push that far enough and the things themselves dissolve. A person is a
network of organs, which are networks of cells, which are networks further
down. Nothing is atomic; anything can be opened. But a tool that insisted on
that would be unusable, because you would never be allowed to just write
*a person*.

So the kernel does the honest thing and stops where you stop. An **entity** is
a network nobody has needed to open yet — it is not a claim that the thing is
simple, only that it hasn't been decomposed. When you do want to open it, you
don't convert it into something else: you write `part_of` relations and its
inner network appears beneath it. Decomposition is a thing you do later,
without permission, without migration.

**Entities and ideas could have been one kind.** They are kept apart for a
single reason worth the cost: an entity asserts that something *is*, and an
idea asserts only that somebody has the thought. Write `entities/tharos` and
the god exists in your world. Write `ideas/tharos` and only the belief does —
believers can `holds` it, a real temple can be dedicated to it, rival accounts
can contradict it, and none of that makes the god real. Fact and belief are the
distinction the kernel is willing to spend a kind on. It is not willing to
spend one on anything else: there used to be a fifth for *things that happen*,
and it was retired once it turned out the kernel never treated happening
differently.

An idea does not need a believer, either. A holderless idea is a dormant
concept — an unread book, a doctrine everyone forgot — which is a state your
world is allowed to be in permanently.

The fourth kind, **type**, is just vocabulary: the categories you invent,
written down as artifacts like everything else, so that what a `guild` or a
`heresy` means in your world lives in your world rather than in the tool.

For the full argument, including which distinctions were rejected and why, see
[OVERVIEW.md](Documentation/OVERVIEW.md) and `Specification/KERNEL.md`.

---

## What it looks like under the hood

```
Worlds/Hask/
  world.yaml           the manifest
  scribe.yaml          agent configuration
  entities/            e.g. people, places, institutions, objects, gods
  ideas/               e.g. doctrines, theories, rumours
  actions/             events and recurring practices (a type, not a kind)
  relations/           connections — each one its own addressable file
  types/               the vocabulary this world invented
  views/               saved interpretations for the viewer
```

Folders are for you; `kind:` is what the tooling reads. `actions/` is the one
named after a type rather than a kind — a convenience shipped by default,
because "where did I put the siege" is a question people actually ask.

```markdown
---
id: entities/marrow-reach
kind: entity
type: place/village
name: Marrow Reach
where: entities/the-fen
status: canon
---
A fen village at the ford, half of it on stilts.
```

---

## Supported hosts

| host | status |
|---|---|
| Claude Desktop / Claude Code (Windows) | supported |
| Codex / ChatGPT Work (Windows) | supported |

macOS and Linux launchers ship in the bundle and nothing in the code is
Windows-specific, but the pipeline has not been run end to end on either, so
neither is claimed. If you try it there, the result is worth reporting.

---

## Documentation

| | |
|---|---|
| [Overview](Documentation/OVERVIEW.md) | what it is, why it is shaped this way, what it is not |
| [Getting started](Documentation/GETTING-STARTED.md) | first world, from prompt to approved canon |
| [Installation](Documentation/INSTALLATION.md) | per-host install, updating, uninstalling |
| [User guide](Documentation/USER-GUIDE.md) | capture, approval, editing, validation |
| [Views](Documentation/VIEWS.md) | `Everything`, filters, custom views, modules |
| [Configuration](Documentation/CONFIGURATION.md) | `scribe.yaml`, manifests, viewer options |
| [Troubleshooting](Documentation/TROUBLESHOOTING.md) | when something does not work |
| [Limitations](Documentation/LIMITATIONS.md) | current boundaries, honestly stated |
| [Roadmap](Documentation/ROADMAP.md) | what is next, without promised dates |
| [Development](Documentation/DEVELOPMENT.md) | building, testing, contributing |
| [Release notes](Documentation/RELEASE-NOTES.md) | what 0.2.0 is, in prose |

The normative specifications live in `Specification/`: **KERNEL.md** is the data
model, **SCRIBE.md** is the capture loop. Both ship verbatim inside the plugin,
so the agent reads the same text you do.

Example worlds are in [`Examples/`](Examples/).

---

## Licence

Worldkeep is released under the [MIT licence](LICENSE) — use it, change it,
build on it, commercially or not.

Bundled third-party components keep their own licences, all likewise MIT; see
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
