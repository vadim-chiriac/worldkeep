---
id: types/state
kind: type
name: State
applies_to_kind: relation
constraints:
  roles_required: [subject]
---
A one-member relation: a fact about its member, carried by `when`, numeric
`amount` or qualitative `value`, and `valence`. The home of every mutable
property — populations, sizes, exploration status, prices-of-the-day.
Specialize by property; for example `state/exploration` carries
`value: unexplored`, rather than using `state/unexplored`. Lenses may chart a
subject's states as a series.
