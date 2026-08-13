# Troubleshooting

Failures that actually happen, and the shortest path from each to knowing what
is wrong.

Two commands answer most questions. **`wb doctor`** reports what the tooling
found and what it did not, which separates a bad install from a bad path.
**`wb session <world>`** reports what a canon contains, which separates a
missing artifact from a hidden one. Ask the agent to run either.

---

## The plugin does not seem to be there

**The agent does not mention worldbuilding at all.** Restart the host. Plugins
load at startup, so a plugin installed mid-session is not there yet. If you
built from a clone, `.\update-plugins.ps1` and then restart.

**It knows about the skill but nothing runs.** Ask for `wb doctor`. It prints
where it looked and what it found:

```
wb 0.1  python 3.10.12  PyYAML 6.0.3
install: .../src/wb
  apply          .../scripts/apply.py
  validate       .../scripts/validate.py
  view           .../viewer/view.py
  kernel         .../Specification/KERNEL.md
```

A missing line there means a broken install rather than a broken world.

---

## Python

**"Bundled Python launcher not found"** — the plugin's launcher is missing or
in the wrong place. This is an install problem: reinstall, or rebuild from your
clone.

**The launcher cannot find a runtime.** It probes known locations and reports
the one blocker it ended on. You need **Python 3.10 or newer** on your PATH:

```powershell
python --version
```

If that prints nothing useful, install from
[python.org](https://www.python.org/downloads/) and tick **Add python.exe to
PATH** in the installer — the box is easy to miss and it is the usual cause.

**You should never need to install anything else.** The YAML parser and the
graph library are bundled. If you are being asked to `pip install` something,
that is a bug worth reporting.

---

## The canon

### "Which folder?" — it cannot find your world

A canon is a folder containing `world.yaml`. If the agent asks rather than
guessing, that is deliberate: your working directory is usually a project root,
and seeding a world into it would scatter `entities/` among unrelated files.

Name the folder explicitly once — "my world in `Worlds/Hask`" — and it stays
resolved for the session.

### The validator reports errors

Errors are mechanical and each names the file:

```
ERROR: relations/bad-participation: role 'action' bound to type 'person', requires ['action']
ERROR: relations/marrow-reach-in-the-fen: dangling reference 'entities/the-marsh'
```

**Dangling reference** — a member points at an id that does not exist. Usually
a typo or something renamed without updating what pointed at it.

**Duplicate id** — two files declare the same `id:`. Note that the id, not the
path, is authoritative; a copied file with an unedited id causes this.

**Constraint violated** — a member is not what its own type file demands. Fix
the member, relax the type, or mark the artifact `fiat: true` if the violation
is the point.

**`fiat` does not fix everything, and should not.** It downgrades violations of
*declared rules* to notices. A dangling reference stays an error, because that
is a broken file rather than a claim about your world.

### The index is stale

```
index:     stale (1 artifact(s) missing, 0 no longer present)
```

Expected after hand-editing. `INDEX.md` is generated for lookup and is not a
source of truth — nothing breaks while it is stale. Ask for a reindex, or:

```
wb reindex <world>
```

### Warnings about missing provenance

```
WARNING: 28 artifact(s) have no scribe.origin/scribe.session in a world that
stamps provenance (...)
```

Expected in a world you partly hand-wrote and partly captured. The check is
all-or-nothing: one stamped artifact makes every unstamped one visible. It is a
note about mixed authorship, not a fault, and it is safe to ignore.

---

## Views

### The view is empty, or something is missing from it

**Render `Everything` first.** It ignores every selection and style you have
declared and shows drafts. If the artifact is there, your view is filtering it
out; if it is not, it is not in the canon. That is the whole diagnostic.

If it is a filtering problem, check in this order: `status` (does the view
select `draft`?), `kinds` (does it list the kind you are looking for?), then
`edges.include` — a relation whose type is not included does not draw, and an
artifact connected only by that relation may vanish with it.

### The picture is one very wide row

Your view nests something and asked for `dagre`, which cannot lay out nested
graphs. The viewer substitutes `fcose` and says so in the warnings. Set
`layout: fcose` in the view to stop being told.

### The layout is not what I asked for

```
[view.unknown-layout] views/typo.yaml: unknown layout 'dagr'; using fcose
(known: concentric, dagre, fcose, preset)
```

A misspelling. The four known layouts are the four named in that message.

### Edges disappear while I pan or drag

Deliberate, above sixty edges: dropping them during interaction is what keeps a
large nested graph responsive. They come back the moment you stop. Below sixty
edges nothing is dropped, so if you are seeing it on a small world, that is
worth reporting.

### A composed view draws something and I cannot see why

```
wb explain <world> --view views/mine.yaml --artifact entities/the-thing
```

It names the module and the rule index behind every property, and reports the
overrides. This is the tool for exactly this question; guessing is slower.

### `lock: stale`

Not an error. A module or the type vocabulary underneath the view has changed
since you last recorded its dependencies. The view still works — you are being
told why the picture may differ. Re-record with `--write-lock` when the change
is one you wanted.

---

## Rendering

**The file opens but the graph is blank**, with a message about Cytoscape not
loading. The render was made without `--vendor` and has no network. Re-render
with `--vendor` to inline the assets.

**The file is large.** A vendored render is around 850 KB almost regardless of
world size, because the browser assets dominate — the sixteen-artifact example
weighs the same as a world twenty times its size. That is the price of a file
that opens with no network in ten years.

---

## Reporting something

Include the host and OS, the plugin version, what you asked for, and what
happened instead. If a canon is involved, paste the output of `wb session` and
`wb validate` — both report structure and counts rather than the contents of
your world, so they are safe to share.

The bugs worth reporting most are the ones where **nothing failed**: a picture
that was quietly wrong, a validation that passed when it should not have, a
warning that never came. Those are the ones tests do not catch, and this
project has shipped several.
