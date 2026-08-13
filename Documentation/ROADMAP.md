# Roadmap

Themes, not dates. This is a project built for its own use, so the order below
reflects what would be most useful next rather than a schedule anyone is
committed to.

Anything here may be reordered or dropped. The only firm statements in this
document are the non-goals at the bottom.

---

## Now

**Release documentation.** The specifications have been readable for a while;
the user-facing documents have not. Most of what is missing is written, and
what remains is listed in the README's documentation table.

**Installation hardening.** The launcher resolves a Python runtime by probing
known locations, and its failure message is the first thing a new user sees
when it does not find one.

**Diagnostics.** `wb doctor` reports what the tooling found and what it did
not. Every failure that has cost real time so far should be answerable by
running it once.

---

## Next

**Migration tooling.** The format is at kernel v0.17 and has changed several
times, each time by hand. Nothing migrates a world from one version to the
next, and "keep it in git" is honest advice rather than a solution. This is the
single largest gap between the current state and one where the format can be
called stable.

**Generated legends.** A rendered view explains its relation behaviours but not
its colours: a world that recolours by faction produces a picture only its
author can read. The information is in the compiled plan already.

**Better help writing views.** Composition is powerful and unforgiving —
`--explain-view` exists because it had to. The gap is between validating a view
you wrote and being helped to write it.

**A reading surface.** Something browsable generated from a canon: linked
pages, an artifact and its connections, readable by someone who is not running
the tooling. This is the "wiki" question, and the honest version of it is a
*generated, read-only* surface rather than a place you write.

---

## Later

**Shareable type and view packages.** A world's vocabulary is a file library;
there is no reason it cannot be published, borrowed and versioned like any
other dependency. This is what would make a genre template meaningful rather
than a folder someone copies.

**Template families.** A starting vocabulary for a fantasy polity, a
science-fiction system, a real-world administrative structure. Deliberately
after packaging, because a template that cannot be updated is a fork you
inherited.

**Derived semantic inference.** Rules a world declares explicitly and a tool
then applies: belief inherited down a `part_of` chain, authority inherited
down a command chain. Declared, never assumed; see the non-goals.

---

## Exploring

No commitment, no design, and possibly no good answer.

**Maps.** `where` anchors are already in the model and compose up a places
chain, so the data is there. What is missing is any notion of coordinates, and
inventing one badly would be worse than not having one.

**Timelines.** The same shape of problem: `when` and `precedes` give ordering,
and ordering is not a chronology until someone decides what to do with a world
that has no calendar.

**Cached projections.** Rendering is fast until a canon is very large. Nobody
has hit that wall yet, which is the only reason this is here rather than in
Next.

---

## Non-goals

These are not "not yet". They are decisions.

**Replacing your prose editor.** Worldkeep stores structure. Your prose lives
wherever you like writing it, including in artifact bodies, and nothing here
will grow into a word processor.

**Inferring canon silently.** The agent proposes; you approve. A tool that
quietly decided things would be faster and would cost you the one property that
makes the canon worth keeping — that everything in it is there because you said
so.

**Enforcing one universal ontology.** No shipped model of races, classes or
kingdoms. The standard type library is a set of useful defaults, and a world
that ignores all of it is a supported world.

**Resolving your contradictions.** Formal validation stays formal. Contested
history, deliberate ambiguity and loose ends are content; a tool that tidied
them away would be deleting the interesting part.

---

Something you want that is not here is worth saying out loud — this list is
short because it is one person's guess about what matters.
