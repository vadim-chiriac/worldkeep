#!/usr/bin/env python3
"""Build, validate, and refresh the Claude/Codex plugin outputs."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CHANGELOG = ROOT / "CHANGELOG.md"
DIST_PLUGIN = ROOT / "dist" / "plugin"
LOCAL_PLUGIN_ROOT = ROOT / "plugins"
LOCAL_PLUGIN = LOCAL_PLUGIN_ROOT / "worldkeep"
MARKETPLACE = ROOT / ".agents" / "plugins" / "marketplace.json"

GENERATED_PREFIXES = (
    "dist/",
    "plugins/worldkeep/",
    "src/viewer/gallery/",
    "src/viewer/out/",
)


def run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    shown = " ".join(command)
    print(f"> {shown}")
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def git_paths(*args: str) -> set[str]:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return {
        line.strip().replace("\\", "/")
        for line in result.stdout.splitlines()
        if line.strip()
    }


def changed_paths() -> set[str]:
    try:
        return (
            git_paths("diff", "--name-only")
            | git_paths("diff", "--cached", "--name-only")
            | git_paths("ls-files", "--others", "--exclude-standard")
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("Warning: Git status unavailable; checking changelog structure only.")
        return set()


def enforce_changelog() -> None:
    if not CHANGELOG.is_file():
        raise SystemExit("CHANGELOG.md is required.")
    if "## [Unreleased]" not in CHANGELOG.read_text(encoding="utf-8"):
        raise SystemExit("CHANGELOG.md must contain an '## [Unreleased]' section.")

    changed = changed_paths()
    source_changes = {
        path
        for path in changed
        if path != "CHANGELOG.md"
        and "__pycache__/" not in path
        and not path.endswith((".pyc", ".pyo"))
        and not path.startswith(GENERATED_PREFIXES)
    }
    if source_changes and "CHANGELOG.md" not in changed:
        examples = ", ".join(sorted(source_changes)[:5])
        raise SystemExit(
            "Source files changed without a CHANGELOG.md update. "
            f"Add an Unreleased entry first. Changed: {examples}"
        )


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Invalid or missing JSON file {path}: {exc}") from exc


def validate_dist_manifests() -> str:
    claude_path = DIST_PLUGIN / ".claude-plugin" / "plugin.json"
    codex_path = DIST_PLUGIN / ".codex-plugin" / "plugin.json"
    claude = load_json(claude_path)
    codex = load_json(codex_path)

    for host, manifest in (("Claude", claude), ("Codex", codex)):
        if manifest.get("name") != "worldkeep":
            raise SystemExit(f"{host} manifest has the wrong plugin name.")
        if not manifest.get("version"):
            raise SystemExit(f"{host} manifest has no version.")

    if claude["version"] != codex["version"]:
        raise SystemExit(
            "Claude and Codex distribution manifests have different base versions: "
            f"{claude['version']} vs {codex['version']}"
        )
    return str(codex["version"])


def validate_marketplace() -> None:
    data = load_json(MARKETPLACE)
    matches = [
        item
        for item in data.get("plugins", [])
        if item.get("name") == "worldkeep"
    ]
    if len(matches) != 1:
        raise SystemExit(
            "The personal marketplace must contain exactly one "
            "worldkeep entry."
        )
    source = matches[0].get("source", {})
    if source.get("source") != "local" or source.get("path") != "./plugins/worldkeep":
        raise SystemExit("The marketplace entry does not point to the local plugin mirror.")


def replace_local_plugin() -> None:
    plugin_root = LOCAL_PLUGIN_ROOT.resolve()
    target = LOCAL_PLUGIN.resolve()
    if target.parent != plugin_root:
        raise SystemExit(f"Refusing to replace plugin outside {plugin_root}: {target}")
    if not DIST_PLUGIN.is_dir():
        raise SystemExit(f"Distribution plugin is missing: {DIST_PLUGIN}")

    if LOCAL_PLUGIN.exists():
        for path in sorted(
            LOCAL_PLUGIN.rglob("*"), key=lambda item: len(item.parts), reverse=True
        ):
            if path.is_file() or path.is_symlink():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        LOCAL_PLUGIN.rmdir()
    shutil.copytree(DIST_PLUGIN, LOCAL_PLUGIN)


def add_codex_cachebuster(base_version: str) -> str:
    helper = (
        Path.home()
        / ".codex"
        / "skills"
        / ".system"
        / "plugin-creator"
        / "scripts"
        / "update_plugin_cachebuster.py"
    )
    if helper.is_file():
        run([sys.executable, str(helper), str(LOCAL_PLUGIN)])
    else:
        manifest_path = LOCAL_PLUGIN / ".codex-plugin" / "plugin.json"
        manifest = load_json(manifest_path)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        manifest["version"] = f"{base_version}+codex.{stamp}"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print("Codex cachebuster helper unavailable; used the compatible fallback.")

    local_path = LOCAL_PLUGIN / ".codex-plugin" / "plugin.json"
    local = load_json(local_path)
    version = str(local.get("version", ""))
    if not version.startswith(f"{base_version}+codex."):
        raise SystemExit(f"Unexpected local Codex cachebuster version: {version}")
    # Rewrite with LF whichever writer produced the file. The external
    # cachebuster helper lives outside this repository and writes with platform
    # defaults, and `plugins/` is tracked, so a CRLF manifest churns the diff
    # every time the pipeline runs on a different operating system.
    local_path.write_text(
        json.dumps(local, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return version


def validate_local_copy(base_version: str) -> None:
    dist_files = {
        path.relative_to(DIST_PLUGIN).as_posix()
        for path in DIST_PLUGIN.rglob("*")
        if path.is_file()
    }
    local_files = {
        path.relative_to(LOCAL_PLUGIN).as_posix()
        for path in LOCAL_PLUGIN.rglob("*")
        if path.is_file()
    }
    if dist_files != local_files:
        raise SystemExit("Local plugin file set differs from dist/plugin.")

    codex_manifest = ".codex-plugin/plugin.json"
    for relative in sorted(dist_files - {codex_manifest}):
        if (DIST_PLUGIN / relative).read_bytes() != (LOCAL_PLUGIN / relative).read_bytes():
            raise SystemExit(f"Local plugin differs from dist: {relative}")

    dist_codex = load_json(DIST_PLUGIN / codex_manifest)
    local_codex = load_json(LOCAL_PLUGIN / codex_manifest)
    local_version = str(local_codex.pop("version", ""))
    if dist_codex.pop("version", None) != base_version or dist_codex != local_codex:
        raise SystemExit("Local Codex manifest differs beyond its cachebuster version.")
    if not local_version.startswith(f"{base_version}+codex."):
        raise SystemExit("Local Codex manifest has no valid cachebuster version.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build and refresh both Worldbuilding Canon plugin surfaces."
    )
    parser.add_argument("--check", action="store_true", help="verify only; write nothing")
    args = parser.parse_args()

    enforce_changelog()
    validate_marketplace()

    if args.check:
        run([sys.executable, str(ROOT / "build.py"), "--check"])
        base_version = validate_dist_manifests()
        validate_local_copy(base_version)
        print(
            f"Both distribution manifests and the local Codex mirror are valid "
            f"at version {base_version}."
        )
        return 0

    run([sys.executable, str(ROOT / "build.py")])
    run([sys.executable, str(ROOT / "build.py"), "--check"])
    base_version = validate_dist_manifests()
    replace_local_plugin()
    local_version = add_codex_cachebuster(base_version)
    validate_local_copy(base_version)

    print("\nPlugin update complete.")
    print(f"  Claude bundle: dist/plugin.zip ({base_version})")
    print(f"  Codex source:  plugins/worldkeep ({local_version})")
    print("Restart the host application to reload the updated plugin.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"Pipeline command failed with exit code {exc.returncode}.") from exc
