#!/usr/bin/env python3
"""Build a browsable gallery: one multi-view document per active world.

Manual-testing harness, not part of the shipped viewer. Retained `Testing/runs`
evidence is deliberately excluded. It copies the shared
views in `views-library/` into each world (worlds keep their own `views/`
folder per the spec), renders one offline HTML document per world with
`--vendor`, and writes an index page so everything is reachable by clicking.

Usage:
    python3 build_gallery.py                 # all known worlds
    python3 build_gallery.py --only marrow   # substring filter on world name
"""
from __future__ import annotations

import argparse
import html
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WB = HERE.parent.parent
GALLERY = HERE / "gallery"
LIBRARY = HERE / "views-library"

# label -> active/current canon folder. Do not add retained Testing/runs evidence.
WORLDS: dict[str, Path] = {
    "marrow-reach (live)": WB / "Testing" / "dry-run-world",
    "tarn-hollow (skill sanity)": WB / "Testing" / "skill-sanity",
    "seed template (empty)": WB / "src" / "skills" / "worldbuilding-scribe" / "assets" / "seed-world",
}


def slug(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")


def build(only: str | None) -> int:
    GALLERY.mkdir(parents=True, exist_ok=True)
    views = sorted(LIBRARY.glob("*.yaml"))
    rows: list[dict] = []

    for label, canon in WORLDS.items():
        if only and only.lower() not in label.lower():
            continue
        if not (canon / "world.yaml").is_file():
            print(f"skip {label}: no world.yaml at {canon}", file=sys.stderr)
            continue

        (canon / "views").mkdir(exist_ok=True)
        for view in views:
            shutil.copyfile(view, canon / "views" / view.name)

        artifacts = len([p for p in canon.rglob("*.md") if "views" not in p.parts])
        out = GALLERY / f"{slug(label)}.html"
        cmd = [sys.executable, str(HERE / "view.py"), str(canon),
               "--all-views", "--vendor", "-o", str(out)]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=HERE)
        warnings = [ln for ln in proc.stderr.splitlines() if ln.startswith("warning:")]
        entry = {
            "label": label,
            "path": str(canon),
            "artifacts": artifacts,
            "view_count": len(views),
            "file": out.name if proc.returncode == 0 else None,
            "ok": proc.returncode == 0,
            "warnings": len(warnings),
            "error": "" if proc.returncode == 0 else proc.stderr.strip()[-300:],
        }
        rows.append(entry)

    (GALLERY / "index.html").write_text(render_index(rows), encoding="utf-8")
    ok = sum(1 for row in rows if row["ok"])
    print(f"{ok}/{len(rows)} multi-view documents rendered")
    print(f"open: {GALLERY / 'index.html'}")
    return 0 if ok == len(rows) else 1


def render_index(rows: list[dict]) -> str:
    cards = []
    for r in rows:
        if r["ok"]:
            warn = f' <span class="w">{r["warnings"]}⚠</span>' if r["warnings"] else ""
            link = f'<a href="{r["file"]}">open {r["view_count"]} views{warn}</a>'
        else:
            link = f'<span class="bad" title="{html.escape(r["error"])}">render failed</span>'
        cards.append(
            f'<section><h2>{html.escape(r["label"])}</h2>'
            f'<p class="meta">{r["artifacts"]} files · <code>{html.escape(r["path"])}</code></p>'
            f'<div class="links">{link}</div></section>'
        )
    return f"""<!doctype html><meta charset="utf-8">
<title>Canon viewer — gallery</title>
<style>
 body{{font:15px/1.5 ui-sans-serif,system-ui,sans-serif;margin:0;padding:40px;
      background:#12110f;color:#e8e3d9;max-width:900px}}
 h1{{font-size:22px;margin:0 0 4px}} .sub{{color:#8b8377;margin:0 0 32px}}
 section{{border-top:1px solid #2b2823;padding:20px 0}}
 h2{{font-size:16px;margin:0 0 2px;font-weight:600}}
 .meta{{color:#8b8377;font-size:12px;margin:0 0 12px}}
 code{{color:#6f6759}}
 .links{{display:flex;flex-wrap:wrap;gap:8px}}
 a{{display:inline-block;padding:7px 13px;border:1px solid #3a352d;border-radius:6px;
    color:#e8e3d9;text-decoration:none;background:#1a1815;font-size:13px}}
 a:hover{{border-color:#7a6f5c;background:#221f1a}}
 .w{{color:#c9a227;font-size:11px}}
 .bad{{padding:7px 13px;border:1px dashed #6b3b3b;border-radius:6px;color:#c86b6b;font-size:13px}}
</style>
<h1>Canon viewer — gallery</h1>
<p class="sub">One portable multi-view document per world. Regenerate with
<code>python3 build_gallery.py</code>.</p>
{"".join(cards)}
"""


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="substring filter on world label")
    raise SystemExit(build(ap.parse_args().only))
