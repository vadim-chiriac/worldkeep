# Development

How to build, test and change Worldkeep itself. If you only want to *use* it,
you want [GETTING-STARTED.md](GETTING-STARTED.md) instead.

---

## Repository layout

The source layout mirrors the shipped layout, so the build is close to a
one-to-one copy rather than a collection from unrelated folders.

```
src/
  skills/worldbuilding-scribe/   SKILL.md, scripts/, assets/seed-world/, tests/
  skills/canon-viewer/           SKILL.md, assets/views-library/
  viewer/                        viewer implementation and tests
  wb/                            the wb agent entrypoint and tests
  runtime/                       Python launchers, one vendored PyYAML copy
Specification/                   KERNEL.md, SCRIBE.md — normative, shipped verbatim
Documentation/                   user documentation
Internal/                        design notes and spec history; not distributed
Testing/                         fixtures the suites assert against, run evidence
Examples/                        example worlds
dist/                            generated release artifacts
plugins/worldkeep/               generated local Codex marketplace mirror
```

**`dist/` and `plugins/worldkeep/` are generated.** Never edit them; edit the
source they are built from. `build.py --check` re-derives both and
fails on drift — it exists because hand-copying drifted twice in one afternoon
under active supervision.

---

## The one command

After changing anything that feeds the plugin:

```powershell
.\update-plugins.ps1
```

That runs the writer, viewer and CLI suites through `build.py`, rebuilds the
artifacts, verifies both manifests, refreshes the local marketplace mirror, and
gives the Codex manifest a fresh cache-busting version.

For a read-only drift check that writes nothing:

```powershell
.\update-plugins.ps1 -Check
```

Restart the host application afterwards so it reloads the plugin.

### Running pieces directly

```powershell
python build.py              # build and package everything
python build.py --check      # verify only; exit 1 if dist is stale or drifted
```

The test suites can be run on their own while iterating. Each resolves imports
against its own package, so run them from their own directory — which is what
`build.py` does:

```powershell
cd src\viewer                    ; python -m pytest tests
cd src\wb                        ; python -m pytest tests
cd src\skills\worldbuilding-scribe ; python tests\test_apply.py
```

---

## Versioning

Three version numbers move independently, and none of them is guessed by the
pipeline:

| version | where it lives | when it changes |
|---|---|---|
| plugin | `PLUGIN_VERSION` in `build.py` | any release-worthy change |
| kernel | first heading of `Specification/KERNEL.md` | a change to the data model |
| scribe | first heading of `Specification/SCRIBE.md` | a change to the capture loop |

The build reads the kernel and scribe versions out of those headings and stamps
them into the Claude manifest's metadata, so a released plugin always says which
specification it carries. The seed world's `world.yaml` must name the current
kernel version; the build fails if it drifts.

Cumulative specification history lives in `Specification/SPEC-HISTORY.md`, not in the
shipped documents — the specs stay focused on current normative behaviour.

---

## Required project record

**Every change adds an entry under `CHANGELOG.md` > `Unreleased` before it is
finished.** This is enforced: `update-plugins.ps1` refuses to run if source
files changed without a changelog update.

Describe the user-visible or developer-visible result, not the commands you ran.
Do not rewrite released history. One entry may cover a source edit and the
generated artifacts refreshed from it.

`AGENTS.md` is the canonical workflow policy for both human and AI contributors;
`CLAUDE.md` points at it so there is one document, not two.

---

## Reproducible builds

Every file in the bundle is copied byte-for-byte except the two generated plugin
manifests, which are written with an explicit `newline="\n"` so the build does
not depend on the operating system that ran it. `dist/BUILD.txt` records a
SHA-256 for every file in both skills.

If you change how a manifest is written, keep the explicit newline. Without it,
`dist/plugin.zip` hashes differently on Windows than everywhere else and
`build.py --check` fails outside Windows.

---

## Vendored dependencies

PyYAML is vendored once, at `src/runtime/_vendor`, and copied into both skill
bundles at build time. The viewer vendors Cytoscape under `src/viewer/vendor`.
Both are bundled so a render still opens with no network years from now, and so
the agent never has to talk to the user about installing dependencies.

Their licences are recorded in `THIRD-PARTY-NOTICES.md` and must stay there.

---

## Deleting things

Only two paths are ever deleted by tooling, and both are generated: `build.py`
may delete and recreate `dist/plugin/`, and `update_plugins.py` may delete and
recreate `plugins/worldkeep/` after verifying it is still under the
repository's `plugins` directory. Anything else — fixtures especially — stays.

`src/viewer/out/` and `src/viewer/gallery/` are scratch render output and are
gitignored; delete them freely.
