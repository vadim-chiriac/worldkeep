# Limitations

What this does not do, what it does badly, and what will probably bite you.
Everything here is a current boundary rather than a criticism of the design;
the things that are *deliberate* absences live in
[ROADMAP.md](ROADMAP.md#non-goals) instead.

This document is written to be believed rather than to reassure. If it turns
out to be understating something, that is a bug in the document.

> **Before you begin:** the format is young and there is no migration tool.
> Keep each world in git and commit before upgrades or large editing sessions.
> That turns an incompatible change into a visible diff you can reverse.

---

## The format is young and there is no migration tooling

This is the one that can actually cost you work.

The kernel is at v0.17 and the capture specification at v0.10. Both have
changed in response to real use, several times, and both may change again. Two
of those changes have been breaking within the last week of development: a
whole kind was retired, and the meaning of a lens key was widened.

**Nothing migrates a world from one version to the next.** When a rule changes,
the tooling tells you — the validator names a retired kind and states its
replacement, and the session report warns when a world's declared
`kernel_version` has fallen behind the packaged one — but it will not rewrite
your files, and neither will anything else.

The mitigation is git, and it is genuinely adequate rather than a fig leaf: the
canon is plain text, a commit is a complete snapshot, and a diff shows exactly
what a change did. But it is a mitigation, not a solution, and calling this
format stable would be a lie until migration tooling exists.

## It has barely been used

By very few people, on very few worlds, most of them built to test something.
The test suites are thorough about the things somebody thought to test; the
number of hours of ordinary use behind this is small.

Concretely, the bugs found in a single week of writing this documentation
included: a default view that selected a kind which no longer existed and so
silently excluded every belief in your world; a layout typo that validated
clean and quietly drew a different picture; nesting that collapsed into an
unreadable row on any world with a hierarchy; and thirty warnings fired at a
user for files they had never touched. All were in shipped code. None were
caught by tests, because all of them required somebody to look at the result
and say "that is not right".

Expect more of that.

## Windows only, in practice

Nothing in the code is Windows-specific and the macOS and Linux launchers ship
in the bundle. The pipeline has never been run end to end on either, so neither
is claimed. This is missing verification rather than missing capability, but an
unverified claim is worth nothing to you.

---

## What it will not do for you

### It will not tell you your world makes sense

Validation is formal and only formal: duplicate ids, dangling references,
missing kinds, empty relations, and the constraints your own type files
declare. It will not notice that your king died twice, that a battle happens
before the war it belongs to, or that two doctrines flatly contradict.

That is a decision, not an oversight — contested history and deliberate
ambiguity are content — but it does mean the validator passing tells you your
*files* are well-formed, and nothing at all about your *world*.

### It will not draw a map or a timeline

`where` and `when` are in the model and views can filter on them. There is no
cartography and no chronology rendering. `when` gives you ordering through
`precedes`, and ordering is not a timeline.

### It will not find things you have not asked about

There is no "your world has no religion" prompt, no completeness score, no
suggestion engine. Incompleteness is a supported permanent state, and a tool
that nagged would be arguing with that.

---

## Where it gets awkward

### Large worlds

The viewer is comfortable at the scale anything has been tested at — a few
hundred artifacts. Beyond that, expect the *picture* to become unreadable
before the tooling becomes slow: a graph of two thousand nodes is a texture,
not a diagram. Views and filters are the answer, which means large worlds
require you to know what you are asking rather than looking at everything.

Rendering itself was slow on nested graphs until recently, and the fix was to
drop edges during interaction on graphs of sixty edges or more. If you notice
edges vanishing while you drag, that is the trade, and it is deliberate.

### Composed views

Composition is powerful and unforgiving. A view assembled from six modules can
produce a picture whose reason is genuinely hard to reconstruct — which is why
`wb explain` exists at all, and why a locking mechanism exists to tell you when
the modules underneath a view have moved.

If you are composing modules and cannot tell why something is coloured the way
it is, that is not you being slow. Ask `wb explain` about the artifact; it will
name the module and the rule index.

### Very long sessions

The agent holds the conversation, and the conversation is finite. In a long
session, ask for a bundle at natural pauses rather than talking for an hour —
not because anything is lost (drafts are written to disk immediately, including
if the session dies) but because a review of eighty artifacts is a worse review
than four reviews of twenty.

### Provenance in mixed worlds

If a world contains any artifact the agent stamped, the validator will note
every artifact without a stamp. Hand-write a world, capture one thing into it,
and you will be told about all the files you wrote yourself. It is one summary
line rather than one per file, and it is a note about mixed authorship rather
than a fault — but it is noise, and it comes from an all-or-nothing flag with
no middle setting.

---

## Privacy, precisely

There is no server, no telemetry and no account, and nothing in the tooling
sends your canon anywhere.

That is not the same as your worldbuilding being private. **Everything you say
to the agent, and everything it reads out of your canon to answer you, is
processed by whichever AI host you run it through** — Anthropic or OpenAI —
under that vendor's terms, not this project's.

If that matters for a particular world, the files are just files. You can write
and edit a canon with no agent involved at all; the validator and the viewer
are local scripts.

---

## Reporting something

The useful bug report says which host and OS, the plugin version, what you
asked for, and what happened instead. If a canon is involved, the output of
`wb session` and `wb validate` on it is usually enough to reconstruct the
state, and both are safe to paste — they report structure and counts, not the
contents of your world.
