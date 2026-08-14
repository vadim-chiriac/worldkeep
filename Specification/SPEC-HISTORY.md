# Specification history

Historical changelog for `KERNEL.md` and `SCRIBE.md`. This document is
informational and is not bundled with the runtime skills. The current,
normative specifications are `KERNEL.md` and `SCRIBE.md`; future release notes
belong here rather than in their runtime preambles.

## KERNEL

### v0.18

Added qualitative one-member state values. `value` is now a standardized,
non-empty string facet only for one-member `state` relations; numeric
magnitudes remain `amount`. A property stays in the type path, so
`state/exploration` can move between `explored` and `unexplored` without
splitting its `(subject, type)` series.

### v0.17

Retired the `action` kind, leaving four: `entity`, `idea`, `relation`, `type`.
Things that happen are now `kind: entity` with the std type `action`, and
recurrent ones `action/practice`, which replace the former `instance` and
`practice` roots.

Applying §3's own kernel-mechanics test — a distinction earns a kind only if
kernel rules treat it differently — `action` failed. `when` and `where` are
open to every artifact; periods were already entities despite occupying time,
which made the old split between a period entity and an action kind an
inconsistency rather than a principle; and the instance/practice distinction
was delegated to types from the beginning. Its one mechanical claim was that
`participates` binds a real event, expressed as `role_kinds: {action: [action]}`.

That claim is preserved by a new constraint, `role_types`, which pins a role to
a type path and is satisfied by any descendant of it, exactly as type paths
behave elsewhere. The viewer's hard-coded hexagon and colour for actions moved
into a `lens:` on `types/action`, which is where a visual belongs; `practice`
is now detected by the type path rather than by a kind plus a type.

`idea` was examined at the same time and kept. §5 carves out exactly one
exception in the whole kernel — an idea's *content* asserts nothing about the
world — and that rule cannot be stated about a type without making kernel
semantics depend on open vocabulary anyone may redefine, inverting §1.1.

The validator reports the retired kind by name and states the replacement,
which is the only migration aid that exists; there is no migration tooling yet.


### v0.16

Corrected the standard visual direction of `subordinate_to` to `subordinate`
→ `superior`, and made explicitly rendered `part_of` links point `part` →
`whole`. Custom `part_of` views still use unarrowed nesting; this was a
presentation-only semantic correction and changed no canon facts.

### v0.15

Relation lenses may declare presentation-only direction as `direction:
[source_role, target_role]`. The viewer projects and marks directed relations
from those declared roles, never from member-list or `roles_required` order.
This changed no canon semantics.

### v0.14

`part_of` now expresses one whole with one or more parts in a single relation
artifact; binary inclusion remains valid. Formal `roles_unique` constraints
make the whole (and a `participates` action) unique, inherit down type paths,
and remain fiat-aware. A relation is one addressable statement, not
necessarily one rendered edge.

### v0.13

Removed the `rank` and `group` presentation behaviors. Both hid their relation
and delegated its meaning to layout behavior that varied by renderer. The
first two worlds built from the same paragraph rendered with 18 visible edges
and 0 respectively, the difference being entirely that one typed its
relations `subordinate_to`. `subordinate_to` kept its meaning; hierarchy
orientation became a property of the view layout. Membership now draws a
normal edge. A type declaring `as: rank` or `as: group` degrades to `edge` and
warns like any unknown behavior.

### v0.12

Made the §8 lens a structured block with a worked example rather than allowing
a named lens. The first live world interpreted the old wording literally,
wrote `lens: chain_of_command`, and exposed the nonexistent implied registry.

### v0.11

Removed ceremony without adding expressive power: `when` may anchor to any
time-bearing artifact, and a type is defined when any ancestor on its path has
a file. Children inherit constraints, so a leaf file is needed only when it
adds something.

### v0.10

Added property-typed states (`state/population`), with series identity defined
by `(subject, type)`; added standard `precedes` so ordering can be derived
topologically; and made the world's present a named period in `world.yaml`
rather than the floating string `"now"`.

### v0.9

Added one-member `state` relations for changing scalar properties. `amount`
may be a list and gained optional `of:` for proportions. Clarified fiat
non-contagion, added worked examples for esotericism and content composition,
and settled that children inherit type constraints and may tighten but never
loosen them.

### v0.8

Added narrator law entities, the contested-versus-fiat distinction,
world-level decrees as law entities with `fiat: true`, `amount` on any
artifact, standard `period`, and the rule that `when` points at the innermost
period while nesting lives in `part_of`.

### v0.7

Added standard `participates` after live testing exposed that agent-to-action
links lacked a standard expression. Role vocabulary remained free and actions
remained a kind, allowing participantless events.

### v0.6

Closed kinds for everyone; demoted `associated` from type to inferred fact;
replaced `from`/`to` with `members`; removed the `composite` facet; added
`fiat`; refined the truth model; and named the compositional properties place,
period, amount, and content.

### v0.5 to v0.2

v0.5 introduced the flat ontology and networks/zoom. v0.4 added the
`associated` root, `idea`, `action`, and composites. v0.3 added perspective via
`holds`, the standard library, and `weight`. v0.2 added beliefs and ambiguity
as a principle.

## SCRIBE

### v0.12

Added computed approval-batch accounting through the optional
`wb.capture/v1` envelope. Bundle membership is checked before writing, and the
post-capture report derives structural counts from the artifacts actually
written. For long source passages, the approval summary now distinguishes
material captured structurally, retained only in prose, and deferred or
omitted.

### v0.11

Clarified capture of qualitative mutable properties: reuse or propose a
property type such as `state/exploration`, then write its reading in
top-level `value`; never encode the reading as a descendant type.

### v0.10

Made the multi-member relation the **default** rather than a permitted option.
Two or more links that share a type, share a member in the same role, and
differ in nothing else are one relation with several members; splitting is now
the exception, reserved for links that genuinely differ in time, status,
provenance, description, or addressability.

The change is a correction for a measured bias rather than a change of model —
the kernel always allowed this. Splitting is always legal, so a scribe weighing
an uncertain condition splits every time, and every graph formalism in a
model's training is binary. Stating the merge as the default counteracts both.
`wb` now reports the groups left behind after a capture, so the instruction has
a deterministic backstop instead of relying on the scribe noticing.


### v0.9

Changed the default type policy to `ask`. Reuse remains mandatory and untyped
remains valid; the scribe proposes new vocabulary only when a type earns its
file, and the author decides whether to add it. `existing_only` remains an
explicit setting.

### v0.8

Added five independent author-facing settings with no presets or hidden
overrides. The scribe reports effective settings at session start. Type policy
became reuse-first, validation became mandatory after every complete mutation
batch, and provenance/spec-loading switches left author configuration.

### v0.7

Clarified that a relation is one addressable statement, not necessarily one
edge. Shared inclusion uses one whole and all stated parts in one `part_of`;
claims split when their time, status, source, description, or other
relation-level facets differ.

### v0.6

Added `scribe.yaml` configuration and a single apply script. This let authors
choose consultation frequency and collapsed per-batch tool traffic from about
`2N` calls to two.

### v0.5

Replaced file-resolution batches with semantic bundles, made invention and
inference visible, removed the candidate-count trigger, affirmed untyped as a
valid default, required a new type to earn its file, and kept validation quiet
when clean.

### v0.4 and v0.4.1

Unified the write cycle: eager candidates become drafts in the proposing turn;
the reply turn first promotes approvals; batch lines bind files; `DELETE` and
`REFINE` were added; and validators are run rather than simulated. v0.4.1 made
TYPE items explicitly subject to eager capture.

### v0.3

Made the approval gate literal, distinguished rejection from deprecation,
treated modeling corrections as edits, required a TYPE item on first use of a
non-standard type, prioritized referent ambiguity questions, and defaulted
provenance to `mixed`.

### v0.2

Realigned to Kernel v0.6: claims became idea artifacts plus `holds` relations;
`members` replaced `from`/`to`; `opposes` replaced `in_conflict`;
`according_to` became perspective through `holds`; bare connections became
legitimate output; and fiat handling was added.

### v0.1

Initial conversation-to-canon loop, diff batches, type policy, and provenance
extension.
