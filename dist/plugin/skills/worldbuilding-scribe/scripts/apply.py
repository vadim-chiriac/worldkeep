#!/usr/bin/env python3
"""SCRIBE.md §11 apply script — the single path canon is written through.

Usage:
  apply.py <world-folder> --session <id> [--status draft|canon]
           [--input-file artifacts.json]
      Write or update one or more artifacts. Reads a JSON array from
      --input-file, or from stdin when that option is omitted. Stamps
      scribe.origin/scribe.session
      (SCRIBE.md §6), runs the validator, and reports exactly what was
      written.

  apply.py <world-folder> --promote <id> [<id> ...]
      Flip status: draft -> canon for each id. A single-field change: the
      rest of the file is left byte-identical.

  apply.py <world-folder> --reject <id> [<id> ...]
      Delete the draft file for each id. If another artifact references it
      (members/where/when), warns which ones will be left dangling before
      deleting — still deletes; the scribe decides, this just surfaces the
      decision instead of leaving it for the next validator run. Reports
      plainly if a delete fails; never silently leaves a false status.

  apply.py <world-folder> --find <query> [--limit N]
      Case-insensitive substring lookup across id, name, and tags. Defaults
      to 20 results and reports when matches were truncated.

  apply.py <world-folder> --index [--kind K] [--type GLOB]
           [--status S] [--limit N]
      Compact id/kind/type/name listing. Filters compose; --type uses the
      same type-path glob semantics as viewer select.types.

  apply.py <world-folder> --reindex
      Regenerate the disposable INDEX.md at the world root.

Successful writes, promotions, and rejections regenerate INDEX.md.

Exit codes (write/promote/reject/reindex): 0 if every item succeeded, 1 if any item
failed (checked, not inferred — see cmd_write/cmd_promote/cmd_reject), 2 on
a usage error (bad flags, unparseable JSON). --find and --index always exit 0.

Lookup commands exit 0, including a zero-match --find. --reindex exits 1
only if INDEX.md could not be written.

Artifact JSON shape (one element of the array):
  {
    "id": "entities/marrow-reach",   # required; also the file path
    "kind": "entity",                # required; entity|idea|relation|type
    "type": "place/village",         # optional
    "name": "Marrow Reach",          # optional
    "tags": ["fen", "ford"],         # optional
    "body": "Free-form markdown...", # optional; defaults to empty
    "status": "draft",               # optional; overrides --status for this item
    "scribe.origin": "mixed",        # optional; overrides default ("mixed")
    ... any other facet/field (when, where, members, amount, valence,
        weight, fiat, constraints, lens, applies_to_kind, ...) passed
        through verbatim into the frontmatter.
  }

Field order on disk (matches the hand-written convention already in use):
  id, kind, type, name, tags, <everything else, input order>, status,
  scribe.origin, scribe.session.
"""
import sys, os, re, json, subprocess
from fnmatch import fnmatchcase

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENDOR_DIRS = (
    os.path.join(SCRIPT_DIR, "_vendor"),
    os.path.abspath(os.path.join(
        SCRIPT_DIR, "..", "..", "..", "runtime", "_vendor")),
)
for vendor_dir in VENDOR_DIRS:
    if os.path.isdir(vendor_dir):
        sys.path.insert(0, vendor_dir)
        break

HEAD_KEYS = ["id", "kind", "type", "name", "tags"]
TAIL_KEYS = ["status", "scribe.origin", "scribe.session"]
RESERVED = set(HEAD_KEYS) | set(TAIL_KEYS) | {"body"}

try:
    import yaml
except ImportError:
    print("pyyaml required"); sys.exit(2)


def here():
    return os.path.dirname(os.path.abspath(__file__))


def find_validator():
    cand = os.path.join(here(), "validate.py")
    return cand if os.path.exists(cand) else None


def build_frontmatter(art, session, default_status):
    lines = []
    used = set()

    def emit(key, value):
        used.add(key)
        # Dump the complete mapping entry instead of trying to splice a bare
        # value after ``key:``. A one-item list dumps as ``- item`` with no
        # internal newline, so value-based branching produced invalid YAML
        # such as ``where: - entities/kings-landing``.
        block = yaml.dump(
            {key: value},
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
        lines.append(block.rstrip("\n"))

    for k in HEAD_KEYS:
        if k in art and art[k] is not None:
            emit(k, art[k])

    for k, v in art.items():
        if k in RESERVED or k in used:
            continue
        emit(k, v)

    status = art.get("status", default_status)
    emit("status", status)

    origin = art.get("scribe.origin", "mixed")
    emit("scribe.origin", origin)

    sess = art.get("scribe.session", session)
    if sess:
        emit("scribe.session", sess)

    return "\n".join(lines)


def write_artifact(world, art, session, default_status):
    aid = art.get("id")
    kind = art.get("kind")
    if not aid:
        return None, "missing 'id'"
    if not kind:
        return None, f"{aid}: missing 'kind'"
    rel = aid + ".md"
    path = os.path.join(world, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fm = build_frontmatter(art, session, default_status)
    body = art.get("body") or ""
    text = f"---\n{fm}\n---\n"
    if body:
        text += f"\n{body.rstrip()}\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return aid, None


def cmd_write(world, session, default_status, input_file=None):
    try:
        if input_file:
            with open(input_file, encoding="utf-8") as handle:
                raw = handle.read()
        else:
            raw = sys.stdin.read()
    except OSError as e:
        print(f"could not read input JSON: {e}")
        sys.exit(2)
    try:
        artifacts = json.loads(raw) if raw.strip() else []
    except Exception as e:
        source = input_file or "stdin"
        print(f"invalid JSON from {source}: {e}")
        sys.exit(2)
    if isinstance(artifacts, dict):
        artifacts = [artifacts]

    written, failed = [], []
    for art in artifacts:
        aid, err = write_artifact(world, art, session, default_status)
        if err:
            failed.append(err)
        else:
            written.append(aid)

    print(f"wrote {len(written)} artifact(s) (session {session}, status "
          f"{default_status}):")
    for aid in written:
        print(f"  {aid}")
    if failed:
        print(f"failed ({len(failed)}):")
        for e in failed:
            print(f"  {e}")

    index_ok = regenerate_index(world) if written else True
    run_validator(world)
    sys.exit(1 if failed or not index_ok else 0)


def load_frontmatter_text(path):
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    m = re.match(r"^---\n(.*?\n)---\n?", text, re.S)
    if not m:
        return None, text
    return m.group(1), text


def find_path_for_id(world, aid):
    p = os.path.join(world, aid + ".md")
    if os.path.exists(p):
        return p
    # id: field may not match path (warned by the validator, not fatal here)
    # — fall back to a scan.
    for dirpath, _, files in os.walk(world):
        for fn in files:
            if not fn.endswith(".md"):
                continue
            fp = os.path.join(dirpath, fn)
            fm_text, _ = load_frontmatter_text(fp)
            if fm_text is None:
                continue
            try:
                fm = yaml.safe_load(fm_text) or {}
            except Exception:
                continue
            if fm.get("id") == aid:
                return fp
    return None


def all_artifacts(world):
    """(id, rel-path, frontmatter-dict) for every artifact in the world,
    skipping the plain-prose files the validator also skips."""
    out = []
    for dirpath, _, files in os.walk(world):
        for fn in files:
            if not fn.endswith(".md"):
                continue
            fp = os.path.join(dirpath, fn)
            rel = os.path.relpath(fp, world)[:-3].replace(os.sep, "/")
            fm_text, _ = load_frontmatter_text(fp)
            if fm_text is None:
                if rel.upper().startswith(("FRICTION", "README", "MANIFEST")):
                    continue
                continue
            try:
                fm = yaml.safe_load(fm_text) or {}
            except Exception:
                continue
            out.append((fm.get("id", rel), rel, fm))
    return out


def index_rows(world):
    """Display/search rows, including malformed YAML as the old --index did."""
    rows = []
    for dirpath, _, files in os.walk(world):
        for fn in sorted(files):
            if not fn.endswith(".md"):
                continue
            fp = os.path.join(dirpath, fn)
            rel = os.path.relpath(fp, world)[:-3].replace(os.sep, "/")
            fm_text, _ = load_frontmatter_text(fp)
            if fm_text is None:
                continue
            try:
                fm = yaml.safe_load(fm_text) or {}
            except Exception as e:
                rows.append((rel, "?", "", f"<yaml error: {e}>", [], ""))
                continue
            aid = fm.get("id", rel)
            tags = fm.get("tags") or []
            if isinstance(tags, str):
                tags = [tags]
            elif not isinstance(tags, list):
                tags = []
            rows.append((aid, fm.get("kind", ""), fm.get("type", "") or "",
                         fm.get("name", "") or "", tags,
                         fm.get("status", "canon") or "canon"))
    rows.sort(key=lambda row: row[0])
    return rows


def print_rows(rows):
    for aid, kind, typ, name, _, _ in rows:
        print(f"  {aid:<40} {kind:<9} {typ:<24} {name}")


def limited(rows, limit):
    if limit is None or len(rows) <= limit:
        return rows, False
    return rows[:limit], True


def type_matches(type_path, pattern):
    if type_path:
        return fnmatchcase(type_path, pattern)
    return pattern in ("*", "<untyped>")


def filter_rows(rows, kind=None, type_pattern=None, status=None):
    return [
        row for row in rows
        if (kind is None or row[1] == kind)
        and (type_pattern is None or type_matches(row[2], type_pattern))
        and (status is None or row[5] == status)
    ]


def markdown_cell(value):
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def write_index(world):
    """Regenerate the disposable, human-readable world index atomically."""
    rows = [row for row in index_rows(world) if row[1] != "?"]
    grouped = {}
    for row in rows:
        grouped.setdefault(row[1] or "unknown", []).append(row)

    kind_order = ["entity", "idea", "relation", "type"]
    ordered_kinds = [kind for kind in kind_order if kind in grouped]
    ordered_kinds += sorted(set(grouped) - set(kind_order))

    lines = [
        "<!-- GENERATED BY apply.py. DO NOT EDIT BY HAND. -->",
        "# Canon index",
        "",
        "Generated from artifact frontmatter. Artifacts are the source of truth; "
        "run `apply.py <world> --reindex` to rebuild this file.",
    ]
    for kind in ordered_kinds:
        lines += [
            "",
            f"## {kind.title()}",
            "",
            "| id | kind | type | name |",
            "|---|---|---|---|",
        ]
        for aid, row_kind, typ, name, _, _ in grouped[kind]:
            lines.append(
                f"| `{markdown_cell(aid)}` | {markdown_cell(row_kind)} | "
                f"{markdown_cell(typ)} | {markdown_cell(name)} |"
            )
    lines.append("")

    path = os.path.join(world, "INDEX.md")
    temp_path = path + ".tmp"
    try:
        with open(temp_path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines))
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    return len(rows)


def regenerate_index(world):
    try:
        count = write_index(world)
        print(f"INDEX.md: regenerated ({count} artifact(s))")
        return True
    except OSError as e:
        print(f"INDEX.md: regeneration failed ({e})")
        return False


def referring_ids(fm):
    """Every other artifact ID this artifact's frontmatter points at —
    members, where, when — same fields the validator treats as references."""
    refs = []
    for m in fm.get("members") or []:
        refs.append(m["id"] if isinstance(m, dict) else m)
    for key in ("where", "when"):
        v = fm.get(key)
        if isinstance(v, str) and "/" in v:
            refs.append(v)
        elif isinstance(v, list):
            refs += [x for x in v if isinstance(x, str) and "/" in x]
    return refs


def find_referrers(world, target_id):
    """Every artifact (other than target_id itself) that references it."""
    referrers = []
    for aid, rel, fm in all_artifacts(world):
        if aid == target_id:
            continue
        if target_id in referring_ids(fm):
            referrers.append(aid)
    return referrers


def cmd_promote(world, ids):
    ok, failed = [], []
    for aid in ids:
        path = find_path_for_id(world, aid)
        if not path:
            failed.append(f"{aid}: not found")
            continue
        fm_text, full = load_frontmatter_text(path)
        if fm_text is None:
            failed.append(f"{aid}: no frontmatter")
            continue
        new_fm_text, n = re.subn(r"(?m)^status:\s*\S+\s*$", "status: canon",
                                  fm_text, count=1)
        if n == 0:
            # no status line to flip — insert one right after the id/kind
            # block (single-field addition, still not a rewrite of the body).
            new_fm_text = fm_text.rstrip("\n") + "\nstatus: canon\n"
        new_full = full.replace(fm_text, new_fm_text, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_full)
        ok.append(aid)

    print(f"promoted {len(ok)} to canon:")
    for aid in ok:
        print(f"  {aid}")
    if failed:
        print(f"failed ({len(failed)}):")
        for e in failed:
            print(f"  {e}")
    index_ok = regenerate_index(world) if ok else True
    if ok:
        run_validator(world)
    sys.exit(1 if failed or not index_ok else 0)


def cmd_reject(world, ids):
    ok, failed, dangled = [], [], []
    for aid in ids:
        path = find_path_for_id(world, aid)
        if not path:
            failed.append(f"{aid}: not found (already gone?)")
            continue
        referrers = find_referrers(world, aid)
        if referrers:
            dangled.append((aid, referrers))
        try:
            os.remove(path)
            ok.append(aid)
        except OSError as e:
            failed.append(f"{aid}: delete failed ({e}) — status left as-is")

    if dangled:
        print("warning — deleting will leave these dangling:")
        for aid, referrers in dangled:
            print(f"  {aid} is referenced by: {', '.join(referrers)}")

    print(f"deleted {len(ok)} draft(s):")
    for aid in ok:
        print(f"  {aid}")
    if failed:
        print(f"failed ({len(failed)}):")
        for e in failed:
            print(f"  {e}")
    index_ok = regenerate_index(world) if ok else True
    if ok:
        run_validator(world)
    sys.exit(1 if failed or not index_ok else 0)


def cmd_index(world, kind=None, type_pattern=None, status=None, limit=None):
    rows = filter_rows(index_rows(world), kind, type_pattern, status)
    shown, truncated = limited(rows, limit)
    if truncated:
        print(f"artifacts: {len(rows)} (showing first {len(shown)}; truncated)")
    else:
        print(f"artifacts: {len(rows)}")
    print_rows(shown)
    sys.exit(0)


def cmd_find(world, query, limit):
    needle = query.casefold()
    matches = []
    for row in index_rows(world):
        aid, _, _, name, tags, _ = row
        haystack = [aid, name, *[tag for tag in tags if isinstance(tag, str)]]
        if any(needle in str(value).casefold() for value in haystack):
            matches.append(row)

    shown, truncated = limited(matches, limit)
    if truncated:
        print(f'{len(matches)} match(es) for "{query}" '
              f'(showing first {len(shown)}; truncated — narrow the query):')
    else:
        print(f'{len(matches)} match(es) for "{query}":')
    print_rows(shown)
    sys.exit(0)


def option_value(rest, flag, default=None):
    if flag not in rest:
        return default
    i = rest.index(flag)
    if i + 1 >= len(rest) or rest[i + 1].startswith("--"):
        print(f"{flag} requires a value"); sys.exit(2)
    return rest[i + 1]


def option_limit(rest, default=None):
    raw = option_value(rest, "--limit")
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        print("--limit must be a positive integer"); sys.exit(2)
    if value < 1:
        print("--limit must be a positive integer"); sys.exit(2)
    return value


def run_validator(world):
    validator = find_validator()
    if not validator:
        print("Validation: skipped (no validate.py found next to apply.py)")
        return
    result = subprocess.run([sys.executable, validator, world],
                             capture_output=True, text=True)
    out = result.stdout.strip()
    if result.returncode == 0 and "ERRORS: 0" in out and "WARNINGS: 0" in out:
        print("Validation: clean")
    else:
        print("Validation:")
        print(out)
        if result.stderr.strip():
            print(result.stderr.strip())


def main():
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        sys.exit(2)
    world = argv[0].rstrip("/\\")
    rest = argv[1:]

    if "--find" in rest:
        query = option_value(rest, "--find")
        cmd_find(world, query, option_limit(rest, 20))
        return

    if "--reindex" in rest:
        ok = regenerate_index(world)
        sys.exit(0 if ok else 1)

    if "--index" in rest:
        cmd_index(
            world,
            kind=option_value(rest, "--kind"),
            type_pattern=option_value(rest, "--type"),
            status=option_value(rest, "--status"),
            limit=option_limit(rest),
        )
        return

    if "--promote" in rest:
        i = rest.index("--promote")
        ids = rest[i + 1:]
        if not ids:
            print("--promote requires at least one id"); sys.exit(2)
        cmd_promote(world, ids)
        return

    if "--reject" in rest:
        i = rest.index("--reject")
        ids = rest[i + 1:]
        if not ids:
            print("--reject requires at least one id"); sys.exit(2)
        cmd_reject(world, ids)
        return

    if "--session" in rest:
        i = rest.index("--session")
        if i + 1 >= len(rest):
            print("--session requires a value"); sys.exit(2)
        session = rest[i + 1]
        status = "draft"
        if "--status" in rest:
            j = rest.index("--status")
            if j + 1 >= len(rest):
                print("--status requires a value"); sys.exit(2)
            status = rest[j + 1]
            if status not in ("draft", "canon"):
                print("--status must be 'draft' or 'canon'"); sys.exit(2)
        input_file = option_value(rest, "--input-file")
        cmd_write(world, session, status, input_file=input_file)
        return

    print(__doc__)
    sys.exit(2)


if __name__ == "__main__":
    main()
