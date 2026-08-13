"""Selective, read-only canon context sized for an AI context window.

Everything here reuses the canonical loader, index, and search behaviour that
`apply.py` already owns: the same file walk, the same frontmatter parsing, the
same fields `--find` matches on. Nothing is inferred, nothing is regenerated,
and no result is ever invented — an id that is not on disk comes back as a miss.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .paths import ToolPaths, import_apply


DEFAULT_LIMIT = 10
SNIPPET_CHARS = 240

#: Fields `apply.py --find` already matches on. Deliberately not widened.
SEARCHABLE_FIELDS = ("id", "name", "tags")


@dataclass
class Match:
    id: str
    kind: str
    type: str
    name: str
    status: str
    tags: list[str]
    reasons: list[str]
    snippet: str = ""
    body: str | None = None

    def as_json(self) -> dict[str, Any]:
        record: dict[str, Any] = {
            "id": self.id,
            "kind": self.kind,
            "type": self.type,
            "name": self.name,
            "status": self.status,
            "tags": list(self.tags),
            "matched_on": list(self.reasons),
        }
        if self.snippet:
            record["snippet"] = self.snippet
        if self.body is not None:
            record["body"] = self.body
        return record


@dataclass
class Neighbor:
    id: str
    kind: str
    type: str
    name: str
    status: str
    via: str
    via_type: str
    via_kind: str
    target_role: str | None = None
    neighbor_role: str | None = None

    def as_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "type": self.type,
            "name": self.name,
            "status": self.status,
            "via": self.via,
            "via_type": self.via_type,
            "via_kind": self.via_kind,
            "target_role": self.target_role,
            "neighbor_role": self.neighbor_role,
        }


@dataclass
class ContextResult:
    query: dict[str, Any]
    matches: list[Match] = field(default_factory=list)
    neighbors: list[Neighbor] = field(default_factory=list)
    total: int = 0
    shown: int = 0
    truncated: bool = False
    notes: list[str] = field(default_factory=list)

    def as_json(self) -> dict[str, Any]:
        record: dict[str, Any] = {
            "query": self.query,
            "total": self.total,
            "shown": self.shown,
            "truncated": self.truncated,
            "omitted": max(0, self.total - self.shown),
            "notes": list(self.notes),
        }
        if self.matches or not self.neighbors:
            record["matches"] = [match.as_json() for match in self.matches]
        if self.neighbors:
            record["neighbors"] = [neighbor.as_json() for neighbor in self.neighbors]
        return record


def format_context(result: "ContextResult") -> str:
    """Render one context result compactly, always stating what was left out."""
    lines: list[str] = []
    query = result.query

    if "artifact" in query:
        header = f"artifact {query['artifact']}"
    elif "neighbors" in query:
        header = f"one-hop neighbours of {query['neighbors']}"
    elif query.get("query"):
        header = f"matches for {query['query']!r}"
    else:
        header = "matching artifacts"

    filters = ", ".join(
        f"{key}={query[key]}"
        for key in ("kind", "type", "status")
        if query.get(key) is not None
    )
    if filters:
        header += f" ({filters})"
    lines.append(f"{header}: {result.total}")
    if result.truncated:
        omitted = result.total - result.shown
        lines.append(f"showing {result.shown}; {omitted} omitted — raise --limit or narrow the query")

    for match in result.matches:
        label = match.name or match.id
        typed = f"/{match.type}" if match.type else ""
        lines.append(
            f"  {match.id}  [{match.kind}{typed}] {label}"
            f"  ({match.status})  <- {', '.join(match.reasons)}"
        )
        if match.tags:
            lines.append(f"      tags: {', '.join(match.tags)}")
        if match.snippet:
            lines.append(f"      {match.snippet}")
        if match.body is not None:
            for line in match.body.splitlines():
                lines.append(f"      | {line}")

    for neighbor in result.neighbors:
        label = neighbor.name or neighbor.id
        roles = ""
        if neighbor.target_role or neighbor.neighbor_role:
            roles = f"  [{neighbor.target_role or '?'} -> {neighbor.neighbor_role or '?'}]"
        lines.append(
            f"  {neighbor.id}  {label}  via {neighbor.via}"
            f" ({neighbor.via_type or neighbor.via_kind}){roles}"
        )

    for note in result.notes:
        lines.append(f"  note: {note}")

    return "\n".join(lines) + "\n"


class CanonReader:
    """One cached read of a world through apply.py's own loader."""

    def __init__(self, world: Path, paths: ToolPaths | None = None) -> None:
        self.world = Path(world)
        self.paths = paths or ToolPaths()
        self.apply = import_apply(self.paths)
        self._artifacts: list[tuple[str, str, dict]] | None = None
        self._bodies: dict[str, str] = {}

    @property
    def artifacts(self) -> list[tuple[str, str, dict]]:
        if self._artifacts is None:
            rows = self.apply.all_artifacts(str(self.world))
            self._artifacts = sorted(rows, key=lambda row: row[0])
        return self._artifacts

    def by_id(self) -> dict[str, tuple[str, str, dict]]:
        return {row[0]: row for row in self.artifacts}

    def body_of(self, artifact_id: str) -> str:
        if artifact_id in self._bodies:
            return self._bodies[artifact_id]
        path = self.apply.find_path_for_id(str(self.world), artifact_id)
        text = ""
        if path:
            try:
                raw = Path(path).read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                raw = ""
            match = re.match(r"^---\n.*?\n---\n?", raw, re.S)
            text = raw[match.end():] if match else raw
        self._bodies[artifact_id] = text.strip()
        return self._bodies[artifact_id]

    def index_state(self) -> dict[str, Any]:
        """Report whether INDEX.md exists and still lists the artifacts on disk.

        There is no stored freshness marker, so freshness is derived by
        comparing the ids the index lists against the ids present now.
        """
        path = self.world / "INDEX.md"
        if not path.is_file():
            return {"present": False, "state": "absent", "detail": "no INDEX.md"}
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            return {"present": True, "state": "unreadable", "detail": str(exc)}

        listed = set(re.findall(r"^\|\s*`([^`]+)`", text, re.M))
        actual = {
            row[0]
            for row in self.artifacts
            if (row[2].get("kind") or "") != ""
        }
        if listed == actual:
            return {"present": True, "state": "fresh", "detail": f"{len(listed)} artifact(s)"}
        missing = len(actual - listed)
        extra = len(listed - actual)
        return {
            "present": True,
            "state": "stale",
            "detail": f"{missing} artifact(s) missing, {extra} no longer present",
            "missing": missing,
            "extra": extra,
        }


def _snippet(text: str, limit: int = SNIPPET_CHARS) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1].rstrip() + "…"


def _tags_of(frontmatter: dict) -> list[str]:
    tags = frontmatter.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    if not isinstance(tags, list):
        return []
    return [tag for tag in tags if isinstance(tag, str)]


def _row_to_match(
    reader: CanonReader,
    artifact_id: str,
    frontmatter: dict,
    reasons: Iterable[str],
    *,
    full: bool = False,
) -> Match:
    body = reader.body_of(artifact_id)
    return Match(
        id=artifact_id,
        kind=frontmatter.get("kind") or "",
        type=frontmatter.get("type") or "",
        name=frontmatter.get("name") or "",
        status=frontmatter.get("status", "canon") or "canon",
        tags=_tags_of(frontmatter),
        reasons=sorted(set(reasons)),
        snippet="" if full else _snippet(body),
        body=body if full else None,
    )


def _passes_filters(
    reader: CanonReader,
    frontmatter: dict,
    kind: str | None,
    type_pattern: str | None,
    status: str | None,
) -> bool:
    if kind is not None and (frontmatter.get("kind") or "") != kind:
        return False
    if type_pattern is not None and not reader.apply.type_matches(
        frontmatter.get("type") or "", type_pattern
    ):
        return False
    if status is not None and (frontmatter.get("status", "canon") or "canon") != status:
        return False
    return True


def search(
    reader: CanonReader,
    query: str | None,
    *,
    kind: str | None = None,
    type_pattern: str | None = None,
    status: str | None = None,
    limit: int = DEFAULT_LIMIT,
    full: bool = False,
) -> ContextResult:
    """Match on the fields apply.py already searches, and say why each hit matched."""
    needle = query.casefold() if query else None
    matches: list[Match] = []

    for artifact_id, _rel, frontmatter in reader.artifacts:
        if not _passes_filters(reader, frontmatter, kind, type_pattern, status):
            continue
        reasons: list[str] = []
        if needle is None:
            reasons.append("filter")
        else:
            if needle in artifact_id.casefold():
                reasons.append("id")
            name = frontmatter.get("name") or ""
            if isinstance(name, str) and needle in name.casefold():
                reasons.append("name")
            if any(needle in tag.casefold() for tag in _tags_of(frontmatter)):
                reasons.append("tag")
            if not reasons:
                continue
        matches.append(_row_to_match(reader, artifact_id, frontmatter, reasons, full=full))

    matches.sort(key=lambda match: match.id)
    total = len(matches)
    shown = matches[:limit] if limit is not None else matches
    return ContextResult(
        query={
            "query": query,
            "kind": kind,
            "type": type_pattern,
            "status": status,
            "limit": limit,
            "searched_fields": list(SEARCHABLE_FIELDS),
        },
        matches=shown,
        total=total,
        shown=len(shown),
        truncated=total > len(shown),
    )


def lookup(reader: CanonReader, artifact_id: str, *, full: bool = False) -> ContextResult:
    """Return one artifact exactly, or an honest miss."""
    row = reader.by_id().get(artifact_id)
    result = ContextResult(
        query={"artifact": artifact_id, "full": full}, total=0, shown=0
    )
    if row is None:
        result.notes.append(
            f"no artifact with id '{artifact_id}' exists in this canon"
        )
        return result
    result.matches = [_row_to_match(reader, row[0], row[2], ["exact id"], full=full)]
    result.total = 1
    result.shown = 1
    return result


def one_hop_neighbors(
    reader: CanonReader,
    artifact_id: str,
    *,
    limit: int = DEFAULT_LIMIT,
) -> ContextResult:
    """Return direct neighbours only, naming the relation and roles that connect them.

    One hop means one hop: the relations this artifact is a member of, and the
    artifacts that reference it. Neighbours of neighbours are never followed.
    """
    by_id = reader.by_id()
    result = ContextResult(query={"neighbors": artifact_id, "limit": limit, "depth": 1})
    if artifact_id not in by_id:
        result.notes.append(
            f"no artifact with id '{artifact_id}' exists in this canon"
        )
        return result

    found: list[Neighbor] = []
    for other_id, _rel, frontmatter in reader.artifacts:
        if other_id == artifact_id:
            continue
        kind = frontmatter.get("kind") or ""
        members = frontmatter.get("members") or []
        roles: dict[str, str | None] = {}
        if isinstance(members, list):
            for member in members:
                if isinstance(member, dict) and isinstance(member.get("id"), str):
                    roles[member["id"]] = (
                        member.get("role") if isinstance(member.get("role"), str) else None
                    )
                elif isinstance(member, str):
                    roles.setdefault(member, None)

        if kind == "relation" and artifact_id in roles:
            for member_id, role in roles.items():
                if member_id == artifact_id or member_id not in by_id:
                    continue
                target = by_id[member_id][2]
                found.append(
                    Neighbor(
                        id=member_id,
                        kind=target.get("kind") or "",
                        type=target.get("type") or "",
                        name=target.get("name") or "",
                        status=target.get("status", "canon") or "canon",
                        via=other_id,
                        via_type=frontmatter.get("type") or "",
                        via_kind="relation",
                        target_role=roles.get(artifact_id),
                        neighbor_role=role,
                    )
                )
            continue

        # Non-relation references: where/when anchors pointing at this artifact.
        if artifact_id in reader.apply.referring_ids(frontmatter):
            found.append(
                Neighbor(
                    id=other_id,
                    kind=kind,
                    type=frontmatter.get("type") or "",
                    name=frontmatter.get("name") or "",
                    status=frontmatter.get("status", "canon") or "canon",
                    via=other_id,
                    via_type=frontmatter.get("type") or "",
                    via_kind="reference",
                )
            )

    found.sort(key=lambda neighbor: (neighbor.id, neighbor.via, neighbor.neighbor_role or ""))
    total = len(found)
    shown = found[:limit] if limit is not None else found
    result.neighbors = shown
    result.total = total
    result.shown = len(shown)
    result.truncated = total > len(shown)
    return result
