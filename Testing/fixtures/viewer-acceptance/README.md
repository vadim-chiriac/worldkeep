# Viewer acceptance world

This compact world exercises every current Viewer graph behavior in one
file: one-whole/two-parts containment, visible membership, hidden temporal order, a state chip,
a reified n-ary relation, a relation targeted by another relation, dormant and
held ideas, instance and practice actions, draft opacity, and a fiat mark.

The world also carries `subordinate_to` relations. Until KERNEL v0.13 those
exercised a sixth behavior, `rank` (no line, layout constraint only); that
behavior is gone and they now draw as ordinary directed edges. KERNEL v0.16
uses their `subordinate`/`superior` roles for endpoint order and target
arrowheads, so the arrow points from the subordinate toward the superior.

Render `views/all-behaviors.yaml` with `src/viewer/view.py`.
For the subordinate-first dagre acceptance fixture without the opposing
membership edge, render `views/07-direction-hierarchy.yaml`.
