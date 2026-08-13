---
id: types/separates
kind: type
name: Separates
applies_to_kind: relation
constraints:
  roles_required: [separator, side]
  role_kinds:
    separator: [entity]
    side: [entity]
lens:
  as: edge
  color: "#5f8fc9"
  line: dashed
  label: name
---
One place or object lies between two or more others.

