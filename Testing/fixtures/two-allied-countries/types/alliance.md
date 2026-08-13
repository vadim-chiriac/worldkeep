---
id: types/alliance
kind: type
name: Alliance
applies_to_kind: relation
constraints:
  roles_required: [ally]
  role_kinds:
    ally: [entity]
lens:
  as: edge
  color: "#78a96b"
  width: weight
  label: name
---
A cooperative relationship between political entities.

