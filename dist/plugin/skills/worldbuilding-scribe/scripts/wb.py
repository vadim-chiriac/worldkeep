#!/usr/bin/env python3
"""wb — one stable entrypoint for working with a worldbuilding canon.

This is a thin orchestration layer. Every canon mutation still goes through the
existing deterministic apply/validate boundary, and every projection still goes
through the existing viewer; wb only removes the work of locating scripts,
juggling plugin-relative paths, and reading whole reference documents to learn
things a command can simply report.

Run ``wb <command> --help`` for a command's options.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from wblib import context as context_module  # noqa: E402
from wblib.capture_report import build_report, format_report, snapshot  # noqa: E402
from wblib.delegate import parse_capture_payload, read_input, run_tool  # noqa: E402
from wblib.discovery import DiscoveryError, resolve_canon  # noqa: E402
from wblib.paths import TOOL_VERSION, ToolNotFound, ToolPaths, parse_document_version  # noqa: E402
from wblib.session import build_session, format_session  # noqa: E402


EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2


def _emit(text: str, output: Path | None) -> None:
    if output is not None:
        target = output.expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(text)


def _emit_document(document: dict, human: str, args: argparse.Namespace) -> None:
    if getattr(args, "json", False):
        _emit(json.dumps(document, ensure_ascii=False, indent=2, default=str) + "\n", args.output)
    else:
        _emit(human, args.output)


def add_common_output(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json", action="store_true", help="emit stable JSON instead of text"
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=None, help="write output to this file"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wb",
        description="Agent-facing operations for a worldbuilding canon.",
    )
    parser.add_argument(
        "--version", action="version", version=f"wb {TOOL_VERSION}"
    )
    commands = parser.add_subparsers(dest="command", metavar="<command>")

    session = commands.add_parser(
        "session",
        help="start here: resolve the canon and report everything needed to work in it",
        description=(
            "Read-only session initialisation. Accepts a canon folder or a "
            "bounded root containing exactly one."
        ),
    )
    session.add_argument("path", type=Path, help="canon folder, or a root containing one")
    session.add_argument(
        "--task",
        choices=("capture", "view"),
        default="capture",
        help="what this session is for; tunes the suggested next operations",
    )
    session.add_argument(
        "--query", default=None, help="also return a small relevant-context section"
    )
    add_common_output(session)
    session.set_defaults(handler=cmd_session)

    # -- reading the canon ------------------------------------------------
    find = commands.add_parser(
        "find", help="search ids, names and tags for a phrase"
    )
    find.add_argument("world", type=Path)
    find.add_argument("query")
    find.add_argument("--limit", type=int, default=context_module.DEFAULT_LIMIT)
    add_common_output(find)
    find.set_defaults(handler=cmd_find)

    context = commands.add_parser(
        "context",
        help="return only the canon an assistant needs, not the whole world",
        description=(
            "Read-only. Exactly one of --query, --artifact or --neighbors, or "
            "filters alone. Neighbours are one hop; the graph is never walked."
        ),
    )
    context.add_argument("world", type=Path)
    selector = context.add_mutually_exclusive_group()
    selector.add_argument("--query", help="match ids, names and tags")
    selector.add_argument("--artifact", help="look one artifact up exactly")
    selector.add_argument("--neighbors", help="direct neighbours of this artifact")
    context.add_argument("--kind", help="restrict to one kind")
    context.add_argument("--type", dest="type_pattern", help="restrict to a type glob")
    context.add_argument("--status", help="restrict to one status")
    context.add_argument("--limit", type=int, default=context_module.DEFAULT_LIMIT)
    context.add_argument(
        "--full",
        action="store_true",
        help="return whole artifact bodies instead of summaries",
    )
    add_common_output(context)
    context.set_defaults(handler=cmd_context)

    # -- changing the canon -----------------------------------------------
    capture = commands.add_parser(
        "capture",
        help="write artifacts from JSON (stdin or --input-file) through apply.py",
        description=(
            "Creates or updates artifacts under the current Scribe rules. New "
            "work lands as a draft; nothing is promoted here."
        ),
    )
    capture.add_argument("world", type=Path)
    capture.add_argument("--session", required=True, help="scribe session id")
    capture.add_argument(
        "--status",
        choices=("draft", "canon"),
        default=None,
        help="default status for items that do not set their own",
    )
    capture.add_argument("--input-file", type=Path, default=None)
    add_common_output(capture)
    capture.set_defaults(handler=cmd_capture)

    approve = commands.add_parser(
        "approve", help="promote approved drafts to canon (apply.py --promote)"
    )
    approve.add_argument("world", type=Path)
    approve.add_argument("ids", nargs="+")
    add_common_output(approve)
    approve.set_defaults(handler=cmd_approve)

    reject = commands.add_parser(
        "reject", help="delete rejected drafts (apply.py --reject)"
    )
    reject.add_argument("world", type=Path)
    reject.add_argument("ids", nargs="+")
    add_common_output(reject)
    reject.set_defaults(handler=cmd_reject)

    reindex = commands.add_parser(
        "reindex", help="rebuild the disposable INDEX.md (apply.py --reindex)"
    )
    reindex.add_argument("world", type=Path)
    add_common_output(reindex)
    reindex.set_defaults(handler=cmd_reindex)

    validate = commands.add_parser(
        "validate",
        help="run the canon validator, or validate one named view",
    )
    validate.add_argument("world", type=Path)
    validate.add_argument(
        "--view", type=Path, default=None, help="validate this view instead of the canon"
    )
    validate.add_argument(
        "--write-lock",
        action="store_true",
        help="with --view, record dependencies in an adjacent lock file",
    )
    add_common_output(validate)
    validate.set_defaults(handler=cmd_validate)

    # -- looking at the canon ---------------------------------------------
    view = commands.add_parser(
        "view",
        help="render or project a view through the existing viewer",
        description=(
            "With no target, renders every view into one document with a "
            "picker, which is almost always what is wanted: switching views "
            "keeps node positions, so the views are comparable. Ask for "
            "--everything when you want the neutral audit instead."
        ),
    )
    view.add_argument("world", type=Path)
    target = view.add_mutually_exclusive_group()
    target.add_argument("--everything", action="store_true", help="the audit projection")
    target.add_argument("--view", dest="view_path", type=Path, action="append")
    target.add_argument("--all-views", action="store_true")
    target.add_argument("--list-views", action="store_true")
    view.add_argument("--json", action="store_true", help="emit the projection as JSON")
    view.add_argument("--vendor", action="store_true", help="inline assets for offline HTML")
    view.add_argument("-o", "--output", type=Path, default=None)
    view.set_defaults(handler=cmd_view)

    explain = commands.add_parser(
        "explain", help="explain why one artifact appears as it does in a view"
    )
    explain.add_argument("world", type=Path)
    explain.add_argument("--view", dest="view_path", type=Path, required=True)
    explain.add_argument("--artifact", required=True)
    explain.add_argument("--json", action="store_true")
    explain.add_argument("-o", "--output", type=Path, default=None)
    explain.set_defaults(handler=cmd_explain)

    doctor = commands.add_parser(
        "doctor", help="report runtime, packaged tools and versions; changes nothing"
    )
    doctor.add_argument("path", type=Path, nargs="?", default=None)
    add_common_output(doctor)
    doctor.set_defaults(handler=cmd_doctor)

    return parser


def _world_of(args: argparse.Namespace) -> Path:
    """Resolve the canon for a command, accepting a bounded root as well."""
    return resolve_canon(args.world).world


def _reader(args: argparse.Namespace, paths: ToolPaths) -> context_module.CanonReader:
    return context_module.CanonReader(_world_of(args), paths)


def _delegate(
    args: argparse.Namespace,
    paths: ToolPaths,
    tool: str,
    arguments: list[str],
    *,
    stdin_text: str | None = None,
) -> int:
    """Run a tool, honouring --json by wrapping its output in a stable envelope."""
    wants_json = getattr(args, "json", False)
    result = run_tool(paths, tool, arguments, stdin_text=stdin_text, capture=wants_json)
    if wants_json:
        _emit(
            json.dumps(result.as_json(), ensure_ascii=False, indent=2) + "\n",
            getattr(args, "output", None),
        )
    return result.returncode


def cmd_session(args: argparse.Namespace) -> int:
    paths = ToolPaths()
    resolution = resolve_canon(args.path)
    document = build_session(
        resolution, task=args.task, query=args.query, paths=paths
    )
    _emit_document(document, format_session(document), args)
    return EXIT_OK


def cmd_find(args: argparse.Namespace) -> int:
    paths = ToolPaths()
    found = context_module.search(_reader(args, paths), args.query, limit=args.limit)
    _emit_document(found.as_json(), context_module.format_context(found), args)
    return EXIT_OK


def cmd_context(args: argparse.Namespace) -> int:
    paths = ToolPaths()
    reader = _reader(args, paths)
    if args.artifact:
        found = context_module.lookup(reader, args.artifact, full=args.full)
    elif args.neighbors:
        found = context_module.one_hop_neighbors(reader, args.neighbors, limit=args.limit)
    else:
        found = context_module.search(
            reader,
            args.query,
            kind=args.kind,
            type_pattern=args.type_pattern,
            status=args.status,
            limit=args.limit,
            full=args.full,
        )
    _emit_document(found.as_json(), context_module.format_context(found), args)
    return EXIT_OK


def cmd_capture(args: argparse.Namespace) -> int:
    paths = ToolPaths()
    world = _world_of(args)
    try:
        raw = read_input(args.input_file)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE

    try:
        payload = parse_capture_payload(raw)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE

    artifact_ids = [artifact["id"] for artifact in payload.artifacts]
    before_reader = context_module.CanonReader(world, paths)
    before = snapshot(before_reader, artifact_ids)

    arguments = [str(world), "--session", args.session]
    if args.status:
        arguments += ["--status", args.status]
    result = run_tool(paths, "apply", arguments, stdin_text=payload.writer_input(), capture=True)
    report = None
    if result.returncode == 0:
        after_reader = context_module.CanonReader(world, paths)
        after = snapshot(after_reader, artifact_ids)
        post_frontmatter = {
            artifact_id: after_reader.by_id()[artifact_id][2]
            for artifact_id in after
        }
        canon_frontmatter = {
            artifact_id: frontmatter
            for artifact_id, _path, frontmatter in after_reader.artifacts
        }
        report = build_report(
            before,
            after,
            payload.bundles,
            post_frontmatter,
            canon_frontmatter,
        )

    if getattr(args, "json", False):
        document = result.as_json()
        if report is not None:
            document["capture"] = report
        _emit(json.dumps(document, ensure_ascii=False, indent=2) + "\n", args.output)
    else:
        human = result.stdout
        if report is not None:
            human += "\n" + format_report(report)
        _emit(human, args.output)
        if result.stderr:
            sys.stderr.write(result.stderr)
        if report is not None and args.output is None:
            _report_mergeable(world, paths)
    return result.returncode


def _report_mergeable(world: Path, paths: ToolPaths) -> None:
    """Say when several relations just written say one thing between them.

    Every graph formalism these models were trained on is binary, and the
    kernel's own rule is a permission with a condition, so splitting is the
    choice that can never be wrong. Prose has not shifted that; a deterministic
    line after the write does. It is a notice — splitting is legal, sometimes
    deliberate, and the author decides.
    """
    try:
        from wblib.context import CanonReader
        from wblib.mergeable import find_mergeable, format_mergeable

        reader = CanonReader(world, paths)
        found = find_mergeable(reader.artifacts, reader.body_or_none)
    except Exception:  # pragma: no cover - never let a hint break a write
        return
    if not found:
        return
    print(f"\ncould be one relation ({len(found)}):")
    for line in format_mergeable(found):
        print(f"  {line}")


def cmd_approve(args: argparse.Namespace) -> int:
    paths = ToolPaths()
    return _delegate(
        args, paths, "apply", [str(_world_of(args)), "--promote", *args.ids]
    )


def cmd_reject(args: argparse.Namespace) -> int:
    paths = ToolPaths()
    return _delegate(
        args, paths, "apply", [str(_world_of(args)), "--reject", *args.ids]
    )


def cmd_reindex(args: argparse.Namespace) -> int:
    paths = ToolPaths()
    return _delegate(args, paths, "apply", [str(_world_of(args)), "--reindex"])


def cmd_validate(args: argparse.Namespace) -> int:
    paths = ToolPaths()
    world = _world_of(args)
    if args.view is not None:
        arguments = [str(world), "--validate-view", str(args.view)]
        if args.write_lock:
            arguments.append("--write-lock")
        if getattr(args, "json", False):
            arguments.append("--json")
        result = run_tool(paths, "view", arguments)
        return result.returncode
    return _delegate(args, paths, "validate", [str(world)])


def cmd_view(args: argparse.Namespace) -> int:
    paths = ToolPaths()
    world = _world_of(args)
    arguments = [str(world)]
    if args.list_views:
        arguments.append("--list-views")
    elif args.all_views:
        arguments.append("--all-views")
    elif args.view_path:
        for path in args.view_path:
            arguments += ["--view", str(path)]
    elif args.everything:
        arguments.append("--everything")
    else:
        # Everything is the audit projection: it ignores every style the world
        # declared, which makes it the wrong thing to hand someone who just
        # asked to see their world. The skill and the documentation both said
        # the default was all views; only this line disagreed. `--everything`
        # used to reach the viewer by being this fallback rather than by being
        # read, which is why it needs its own branch now.
        arguments.append("--all-views")
    if args.json:
        arguments.append("--json")
    if args.vendor:
        arguments.append("--vendor")
    if args.output is not None:
        arguments += ["--output", str(args.output)]
    result = run_tool(paths, "view", arguments)
    return result.returncode


def cmd_explain(args: argparse.Namespace) -> int:
    paths = ToolPaths()
    arguments = [
        str(_world_of(args)),
        "--explain-view",
        str(args.view_path),
        "--artifact",
        args.artifact,
    ]
    if args.json:
        arguments.append("--json")
    if args.output is not None:
        arguments += ["--output", str(args.output)]
    result = run_tool(paths, "view", arguments)
    return result.returncode


def cmd_doctor(args: argparse.Namespace) -> int:
    paths = ToolPaths()
    located = paths.describe()
    problems: list[str] = []
    for name in ("apply", "validate", "view"):
        if located[name] is None:
            problems.append(f"missing tool: {name}")
    for name in ("kernel", "scribe"):
        if located[name] is None:
            problems.append(f"missing reference: {name.upper()}.md")

    runtime = {
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "wb": TOOL_VERSION,
        "install_root": str(SCRIPT_DIR),
    }
    try:
        import yaml

        runtime["pyyaml"] = getattr(yaml, "__version__", "unknown")
    except ImportError:
        runtime["pyyaml"] = None
        problems.append("PyYAML is not importable; the bundled copy was not found")

    document = {
        "schema": "wb.doctor/v1",
        "runtime": runtime,
        "tools": located,
        "versions": {
            "kernel_document": parse_document_version(paths.find("kernel")),
            "scribe_document": parse_document_version(paths.find("scribe")),
        },
        "problems": problems,
    }

    if args.path is not None:
        try:
            resolution = resolve_canon(args.path)
            document["world"] = {
                "path": str(resolution.world),
                "name": resolution.name,
                "warnings": resolution.warnings,
            }
        except DiscoveryError as exc:
            document["world"] = {"error": str(exc)}
            problems.append(str(exc))

    lines = [f"wb {runtime['wb']}  python {runtime['python']}  PyYAML {runtime['pyyaml']}"]
    lines.append(f"install: {runtime['install_root']}")
    for name, location in located.items():
        lines.append(f"  {name:<14} {location or 'NOT FOUND'}")
    if "world" in document:
        lines.append(f"world: {document['world'].get('path', document['world'].get('error'))}")
    if problems:
        lines.append("")
        lines.append(f"problems ({len(problems)}):")
        lines += [f"  {problem}" for problem in problems]
    else:
        lines.append("")
        lines.append("no problems found")

    _emit_document(document, "\n".join(lines) + "\n", args)
    return EXIT_OK if not problems else EXIT_FAILED


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "command", None) is None:
        parser.print_help()
        return EXIT_USAGE
    try:
        return args.handler(args)
    except DiscoveryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except ToolNotFound as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except BrokenPipeError:  # pragma: no cover - piping into head and friends
        return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
