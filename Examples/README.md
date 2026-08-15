# Examples

Worked canons you can open, render and read. Each is a real folder — validate
it, view it, copy it and start editing.

If you want to create a world rather than inspect one, start with the
[five-minute walkthrough](../Documentation/GETTING-STARTED.md). The examples
are finished results, not mandatory templates.

---

## [The Lower Fen](lower-fen)

**31 world artifacts, 19 type definitions.** Wet low country, two settlements,
a ford, a crossing, a fever, and one brick bell tower that its communities
cannot agree about.

The one to look at first. It is small enough to read in full and deliberately
built to show several things a fixed-category tool cannot do:

- **places nested two levels deep** — containment is a relation, not a field
- **two rival doctrines as ideas**, tied by `opposes`, neither true nor false
- **a qualitative state** — the Fen is currently `flooded`, modeled with an
  approved `state/inundation` property type
- **a shared practice** connecting the bell watch, its performers, and its
  place without flattening that event into prose
- **weighted beliefs** that make strong conviction and hesitant adherence
  visibly different

It also demonstrates one thing the tooling asks for and models can miss:
Marrow Reach and Sallow Quay sit in the Fen as **one** multi-member `part_of`
statement, not two near-identical files. The Bell Tower has its own containment
statement because its whole is Sallow Quay.

```
wb view Examples/lower-fen --all-views --vendor --output lower-fen.html
wb validate Examples/lower-fen
```

Useful prompts after pointing an installed agent at this folder:

> What's in this world?

> Show me every saved view.

> Explain why the Bell Wardens and the Rope are drawn differently in the bell
> dispute view.

---

## What is not here yet

A ladder of examples, from a sixty-second first world to a full modelling
gallery, is the plan. What exists today is one world, because one honest worked
example is worth more than five sketched ones.

The modelling patterns that deserve their own examples, and do not have them:
membership and hierarchy together, state changing over time, relations that
target other relations, and a composed view built from modules. Some of these
are demonstrated in the test fixtures under
`Testing/fixtures/` — those are built to exercise the code rather than to be
read, but `composition-acceptance` is the working reference for view modules
until a proper example exists.

There are no genre templates. The kernel is domain-neutral, and shipping a
fantasy starter before the packaging that would let it be updated would be
handing you a fork to maintain. See [ROADMAP.md](../Documentation/ROADMAP.md).

Current coverage, stated plainly:

| need | available now |
|---|---|
| simple prompt → approval → view | the [Getting started](../Documentation/GETTING-STARTED.md) walkthrough |
| readable richer world and saved view | [The Lower Fen](lower-fen) |
| composed view modules | technical fixture in `Testing/fixtures/composition-acceptance` |
| complete conversation transcript | not yet |
| non-fantasy and cross-genre gallery | not yet |
