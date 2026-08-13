"""Find relations that say one thing in several files.

The kernel permits a relation to carry many members, and the scribe is told to
use one when the facets, provenance and description apply to every member.
Models rarely do: almost every graph formalism they were trained on is binary,
and the rule is a permission with a condition attached, so splitting is the
choice that can never be wrong. Prose has not moved that prior, so this reports
the shape instead.

A notice, never an error. Splitting is legal, sometimes deliberate, and the
author is the one who decides. The point is only that they should be told the
option exists when nothing distinguishes the parts.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Iterable

#: Relation-level facets that must match before a merge can be suggested.
FACETS = ("when", "where", "valence", "weight", "status", "amount", "value", "fiat")

#: Provenance, compared as strictly as any facet. SCRIBE §2 names it among the
#: things that make two links different statements, and it is exactly what
#: differs between a link the author wrote and one the scribe inferred in some
#: other session — which is the pair a merge would silently flatten.
PROVENANCE = ("scribe.origin", "scribe.session")

#: SCRIBE says "two or more", so two is a pattern. A single pair of identical
#: links is precisely the case a reader would otherwise never think to merge.
MINIMUM = 2


def _members(frontmatter: dict) -> list[tuple[str, str | None]]:
    members: list[tuple[str, str | None]] = []
    for member in frontmatter.get("members") or []:
        if isinstance(member, str):
            members.append((member, None))
        elif isinstance(member, dict) and isinstance(member.get("id"), str):
            role = member.get("role")
            members.append((member["id"], role if isinstance(role, str) else None))
    return members


def _provenance(frontmatter: dict) -> tuple:
    """Read `scribe.origin` in either spelling the format allows."""
    nested = frontmatter.get("scribe")
    nested = nested if isinstance(nested, dict) else {}
    values = []
    for key in PROVENANCE:
        short = key.split(".", 1)[1]
        values.append(repr(frontmatter.get(key, nested.get(short))))
    return tuple(values)


def _signature(frontmatter: dict, body: str) -> tuple:
    """Everything that would have to be identical for one file to say it all.

    Body included: a description is a statement about *this* link, and folding
    two links with different prose would throw one of them away. Any field the
    world invented is included too — the kernel's vocabulary is open, so a
    signature that only knew the standard facets would be blind to exactly the
    fields a world added to tell its links apart.
    """
    known = set(FACETS) | set(PROVENANCE) | {"id", "kind", "type", "members", "scribe"}
    extra = tuple(
        (key, repr(frontmatter[key])) for key in sorted(frontmatter) if key not in known
    )
    return (
        tuple(repr(frontmatter.get(facet)) for facet in FACETS)
        + _provenance(frontmatter)
        + (body.strip(),)
        + extra
    )


def find_mergeable(
    rows: Iterable[tuple[str, str, dict]],
    body_of: Callable[[str], str | None] | None = None,
) -> list[dict[str, Any]]:
    """Group binary relations that differ only in the member that varies.

    `rows` is the canon reader's own `(id, relative_path, frontmatter)` shape,
    so this needs no loader of its own. `body_of` reads one artifact's prose and
    returns None when it cannot; pass `CanonReader.body_or_none`. Without it,
    bodies cannot be compared at all and no suggestion is made for any relation
    that has one — silence is the only safe answer when the comparison cannot
    be performed.
    """
    artifacts = list(rows)
    kinds = {row[0]: (row[2] or {}).get("kind") for row in artifacts}

    # A relation another artifact points at is addressable in its own right;
    # folding it into a sibling would silently break that reference.
    targeted: set[str] = set()
    for _artifact_id, _path, frontmatter in artifacts:
        for member_id, _role in _members(frontmatter or {}):
            if kinds.get(member_id) == "relation":
                targeted.add(member_id)

    groups: dict[tuple, list[tuple[str, str]]] = defaultdict(list)
    for artifact_id, _path, frontmatter in artifacts:
        frontmatter = frontmatter or {}
        if frontmatter.get("kind") != "relation" or artifact_id in targeted:
            continue
        members = _members(frontmatter)
        if len(members) != 2:
            continue
        if body_of is None:
            # No way to compare prose, so no way to know two links say the same
            # thing. Only bodiless relations can be judged, and this is a hint:
            # a wrong hint is worse than a missing one.
            body = ""
            if (frontmatter.get("body") or "").strip():
                continue
        else:
            body = body_of(artifact_id)
            if body is None:
                # Unreadable is not empty. Two files nobody can open are not
                # thereby the same statement, and a suggestion to fold them
                # would be built on a comparison that never happened.
                continue
        signature = _signature(frontmatter, body)
        # One member is the shared anchor, the other is what varies. Try both
        # ways round: which is which is a property of the group, not the file.
        for anchor, varying in ((members[0], members[1]), (members[1], members[0])):
            key = (
                frontmatter.get("type") or "",
                anchor[0],
                anchor[1],
                varying[1],
                signature,
            )
            groups[key].append((artifact_id, varying[0]))

    found: list[dict[str, Any]] = []
    claimed: set[str] = set()
    for key, entries in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0][:4])):
        if len(entries) < MINIMUM:
            continue
        if any(relation_id in claimed for relation_id, _ in entries):
            continue
        claimed.update(relation_id for relation_id, _ in entries)
        relation_type, anchor_id, anchor_role, varying_role, _ = key
        found.append(
            {
                "type": relation_type or "(untyped)",
                "anchor": anchor_id,
                "anchor_role": anchor_role,
                "member_role": varying_role,
                "relations": sorted(relation_id for relation_id, _ in entries),
                "members": sorted(member_id for _, member_id in entries),
            }
        )
    return found


def format_mergeable(found: list[dict[str, Any]], *, limit: int = 3) -> list[str]:
    """One line per group, in the register the scribe reports warnings in."""
    lines: list[str] = []
    for group in found[:limit]:
        count = len(group["relations"])
        role = group["member_role"] or "member"
        anchor_role = group["anchor_role"] or "member"
        lines.append(
            f"{count} '{group['type']}' relations share {anchor_role} "
            f"{group['anchor']} with identical facets; one relation with "
            f"{count} '{role}' members would say the same thing"
        )
    if len(found) > limit:
        lines.append(f"(+{len(found) - limit} more such groups)")
    return lines
