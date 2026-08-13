---
id: types/precedes
kind: type
name: Precedes
applies_to_kind: relation
constraints:
  roles_required: [earlier, later]
---
Temporal order between two artifacts that occupy time — periods, actions,
states. Ordering is derived by topological sort over these relations;
numeric `when.sort` is an optional override for worlds with a calendar.
