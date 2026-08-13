#!/usr/bin/env python3
"""Development server for the canon viewer — NOT part of the shipped tool.

The shipped viewer is `view.py`: one command, one self-contained HTML file,
no server. That stays true. This is a workbench for iterating: one browser
tab, a world picker, a view dropdown, and a reload button that re-reads the
canon from disk so you see edits without rebuilding anything.

It deliberately imports the same `viewer` package the CLI uses, so there is
exactly one implementation of load and projection. Nothing here is
reimplemented in JavaScript, and nothing here writes to your canon.

    python devserver.py                 # http://127.0.0.1:8000
    python devserver.py --port 880 --root G:\\WB\\Worlds

Future: this is the natural seed for an editor. Write endpoints are absent
on purpose — adding them is a deliberate act, not an accident.
"""
from __future__ import annotations

import argparse
import html
import json
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from viewer.load import (
    CanonLoadError,
    ViewLoadError,
    list_views,
    load_canon,
)
from viewer.compile import CompileError
from viewer.modules import ModuleError
from viewer.project import project_views
from viewer.render_graph import render_graph, render_graph_document

HERE = Path(__file__).resolve().parent
WB = HERE.parent.parent
VENDOR = HERE / "vendor"

# Folders scanned for worlds (any directory containing world.yaml, 2 deep).
DEFAULT_ROOTS = [WB / "Testing", WB / "Worlds", WB / "Examples", WB / "src"]

def discover_worlds(roots: list[Path]) -> list[Path]:
    found: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        for manifest in sorted(root.glob("*/world.yaml")) + sorted(
            root.glob("*/*/world.yaml")
        ):
            world = manifest.parent
            if world not in found:
                found.append(world)
    return found


def toolbar(worlds: list[Path], world: Path | None) -> str:
    options = []
    for candidate in worlds:
        label = str(candidate).replace(str(WB) + "/", "").replace(str(WB) + "\\", "")
        sel = " selected" if world and candidate == world else ""
        options.append(
            f'<option value="{html.escape(str(candidate))}"{sel}>{html.escape(label)}</option>'
        )
    return f"""<div id="devbar">
  <span class="devbar-tag">dev</span>
  <select id="devbar-world" title="World">{''.join(options)}</select>
  <button id="devbar-reload" title="Re-read the canon from disk">Reload</button>
  <a id="devbar-json" href="#" title="Inspect the projection JSON">json</a>
</div>
<style>
 #devbar{{position:fixed;top:0;left:0;right:0;z-index:9999;display:flex;gap:8px;
   align-items:center;padding:7px 12px;background:#191712;border-bottom:1px solid #35302a;
   font:13px ui-sans-serif,system-ui,sans-serif;color:#e8e3d9}}
 #devbar .devbar-tag{{font-size:10px;letter-spacing:.08em;text-transform:uppercase;
   color:#12110f;background:#c9a227;border-radius:3px;padding:2px 6px;font-weight:700}}
 #devbar select,#devbar button{{background:#12110f;color:#e8e3d9;border:1px solid #3a352d;
   border-radius:5px;padding:5px 8px;font:inherit;max-width:38vw}}
 #devbar button{{cursor:pointer}} #devbar button:hover{{border-color:#7a6f5c}}
 #devbar a{{color:#8b8377;text-decoration:none;font-size:12px;margin-left:auto}}
 #devbar a:hover{{color:#c9a227}}
 body{{padding-top:42px !important}}
</style>
<script>
(function(){{
  const w=document.getElementById("devbar-world");
  const go=(json)=>{{const u=new URL(location.href);u.pathname=json?"/json":"/";
    u.searchParams.set("world",w.value);location.href=u;}};
  w.addEventListener("change",()=>{{const u=new URL(location.href);
    u.searchParams.set("world",w.value);location.href=u;}});
  document.getElementById("devbar-reload").addEventListener("click",()=>location.reload());
  document.getElementById("devbar-json").addEventListener("click",(e)=>{{e.preventDefault();go(true);}});
}})();
</script>"""


def page(body: str, title: str = "Canon viewer — dev") -> bytes:
    return f"""<!doctype html><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>body{{font:15px/1.6 ui-sans-serif,system-ui,sans-serif;background:#12110f;
 color:#e8e3d9;margin:0;padding:60px 40px;max-width:820px}}
 h1{{font-size:19px}} code,pre{{color:#c9a227}} pre{{white-space:pre-wrap}}
 a{{color:#c9a227}}</style>{body}""".encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    roots: list[Path] = DEFAULT_ROOTS

    def log_message(self, fmt, *args):  # quieter console
        pass

    def _send(self, payload: bytes, status: int = 200, ctype: str = "text/html") -> None:
        self.send_response(status)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        worlds = discover_worlds(self.roots)

        if parsed.path not in {"/", "/json"}:
            self._send(page("<h1>Not found</h1>"), 404)
            return
        if not worlds:
            roots = "".join(f"<li><code>{html.escape(str(r))}</code></li>" for r in self.roots)
            self._send(page(
                f"<h1>No worlds found</h1><p>Looked for <code>world.yaml</code> under:</p>"
                f"<ul>{roots}</ul><p>Pass another with <code>--root</code>.</p>"), 404)
            return

        want = params.get("world", [None])[0]
        world = Path(want).resolve() if want else worlds[0]
        # Discovered worlds only. A path carrying a world.yaml is NOT enough:
        # the query string must never widen what the process can read beyond
        # its configured roots. This boundary has to exist before any write
        # endpoint does, and it is cheaper to hold it from the start.
        if world not in worlds:
            hint = "not under a configured root — restart with --root" \
                if (world / "world.yaml").is_file() else "no world.yaml there"
            self._send(page(
                f"<h1>Not an available world</h1>"
                f"<p><code>{html.escape(str(world))}</code> — {hint}.</p>"
                f'<p><a href="/">back</a></p>'), 403)
            return

        try:
            canon = load_canon(world)
            views = list_views(world)
            loaded_views = views
            projections = project_views(canon, loaded_views)

            if parsed.path == "/json":
                payload = projections[0] if len(projections) == 1 else {"views": projections}
                self._send(json.dumps(payload, indent=2, ensure_ascii=False,
                                      default=str).encode("utf-8"),
                           ctype="application/json")
                return

            if len(projections) == 1:
                document = render_graph(
                    projections[0], canon, vendor=True, vendor_dir=VENDOR
                )
            else:
                document = render_graph_document(
                    projections,
                    canon,
                    explicit_layouts=["layout" in view.data for view in loaded_views],
                    view_paths=[view.relative_path for view in loaded_views],
                    vendor=True,
                    vendor_dir=VENDOR,
                )
            bar = toolbar(worlds, world)
            document = document.replace("<body>", "<body>" + bar, 1)
            self._send(document.encode("utf-8"))
        except (CanonLoadError, ViewLoadError, ModuleError, CompileError) as exc:
            self._send(page(f"<h1>Cannot load</h1><pre>{html.escape(str(exc))}</pre>"
                            f'<p><a href="/">back</a></p>'), 400)
        except Exception:  # noqa: BLE001 — a dev tool should show its own stack
            self._send(page(f"<h1>Viewer error</h1><pre>"
                            f"{html.escape(traceback.format_exc())}</pre>"), 500)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--root", action="append", type=Path,
                    help="folder to scan for worlds (repeatable)")
    args = ap.parse_args()
    Handler.roots = [Path(r).expanduser().resolve() for r in args.root] if args.root \
        else DEFAULT_ROOTS
    found = discover_worlds(Handler.roots)
    print(f"canon viewer (dev) — {len(found)} world(s)")
    for world in found:
        print(f"  {world}")
    print(f"\n  http://{args.host}:{args.port}/\n  ctrl-c to stop")
    try:
        ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()
    except KeyboardInterrupt:
        print("stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
