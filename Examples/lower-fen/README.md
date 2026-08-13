# The Lower Fen

A small worked canon — 16 artifacts and 12 relations — built to show what the
kernel does that a fixed-category tool cannot.

Wet country, a village on stilts, a tidewater town, and one brick bell tower
that two communities cannot agree about.

## What to look at

Open `views/the-bell-dispute.yaml`, which is the view worth seeing first.

**Places nest, two levels deep.** The Ford is inside Marrow Reach is inside the
Fen; the Bell Tower is inside Sallow Quay. Containment is a `part_of` relation,
not a field, so a place can be moved by editing one file.

**The disagreement is structure, not prose.** The Bell Wardens hold that the
bell rings for the drowned. The Rope holds that it is a tide signal and always
was. Neither doctrine is true or false — an idea's content asserts nothing —
but both exist, both are held, and an `opposes` relation ties them. Ask the
canon who believes what and it can answer, because belief was never written
into a paragraph.

**Conviction has a thickness.** The `holds` edges are weighted: the Wardens at
0.95, the Rope at 0.8, the fenfolk hedging at 0.4. The view scales edge width
by weight, so the strength of a belief is visible before you read a label.

**Things that happen are entities.** The Fever and the Crossing are typed
`action` and `action/practice`, drawn as hexagons because `types/action`
declares that lens — the shape lives in the canon, not in the renderer.

**One statement, one file.** Three places sit in the Fen, and that is one
`part_of` relation with three `part` members rather than three near-identical
files. It draws exactly the same picture — the same sixteen nodes and fourteen
edges — because a relation is one addressable statement, not one edge. Split it
only when the parts differ in something: a different date, a different source,
a link something else needs to point at.

## Reproducing it

```
wb view Examples/lower-fen --all-views -o lower-fen.html
wb validate Examples/lower-fen
```

Expected: 16 nodes, 14 edges, no warnings, and zero errors. The validator
counts 47 artifacts, because it counts everything in the folder: the 16 above,
the 12 relations that draw as edges rather than nodes, and 19 type definitions,
all but one of which came with the seed.
