# Worldkeep 0.3.0 — a more usable viewer and safer capture loop

Worldkeep turns worldbuilding conversation into structured canon: plain
Markdown and YAML files you own, written by an agent that proposes and never
decides, and rendered into graphs you can inspect.

This remains an early release. It is functional and tested, but the format is
young, migration tooling does not exist yet, and the macOS/Linux pipeline has
not been tested end to end. Keep worlds in git and review the actual canon
before approving changes.

## What changed since 0.2.0

### A clearer viewer

- Relation details are grouped into readable member-and-role cards.
- One-hop relation and neighbourhood focus make dense graphs easier to inspect.
- The legend is generated from the marks currently shown and stays collapsed
  until needed.
- Qualitative and numeric state values render correctly, including ranges.
- The default Groups view prunes unrelated artifacts.
- View validation reports deterministic style-rule match counts and useful
  non-blocking notices.

Custom views remain interpretations, not automatic truth. Ask for the reading
you want, inspect the preview, compare it with `Everything`, and refine it
before saving. `Everything` is a neutral audit baseline: it ignores custom
selection, styles, and lenses, can become crowded, and its filters are temporary
for the current browser session. It helps reveal omissions; it is not expected
to be the clearest view of a world.

See [VIEWER-GUIDE.md](VIEWER-GUIDE.md) and [VIEWS.md](VIEWS.md).

### Safer capture and review

- Approval-batch envelopes require every artifact to belong to exactly one
  semantic bundle before writing.
- Successful captures report structural counts, relation shapes, new types,
  and reclassifications.
- Disconnected entities and ideas receive a non-blocking notice.
- Merge suggestions respect provenance, descriptions, custom fields, and
  unreadable relation bodies.
- Relation modelling distinguishes correspondence-sensitive claims from
  higher-order grouped relations and warns about repeated endpoint roles.

A clean validation result means the files are structurally consistent. It does
not mean the agent understood every relationship as intended. Correct and
refine proposed canon before approval.

### Current specifications and examples

Qualitative one-member states use a structured top-level `value`; numeric
states use `amount`. The current public specifications are KERNEL v0.19 and
SCRIBE v0.13, and the seed world is aligned with them.

The release also includes an illustrated viewer guide, clearer onboarding and
an expanded Lower Fen example with 31 approved world artifacts, weighted
beliefs, qualitative inundation state, shared containment, and a richer dispute
view.

### Distribution

The plugin identity is consistently `worldkeep` across Claude and
ChatGPT/Codex. The public
[vadim-chiriac/worldkeep repository](https://github.com/vadim-chiriac/worldkeep)
contains both host manifests and the two skills:

- Worldbuilding Scribe;
- Canon Viewer.

## What it is not

Worldkeep is not a writing application, continuity engine, predefined fantasy
ontology, map generator, or autonomous author. It stores structure, keeps the
canon local, and gives an agent a controlled way to propose changes.

## Before you rely on it

There is no automatic migration path. The project has been used on only a small
number of worlds, and manual inspection has found issues that automated tests
did not catch. Treat a generated view as a way to inspect canon, not as proof
that the canon is complete or semantically correct.

There is no Worldkeep server or telemetry, but conversation is still processed
by whichever AI host you use. The local files, validator, and viewer can be
used independently of an agent.

MIT licensed.
