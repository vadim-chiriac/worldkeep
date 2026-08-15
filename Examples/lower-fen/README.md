# The Lower Fen

A small current Worldkeep canon: 31 world artifacts plus 19 type definitions.
It is deliberately compact enough to read file by file while exercising the
same structures used by larger worlds.

Wet low country contains two settlements, a ford, a deep channel, and a bell
tower. Its communities disagree about what the bell means and whether a fever
was judgement; people keep the bell watch and work the Crossing.

## What to look at

Open `views/the-bell-dispute.yaml` first. Its validated projection contains 18
nodes and 17 edges, with no warnings.

- **One shared containment statement.** Marrow Reach and Sallow Quay are both
  parts of the Fen in one multi-member `part_of` relation. The Bell Tower is
  separately part of Sallow Quay because that fact has a different whole.
- **A qualitative state.** `state/inundation` records that the Fen is currently
  `flooded`; the property type was proposed and approved with the canon.
- **Ideas remain first-class.** The two doctrines about the bell are connected
  by `opposes`, while `holds` records who believes each one and how strongly.
- **Several readable threads coexist.** The Fever, Crossing, Fenfolk, and
  Harbormistress add connected sub-stories without making the graph large.
- **A shared practice.** The bell watch is an `action/practice` with the Wardens
  as performer and the Bell Tower as place.
- **A durable custom view.** The saved YAML selects only the relation types
  needed for this reading. `Everything` remains the neutral audit graph.

## Reproducing it

```text
wb validate Examples/lower-fen
wb view Examples/lower-fen --all-views --vendor --output lower-fen.html
```

Expected validation: 50 artifacts, zero errors, zero warnings and zero notices.
The total includes 31 world artifacts and 19 type definitions.
