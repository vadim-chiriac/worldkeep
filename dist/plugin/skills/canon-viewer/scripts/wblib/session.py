"""Everything an assistant needs to start working in a canon, in one read.

The point of this module is economy: one bounded, deterministic report that
replaces opening SKILL.md, KERNEL.md, SCRIBE.md, scribe.yaml, world.yaml, the
index, and the type and view folders one at a time. It reports; it never
decides, never writes, and never regenerates anything.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from . import context as context_module
from .discovery import Resolution, world_display_name
from .mergeable import find_mergeable, format_mergeable
from .paths import TOOL_VERSION, ToolPaths, parse_document_version
from .scribe_config import load_scribe_config


SCHEMA = "wb.session/v1"

#: Caps that keep the report small enough to be worth reading in full.
MAX_TYPES = 40
MAX_VIEWS = 20
MAX_MODULES = 20
MAX_QUERY_MATCHES = 5

KIND_ORDER = ("entity", "idea", "relation", "type")
STATUS_ORDER = ("canon", "draft", "deprecated")


def _counts(reader: context_module.CanonReader) -> dict[str, Any]:
    by_kind: dict[str, int] = {}
    by_status: dict[str, int] = {}
    graph_total = 0
    for _artifact_id, _rel, frontmatter in reader.artifacts:
        kind = frontmatter.get("kind") or "unknown"
        status = frontmatter.get("status", "canon") or "canon"
        by_kind[kind] = by_kind.get(kind, 0) + 1
        by_status[status] = by_status.get(status, 0) + 1
        if kind != "type":
            graph_total += 1

    def ordered(source: dict[str, int], preferred: tuple[str, ...]) -> dict[str, int]:
        known = {key: source[key] for key in preferred if key in source}
        rest = {key: source[key] for key in sorted(set(source) - set(preferred))}
        return {**known, **rest}

    return {
        "total": len(reader.artifacts),
        "graph_artifacts": graph_total,
        "by_kind": ordered(by_kind, KIND_ORDER),
        "by_status": ordered(by_status, STATUS_ORDER),
    }


def _types(reader: context_module.CanonReader, manifest: dict) -> dict[str, Any]:
    declared = manifest.get("std_types")
    standard = [item for item in declared if isinstance(item, str)] if isinstance(declared, list) else []

    defined: list[str] = []
    for artifact_id, _rel, frontmatter in reader.artifacts:
        if (frontmatter.get("kind") or "") != "type":
            continue
        defined.append(artifact_id.removeprefix("types/"))
    defined.sort()

    shown = defined[:MAX_TYPES]
    return {
        "standard": sorted(standard),
        "defined": shown,
        "defined_total": len(defined),
        "defined_omitted": max(0, len(defined) - len(shown)),
    }


def _yaml_name(path: Path, fallback: str) -> str:
    try:
        parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError):
        return fallback
    if isinstance(parsed, dict):
        name = parsed.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return fallback


def _views(world: Path) -> dict[str, Any]:
    views_dir = world / "views"
    entries: list[dict[str, str]] = []
    if views_dir.is_dir():
        for path in sorted(views_dir.rglob("*"), key=lambda item: item.as_posix().lower()):
            if not path.is_file() or path.suffix.lower() not in {".yaml", ".yml"}:
                continue
            if path.name.casefold().endswith(".view.lock.yaml"):
                continue
            entries.append(
                {
                    "path": path.relative_to(world).as_posix(),
                    "name": _yaml_name(path, path.stem),
                }
            )
    shown = entries[:MAX_VIEWS]

    modules_dir = world / "view-modules"
    modules: list[dict[str, str]] = []
    if modules_dir.is_dir():
        for path in sorted(modules_dir.iterdir(), key=lambda item: item.name.lower()):
            if not path.is_file() or path.suffix.lower() not in {".yaml", ".yml"}:
                continue
            try:
                parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, yaml.YAMLError):
                continue
            if not isinstance(parsed, dict):
                continue
            modules.append(
                {
                    "id": str(parsed.get("id", path.stem)),
                    "kind": str(parsed.get("kind", "unknown")),
                }
            )
    shown_modules = modules[:MAX_MODULES]

    return {
        "builtin": ["Everything"],
        "named": shown,
        "named_total": len(entries),
        "named_omitted": max(0, len(entries) - len(shown)),
        "modules": shown_modules,
        "modules_total": len(modules),
        "modules_omitted": max(0, len(modules) - len(shown_modules)),
    }


def _versions(manifest: dict, paths: ToolPaths) -> dict[str, Any]:
    world_kernel = manifest.get("kernel_version")
    world_kernel = str(world_kernel) if world_kernel is not None else None
    kernel_doc = parse_document_version(paths.find("kernel"))
    scribe_doc = parse_document_version(paths.find("scribe"))

    problems: list[str] = []
    normalized_doc = kernel_doc.removeprefix("v") if kernel_doc != "unknown" else None
    if world_kernel is None:
        problems.append("world.yaml declares no kernel_version")
    elif normalized_doc and world_kernel != normalized_doc:
        problems.append(
            f"world.yaml kernel_version {world_kernel} != packaged KERNEL {normalized_doc}; "
            "re-read KERNEL.md before relying on version-specific rules"
        )

    return {
        "world_kernel": world_kernel,
        "kernel_document": kernel_doc,
        "scribe_document": scribe_doc,
        "wb": TOOL_VERSION,
        "problems": problems,
    }


def _next_operations(task: str, world_label: str, counts: dict[str, Any], views: dict[str, Any]) -> list[str]:
    if task == "view":
        operations = [
            f"wb view {world_label} --all-views -o out.html   # default",
            f"wb context {world_label} --query \"<subject>\"",
        ]
        if views["named_total"]:
            first = views["named"][0]["path"]
            operations.append(f"wb view {world_label} --view {first} -o out.html")
            operations.append(f"wb validate {world_label} --view {first}")
        else:
            operations.append(f"wb view {world_label} --everything -o out.html")
            operations.append(f"wb view {world_label} --all-views --json")
        return operations

    operations = [
        f"wb context {world_label} --query \"<subject>\"",
        f"wb capture {world_label} --session <id> < artifacts.json",
    ]
    if counts["by_status"].get("draft"):
        operations.append(f"wb approve {world_label} <id>...   # or: wb reject")
    operations.append(f"wb validate {world_label}")
    return operations


def build_session(
    resolution: Resolution,
    *,
    task: str = "capture",
    query: str | None = None,
    paths: ToolPaths | None = None,
) -> dict[str, Any]:
    """Assemble the whole session report as one JSON-shaped document."""
    paths = paths or ToolPaths()
    world = resolution.world
    reader = context_module.CanonReader(world, paths)

    scribe = load_scribe_config(world)
    counts = _counts(reader)
    views = _views(world)
    versions = _versions(resolution.manifest, paths)
    index_state = reader.index_state()

    warnings: list[str] = list(resolution.warnings)
    warnings.extend(scribe.warnings)
    warnings.extend(versions["problems"])
    if index_state["state"] == "stale":
        warnings.append(
            f"INDEX.md is stale ({index_state['detail']}); run 'wb reindex' if you want it current"
        )
    missing_tools = [name for name in ("apply", "validate", "view") if paths.find(name) is None]
    if missing_tools:
        warnings.append(
            f"packaged tool(s) not found beside wb: {', '.join(missing_tools)}; run 'wb doctor'"
        )
    if not counts["total"]:
        warnings.append("this canon has no artifacts yet")

    world_label = str(world)
    document: dict[str, Any] = {
        "schema": SCHEMA,
        "task": task,
        "world": {
            "path": world_label,
            "name": resolution.name or world_display_name(world, resolution.manifest),
        },
        "versions": versions,
        "scribe": scribe.as_json(),
        "counts": counts,
        "types": _types(reader, resolution.manifest),
        "index": index_state,
        "next": _next_operations(task, world_label, counts, views),
        "warnings": warnings,
    }

    mergeable = find_mergeable(reader.artifacts)
    if mergeable:
        document["mergeable"] = mergeable

    if task == "view" or views["named_total"] or views["modules_total"]:
        document["views"] = views

    if query:
        found = context_module.search(reader, query, limit=MAX_QUERY_MATCHES)
        document["context"] = found.as_json()

    return document


def format_session(document: dict[str, Any]) -> str:
    """Render the report as compact human-readable text."""
    lines: list[str] = []
    world = document["world"]
    lines.append(f"world: {world['name']}")
    lines.append(f"path:  {world['path']}")

    versions = document["versions"]
    lines.append(
        f"versions: kernel {versions['world_kernel'] or '?'} (doc {versions['kernel_document']}), "
        f"scribe {versions['scribe_document']}, wb {versions['wb']}"
    )

    counts = document["counts"]
    kinds = ", ".join(f"{kind} {count}" for kind, count in counts["by_kind"].items()) or "none"
    statuses = ", ".join(f"{status} {count}" for status, count in counts["by_status"].items()) or "none"
    lines.append(f"artifacts: {counts['total']} ({kinds})")
    lines.append(f"status:    {statuses}")

    scribe = document["scribe"]
    origin = "scribe.yaml" if scribe["file_present"] else "defaults (no scribe.yaml)"
    settings = ", ".join(
        f"{name}={detail['value']}" for name, detail in scribe["settings"].items()
    )
    lines.append(f"scribe:    {settings}  [{origin}]")

    types = document["types"]
    if types["standard"]:
        lines.append(f"std types: {', '.join(types['standard'])}")
    if types["defined"]:
        suffix = f" (+{types['defined_omitted']} more)" if types["defined_omitted"] else ""
        lines.append(f"defined:   {', '.join(types['defined'])}{suffix}")

    views = document.get("views")
    if views:
        # The full catalogue is only worth the space when the session is about
        # viewing; otherwise a count tells an assistant whether to ask for it.
        if document["task"] == "view":
            lines.append("views:     Everything (built in)")
            for entry in views["named"]:
                lines.append(f"           {entry['path']}  {entry['name']}")
            if views["named_omitted"]:
                lines.append(f"           (+{views['named_omitted']} more)")
            for entry in views["modules"]:
                lines.append(f"module:    {entry['id']} ({entry['kind']})")
            if views["modules_omitted"]:
                lines.append(f"           (+{views['modules_omitted']} more)")
        else:
            summary = f"Everything (built in) + {views['named_total']} named"
            if views["modules_total"]:
                summary += f", {views['modules_total']} module(s)"
            lines.append(f"views:     {summary}  [--task view to list]")

    index_state = document["index"]
    lines.append(f"index:     {index_state['state']} ({index_state['detail']})")

    found = document.get("context")
    if found:
        lines.append("")
        header = f"context for {found['query']['query']!r}: {found['total']} match(es)"
        if found["truncated"]:
            header += f", showing {found['shown']}"
        lines.append(header)
        for match in found.get("matches", []):
            label = match["name"] or match["id"]
            lines.append(
                f"  {match['id']}  [{match['kind']}"
                + (f"/{match['type']}" if match["type"] else "")
                + f"] {label}  <- {', '.join(match['matched_on'])}"
            )
            if match.get("snippet"):
                lines.append(f"      {match['snippet']}")

    lines.append("")
    lines.append("next:")
    for operation in document["next"]:
        lines.append(f"  {operation}")

    mergeable = document.get("mergeable") or []
    if mergeable:
        lines.append("")
        lines.append(f"could be one relation ({len(mergeable)}):")
        for line in format_mergeable(mergeable):
            lines.append(f"  {line}")

    warnings = document["warnings"]
    if warnings:
        lines.append("")
        lines.append(f"warnings ({len(warnings)}):")
        for warning in warnings:
            lines.append(f"  {warning}")

    return "\n".join(lines) + "\n"
