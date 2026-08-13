---
id: types/participates
kind: type
name: Participates
applies_to_kind: relation
constraints:
  roles_required: [action]
  roles_unique: [action]
  role_types: { action: [action] }
---
Binds participants to an action. One member carries role `action` and must
be typed `action` or a descendant of it; all other roles are free
vocabulary — `performer`, `target`, `instrument`, `witness`, … Agency is a
role, not a type: whether something acts or is acted upon is stated
per-member, per the flat ontology. Several participants bundle into one
file; `weight` per member = degree of involvement.
