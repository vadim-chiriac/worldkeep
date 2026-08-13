---
id: types/period
kind: type
name: Period
applies_to_kind: entity
---
A span of time as an entity — era, reign, season, siege. `when` anchors
point at the innermost applicable period; periods nest via `part_of`
(child period as `part`, parent as `whole`) — never via the anchor.
