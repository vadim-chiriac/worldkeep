---
id: types/holds
kind: type
name: Holds
applies_to_kind: relation
constraints:
  roles_required: [holder, held]
  role_kinds: { held: [idea] }
---
An entity holds an idea. Weight on the holder member = strength of
conviction. Perspective, belief, doctrine adhesion — all this one type.
