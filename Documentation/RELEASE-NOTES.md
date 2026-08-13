# Worldkeep 0.2.0 — first public release

Worldkeep turns worldbuilding conversation into structured canon: plain
Markdown and YAML files you own, written by an agent that proposes and never
decides, and rendered into graphs you can look at.

This is the first version anyone other than its author is meant to try.

---

## What it is for

Two kinds of tool already exist, and both are frustrating in opposite
directions.

Prose notes let you write anything and find nothing. There is no way to ask a
folder of Markdown *who currently rules what*, because nothing in it separates
a ruler from a sentence containing the word "rules".

Worldbuilding databases can answer that, because they decided in advance what a
world contains — character, location, organization, item. Most let you add
custom fields, and some let you write templates. But the categories stay the
frame: you are adding fields to a Character, not deciding whether "character"
is a useful distinction in your setting. And customising is something you stop
and go configure, which means you only do it once the friction has already
become annoying enough to interrupt you.

Worldkeep aims between the two. Four kernel kinds — entity, idea, relation,
type — and everything above them is vocabulary you invent while talking. A type
is a small file the agent writes mid-sentence, the first time you say a word it
has not heard before.

That is what lets a contested doctrine, a river with legal rights, and a famine
that halves a village over two centuries all fit without anyone touching a
schema.

## What is different about it

**Connections are the content.** A relation is its own addressable file, which
means a relation can be the subject of another relation, or of an idea. Secrecy,
disputed histories, and beliefs about beliefs fall out of that one property
rather than out of dedicated features.

**Belief and fact are separate.** An entity asserts that something exists. An
idea asserts only that somebody has the thought. Write `entities/tharos` and
the god is in your world; write `ideas/tharos` and only the belief is —
believers can hold it, a real temple can be dedicated to it, and none of it
makes the god real.

**Nothing is decomposed until you decompose it.** An entity is a network nobody
has needed to open yet, not a claim that a thing is simple. When you want to
open one, you write `part_of` relations and its inner network appears. No
migration, no conversion, no permission.

**Incompleteness is a supported state.** Loose ends, dormant ideas, connections
with no stated meaning: content, not a backlog. Nothing nags.

**You approve decisions, not files.** The agent captures everything it hears as
drafts immediately — a session that dies loses nothing — and presents them back
as the things you said, with the file count as a footnote. What it inferred or
invented is named in the bundle that contains it.

**It is local, and it is yours.** No server, no account, no telemetry. The
canon is a folder. Rendered views are single self-contained HTML files that
open with no network, now and in ten years.

## What is in this release

Two skills in one plugin, for Claude and for ChatGPT/Codex.

The **scribe** runs the conversation-to-canon loop and owns the writing: a
deterministic apply-and-validate boundary that stamps provenance, runs the
validator, and reports exactly which files it touched.

The **viewer** turns "show me who rules what" into a saved view and renders it.
Views select, filter, style and structure; when the same concern keeps
recurring you lift it into a reusable module and compose views from modules.
`Everything` is always there as a neutral audit that ignores everything you
have configured, for checking what is actually in the folder.

The full documentation set ships with it: an overview, a five-minute start,
per-host installation, a user guide, views, configuration, troubleshooting, and
an honest account of the current limitations.

## What it is not

Not a writing application — it stores structure; your prose lives where you
like writing it. Not a map or timeline generator. Not a continuity engine: it
will not notice your king died twice, because sometimes that is the point. Not
a predefined fantasy ontology, and there are no genre templates. Not an
autonomous author.

## Before you rely on it

**The format is young and nothing migrates it.** The kernel is at v0.18 and has
changed several times, twice breakingly in the week before this release. When a
rule changes the tooling tells you — it will not rewrite your files. Keep your
worlds in git; the canon is plain text, so a commit is a complete snapshot and
a diff shows exactly what happened.

**It has barely been used.** By very few people, on very few worlds. Writing
this documentation turned up four bugs in already-shipped code, none of which
the test suites caught, because all of them needed somebody to look at a result
and say "that is not right". Expect more.

**Windows only, in practice.** Nothing in the code is Windows-specific and the
macOS and Linux launchers ship, but the pipeline has never been run end to end
on either, so neither is claimed.

**Privacy, precisely.** There is no server and nothing here sends your canon
anywhere. That is not the same as your worldbuilding being private: everything
you say to the agent is processed by whichever AI host you run it through,
under that vendor's terms. If it matters for a particular world, the files are
just files — the validator and the viewer are local scripts, and you can work
without an agent at all.

---

## Getting started

Install per [INSTALLATION.md](INSTALLATION.md), then point the agent at a
folder and start talking. [GETTING-STARTED.md](GETTING-STARTED.md) walks a
first world from prompt to rendered view.

[`Examples/lower-fen`](../Examples/lower-fen) is sixteen artifacts you can read
in full: a village on stilts, a tidewater town, and one bell tower two
communities cannot agree about.

MIT licensed. The reports worth making most are the ones where nothing failed
and the result was quietly wrong.
