#!/usr/bin/env python3
"""Worldbuilding canon viewer CLI (Stage 1: view discovery)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
VENDOR_DIRS = (
    SCRIPT_DIR / "_vendor",
    SCRIPT_DIR.parent / "runtime" / "_vendor",
)
for vendor_dir in VENDOR_DIRS:
    if vendor_dir.is_dir():
        sys.path.insert(0, str(vendor_dir))
        break

from viewer.compile import CompileError, compile_view
from viewer.explain import explain_artifact, format_explanation
from viewer.load import CanonLoadError, ViewLoadError, builtin_everything, list_views, load_canon, load_view
from viewer.modules import ModuleError
from viewer.project import project_view, project_views
from viewer.render_graph import RenderError, render_graph, render_graph_document
from viewer.validate_view import validate_view


def _emit(args: argparse.Namespace, rendered: str) -> None:
    """Write text to the requested output file, or to stdout."""
    if args.output:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(rendered)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read a KERNEL canon folder and generate a view."
    )
    parser.add_argument("canon_folder", type=Path, help="path to the canon folder")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument(
        "--list-views",
        action="store_true",
        help="list view files available in the canon folder",
    )
    action.add_argument(
        "--view",
        type=Path,
        action="append",
        help="view YAML path relative to the canon; repeat for one document",
    )
    action.add_argument(
        "--all-views",
        action="store_true",
        help="include every view in the canon, ordered by path",
    )
    action.add_argument(
        "--everything",
        action="store_true",
        help="render the viewer-owned Everything audit projection",
    )
    action.add_argument(
        "--validate-view",
        type=Path,
        help="check that a named view compiles and renders, without generating HTML",
    )
    action.add_argument(
        "--explain-view",
        type=Path,
        help="explain why one artifact appears as it does in a named view",
    )
    parser.add_argument(
        "--artifact",
        help="artifact id to explain; required with --explain-view",
    )
    parser.add_argument(
        "--write-lock",
        action="store_true",
        help="with --validate-view, record dependencies in an adjacent lock file",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit the Viewer v0 projection as JSON and skip rendering",
    )
    parser.add_argument("-o", "--output", type=Path, help="write output to this file")
    parser.add_argument(
        "--vendor",
        action="store_true",
        help="inline pinned local browser assets for fully offline HTML",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.list_views:
            if args.json or args.output or args.vendor:
                parser.error("--list-views cannot be combined with output options")
            views = list_views(args.canon_folder)
            for view in views:
                print(f"{view.relative_path}\t{view.name}")
                for warning in view.warnings:
                    print(f"warning: {warning}", file=sys.stderr)
            return 0

        if args.validate_view is not None:
            if args.vendor:
                parser.error("--vendor applies to HTML output, not --validate-view")
            canon = load_canon(args.canon_folder)
            view = load_view(args.canon_folder, args.validate_view)
            result = validate_view(canon, view, write_lock_file=args.write_lock)
            rendered = (
                json.dumps(result.as_json(), ensure_ascii=False, indent=2, default=str) + "\n"
                if args.json
                else result.as_text()
            )
            _emit(args, rendered)
            return 0 if result.ok else 1

        if args.explain_view is not None:
            if args.artifact is None:
                parser.error("--explain-view requires --artifact")
            if args.vendor:
                parser.error("--vendor applies to HTML output, not --explain-view")
            canon = load_canon(args.canon_folder)
            view = load_view(args.canon_folder, args.explain_view)
            plan = compile_view(canon, view)
            projection = project_view(canon, view, plan=plan)
            trace = explain_artifact(canon, plan, projection, args.artifact)
            rendered = (
                json.dumps(trace, ensure_ascii=False, indent=2, default=str) + "\n"
                if args.json
                else format_explanation(trace)
            )
            _emit(args, rendered)
            return 0

        if args.write_lock:
            parser.error("--write-lock applies to --validate-view")

        canon = load_canon(args.canon_folder)
        if args.all_views:
            views = list_views(args.canon_folder)
        elif args.everything:
            views = [builtin_everything()]
        else:
            views = [load_view(args.canon_folder, path) for path in args.view]
        projections = project_views(canon, views)
        for view, projection in zip(views, projections):
            for warning in projection["warnings"]:
                prefix = f"{view.relative_path}: " if len(views) > 1 else ""
                print(f"warning: {prefix}{warning}", file=sys.stderr)
        if args.json:
            if args.vendor:
                parser.error("--vendor applies to HTML output, not --json")
            payload = projections[0] if len(projections) == 1 else {"views": projections}
            rendered = json.dumps(
                payload, ensure_ascii=False, indent=2, default=str
            ) + "\n"
        else:
            if args.output is None:
                parser.error("HTML rendering requires -o/--output")
            render_args = {
                "vendor": args.vendor,
                "vendor_dir": Path(__file__).resolve().parent / "vendor",
            }
            if len(projections) == 1:
                rendered = render_graph(projections[0], canon, **render_args)
            else:
                rendered = render_graph_document(
                    projections,
                    canon,
                    explicit_layouts=["layout" in view.data for view in views],
                    view_paths=[view.relative_path for view in views],
                    **render_args,
                )
    except (CanonLoadError, ViewLoadError, ModuleError, CompileError, RenderError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    _emit(args, rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
