# Examples

Worked canons you can open, render and read. Each is a real folder — validate
it, view it, copy it and start editing.

If you want to create a world rather than inspect one, start with the
[five-minute walkthrough](../Documentation/GETTING-STARTED.md). The examples
are finished results, not mandatory templates.

---

## [The Lower Fen](lower-fen)

**16 artifacts, 12 relations.** Wet country, a village on stilts, a tidewater
town, and one brick bell tower that two communities cannot agree about.

The one to look at first, and the source of the screenshot in the project
README. It is small enough to read in full and deliberately built to show the
four things a fixed-category tool cannot do:

- **places nested two levels deep** — containment is a relation, not a field
- **two rival doctrines as ideas**, tied by `opposes`, neither true nor false
- **`holds` edges weighted by conviction** — 0.95 for the Wardens, 0.4 for the
  fenfolk hedging, and the view draws that as thickness
- **an action drawn as a hexagon** because its type declares the lens, so the
  shape lives in the canon rather than in the renderer

It also demonstrates one thing the tooling asks for and most models resist:
three places sit in the Fen as **one** `part_of` relation with three `part`
members, not three near-identical files. It draws exactly the same picture.

```
wb view Examples/lower-fen --all-views -o lower-fen.html
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
contested belief with rival holders, membership and hierarchy together, state
changing over time, relations that target other relations, and a composed view
built from modules. Some of these are demonstrated in the test fixtures under
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
