# Installation

Worldkeep is a plugin containing two skills. Installing it means telling your AI
host where to find the plugin; there is no service to sign up for, nothing runs
in the background, and nothing phones home.

**Supported for this release: Claude and ChatGPT/Codex, on Windows.** The
macOS and Linux launchers ship in the bundle but have not been verified, so
they are not claimed. See [Other operating systems](#other-operating-systems).

---

## Before you start

You need **Python 3.10 or newer** on your PATH. Everything else the plugin
needs — the YAML parser, the graph library — is bundled, so there is nothing to
`pip install` and no virtual environment to manage.

Check it:

```powershell
python --version
```

If that prints a version below 3.10, or is not recognised at all, install
Python from [python.org](https://www.python.org/downloads/) and tick **Add
python.exe to PATH** in the installer.

---

## Claude

Claude installs plugins from a **marketplace**, which is just a repository
containing a catalogue file. Add the marketplace once, then install from it.

```
/plugin marketplace add vadim-chiriac/worldkeep
/plugin install worldkeep@worldkeep
```

Restart Claude afterwards so it loads the plugin.

To check it took, ask for something a skill handles:

> Show me what worldbuilding skills you have.

You should see **worldbuilding-scribe** and **canon-viewer**.

### Installing from a local clone instead

If you would rather read the source before running it — a reasonable habit for
any plugin — clone the repository and point Claude at the folder:

```powershell
git clone https://github.com/vadim-chiriac/worldkeep.git
```

```
/plugin marketplace add ./worldkeep
/plugin install worldkeep@worldkeep
```

---

## ChatGPT / Codex

ChatGPT and Codex use the catalogue at `.agents/plugins/marketplace.json`. Add
the public repository as a marketplace from a terminal:

```powershell
codex plugin marketplace add vadim-chiriac/worldkeep --ref main
codex plugin marketplace list
```

Then restart the ChatGPT desktop app, open **Plugins Directory**, choose the
**Worldkeep** marketplace and install **worldkeep**. Start a new chat after
installation so the two skills are loaded into the conversation.

This repository marketplace is the direct GitHub distribution route. A listing
in the universal public Plugins Directory shared by ChatGPT and Codex is a
separate release step that requires submission and review by OpenAI.

### Installing ChatGPT / Codex from a local clone instead

Clone the repository, then register the clone as the marketplace root:

```powershell
git clone https://github.com/vadim-chiriac/worldkeep.git
codex plugin marketplace add .\worldkeep
```

Restart the ChatGPT desktop app and install **worldkeep** from the
**Worldkeep** source in Plugins Directory.

---

## Verifying the installation

The surest check is to make the tooling talk. Point the agent at any folder
containing a `world.yaml` — `Examples/lower-fen` in the repository will do —
and ask:

> What's in this world?

A working installation reports the world's name, its artifact counts by kind,
the type vocabulary in play and the views available. If instead you are told a
tool cannot be found, run the diagnostic:

> Run wb doctor.

It reports which of the packaged tools it located and which it did not, which
is the fastest way to tell a bad install from a bad path.

---

## Updating

**Claude:** refresh the marketplace, then update or reinstall the plugin from
Claude's plugin manager:

```
/plugin marketplace update worldkeep
```

**ChatGPT / Codex:** refresh the marketplace snapshot, restart the desktop app,
then update or reinstall **worldkeep** from Plugins Directory:

```powershell
codex plugin marketplace upgrade worldkeep
```

**From a local clone:** pull the released files and restart the host:

```powershell
git pull
```

`update-plugins.ps1` is the maintainer build pipeline; users installing a
released plugin do not need to run it.

**Your worlds are not touched by an update.** A canon is a folder of your own
files, entirely outside the plugin. That is also why nothing migrates them: see
[Limitations](LIMITATIONS.md).

---

## Uninstalling

In Claude:

```
/plugin uninstall worldkeep@worldkeep
```

Optionally remove the marketplace as well:

```
/plugin marketplace remove worldkeep
```

In ChatGPT / Codex, uninstall or disable **worldkeep** in Plugins Directory.
To forget the repository marketplace as well:

```powershell
codex plugin marketplace remove worldkeep
```

**Your worlds survive.** They are plain Markdown and YAML in whatever folder
you chose, and nothing about them requires this plugin — they remain readable,
diffable and editable in any text editor. Rendered views are self-contained
HTML with no external dependencies, so they keep opening too.

---

## Other operating systems

The bundle ships `run-python.sh` alongside the Windows `run-python.ps1`, and
nothing in the code is Windows-specific — the paths, the launchers and the
build are all platform-neutral, and the build itself is byte-reproducible
across platforms.

What is missing is verification, not capability. The pipeline has not been run
end to end on macOS or Linux, so claiming support would be a guess. If you try
it there and it works, that is worth reporting; if it breaks, the failure is
likely to be one line in a launcher.

---

## If something goes wrong

[TROUBLESHOOTING.md](TROUBLESHOOTING.md) covers the failures that actually
happen: Python not found, the launcher exhausting its candidates, a plugin that
will not reload, an empty view.
