# Composition acceptance world

A deliberately small world for reading, not for coverage. It demonstrates the
four things Phase 2 composition has to get right, and nothing else.

Render or inspect `views/composed-overview.yaml`:

```
view.py Testing/fixtures/composition-acceptance --view views/composed-overview.yaml --vendor -o out.html
view.py Testing/fixtures/composition-acceptance --validate-view views/composed-overview.yaml
view.py Testing/fixtures/composition-acceptance --explain-view views/composed-overview.yaml \
    --artifact entities/tomas-veyra
```

## What it demonstrates

**Composition.** One view combines four independently useful module kinds:
`selection`, `relation`, `style`, and `lens`. Each module is reusable on its
own and knows nothing about the others.

**Overlapping membership.** `entities/tomas-veyra` is chosen by both `people`
and `notable-figures`; `entities/merchants-guild` by both `organizations` and
`notable-figures`. The union in `any_of` then the intersection with
`active-subjects` in `all_of` resolve to one set with no duplicates, which
`--explain-view` will attribute to every contributing module.
`entities/pell-oarsman` is removed by `retired-figures`, and no later rule can
bring him back.

**Style precedence, property by property.** `base-palette` gives every person
a colour *and* a shape. `faction-palette` is declared after it and re-declares
only the colour. People end up with `faction-palette`'s colour and
`base-palette`'s shape, and the compiler emits an overlap warning naming both
sources, the property, and both values. That warning is expected output here,
not a defect.

**One resolved structural lens.** `nest-containment` and `flat-containment`
disagree about whether `part_of` draws as a nest or an edge. That is a
validation error on its own. The view resolves it with a local `lenses:` rule
naming the exact type `part_of`, so the view validates and the two communities
nest inside the free port. Delete that local rule and `--validate-view` fails
with `lens.structural-conflict`, and the render falls back with a prominent
`UNVALIDATED FALLBACK` warning.
