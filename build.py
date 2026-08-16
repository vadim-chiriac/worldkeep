#!/usr/bin/env python3
"""Packaging build script.

Assembles two skills (worldbuilding-scribe, canon-viewer) from sources
elsewhere in the tree into dist/*.skill zips and a dual-host dist/plugin/
folder for Claude and ChatGPT/Codex. Skill folders are build artifacts;
nothing here is hand-copied.

Usage:
    python build.py            # sync + package both skills + assemble plugin
    python build.py --check    # verify only: exit 1 if dist is stale or drifted
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
SPEC = ROOT / "Specification"
SCRIBE_SRC = SRC / "skills" / "worldbuilding-scribe"
VIEWER_SKILL_SRC = SRC / "skills" / "canon-viewer"
VIEWER = SRC / "viewer"
WB = SRC / "wb"
RUNTIME = SRC / "runtime"
DIST = ROOT / "dist"
DOCUMENTATION_ASSETS = ROOT / "Documentation" / "assets"

PLUGIN_NAME = "worldkeep"
PLUGIN_VERSION = "0.3.2"
PLUGIN_DESCRIPTION = "Worldkeep: capture and view a structured worldbuilding canon"
PLUGIN_REPOSITORY = "https://github.com/vadim-chiriac/worldkeep"
PLUGIN_DEVELOPER = "Worldkeep project"

VENDOR_DIR = RUNTIME / "_vendor"
if VENDOR_DIR.is_dir():
    sys.path.insert(0, str(VENDOR_DIR))
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"


# ---------------------------------------------------------------------------
# Generic sync helpers
# ---------------------------------------------------------------------------

def copy_agent_cli(bundle: Path) -> list[Path]:
    """Place the one canonical `wb` in a bundle's scripts folder.

    Both skills ship the same entrypoint from `src/wb`, so an agent has
    one command wherever it starts. At runtime wb resolves its sibling skill
    through the installed layout rather than being duplicated per bundle.
    """
    copied: list[Path] = []
    copied += copytree_all(WB / "wb.py", bundle / "scripts" / "wb.py")
    copied += copytree_all(
        WB / "wblib",
        bundle / "scripts" / "wblib",
        exclude_names={"__pycache__"},
    )
    return copied


def copytree_all(src: Path, dst: Path, *, exclude_names: set[str] = frozenset()) -> list[Path]:
    """Copy every file under src to dst, recursively. Returns list of dest files.

    Skips directories/files whose basename is in exclude_names (checked at
    every level, e.g. '__pycache__'), and skips dotfiles like .gitkeep is
    NOT excluded (it's needed to keep empty dirs meaningful in git, but it
    is harmless to ship too) -- gitkeep files ARE copied since brief says
    copy everything under the path, not a hand-listed set.
    """
    copied: list[Path] = []
    if not src.exists():
        raise FileNotFoundError(f"source path missing: {src}")
    if src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(dst)
        return copied
    for path in sorted(src.rglob("*")):
        if path.is_dir():
            continue
        if any(part in exclude_names for part in path.relative_to(src).parts):
            continue
        rel = path.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied.append(target)
    return copied


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def parse_first_heading(md_path: Path) -> str:
    """Pull the version string out of the first '# ... (vX.Y)' heading."""
    text = md_path.read_text(encoding="utf-8")
    first_line = text.splitlines()[0] if text else ""
    m = re.search(r"\(v[0-9][^)]*\)", first_line)
    if m:
        return m.group(0).strip("()")
    m = re.search(r"v[0-9][\w.]*", first_line)
    return m.group(0) if m else "unknown"


def check_canonical_seed_kernel_version(seed_world: Path, kernel_version: str) -> None:
    """Require the shipped seed manifest to name the canonical KERNEL version."""
    import yaml

    manifest_path = seed_world / "world.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    actual = str(manifest.get("kernel_version", "")) if isinstance(manifest, dict) else ""
    expected = kernel_version.removeprefix("v")
    if actual != expected:
        try:
            display_path = manifest_path.relative_to(ROOT)
        except ValueError:
            display_path = manifest_path
        raise SystemExit(
            f"build failed: {display_path} kernel_version "
            f"'{actual}' != KERNEL.md version '{expected}'"
        )


def parse_skill_frontmatter(skill_md: Path) -> dict:
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{skill_md}: missing YAML frontmatter")
    end = text.find("\n---", 4)
    if end == -1:
        raise ValueError(f"{skill_md}: unterminated YAML frontmatter")
    import yaml
    fm = yaml.safe_load(text[4:end])
    if not isinstance(fm, dict) or "name" not in fm or "description" not in fm:
        raise ValueError(f"{skill_md}: frontmatter missing 'name' or 'description'")
    return fm


# ---------------------------------------------------------------------------
# Skill 1 — worldbuilding-scribe
# ---------------------------------------------------------------------------

def build_scribe(build_dir: Path) -> tuple[Path, dict]:
    bundle = build_dir / "worldbuilding-scribe"
    copied: list[Path] = []

    copied += copytree_all(SCRIBE_SRC / "SKILL.md", bundle / "SKILL.md")
    copied += copytree_all(SPEC / "KERNEL.md", bundle / "references" / "KERNEL.md")
    copied += copytree_all(SPEC / "SCRIBE.md", bundle / "references" / "SCRIBE.md")
    copied += copytree_all(SCRIBE_SRC / "scripts" / "validate.py", bundle / "scripts" / "validate.py")
    copied += copytree_all(SCRIBE_SRC / "scripts" / "apply.py", bundle / "scripts" / "apply.py")
    copied += copy_agent_cli(bundle)
    copied += copytree_all(
        RUNTIME / "_vendor",
        bundle / "scripts" / "_vendor",
        exclude_names={"__pycache__"},
    )
    copied += copytree_all(
        RUNTIME / "run-python.ps1",
        bundle / "scripts" / "run-python.ps1",
    )
    copied += copytree_all(
        RUNTIME / "run-python.sh",
        bundle / "scripts" / "run-python.sh",
    )

    seed_src = SCRIBE_SRC / "assets" / "seed-world"
    seed_dst = bundle / "assets" / "seed-world"
    for path in sorted(seed_src.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(seed_src)
        if rel.name.upper() == "INDEX.md".upper():
            continue
        target = seed_dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied.append(target)

    manifest = {p.relative_to(build_dir).as_posix(): sha256_file(p) for p in copied}
    return bundle, manifest


# ---------------------------------------------------------------------------
# Skill 2 — canon-viewer
# ---------------------------------------------------------------------------

def build_viewer(build_dir: Path) -> tuple[Path, dict]:
    bundle = build_dir / "canon-viewer"
    copied: list[Path] = []

    copied += copytree_all(VIEWER_SKILL_SRC / "SKILL.md", bundle / "SKILL.md")
    copied += copytree_all(VIEWER / "view.py", bundle / "scripts" / "view.py")
    copied += copy_agent_cli(bundle)
    copied += copytree_all(
        RUNTIME / "_vendor",
        bundle / "scripts" / "_vendor",
        exclude_names={"__pycache__"},
    )
    copied += copytree_all(
        RUNTIME / "run-python.ps1",
        bundle / "scripts" / "run-python.ps1",
    )
    copied += copytree_all(
        RUNTIME / "run-python.sh",
        bundle / "scripts" / "run-python.sh",
    )
    copied += copytree_all(
        VIEWER / "viewer", bundle / "scripts" / "viewer",
        exclude_names={"__pycache__"},
    )
    copied += copytree_all(
        VIEWER / "vendor", bundle / "scripts" / "vendor",
        exclude_names={"__pycache__"},
    )
    copied += copytree_all(VIEWER_SKILL_SRC / "assets" / "views-library", bundle / "assets" / "views-library")

    manifest = {p.relative_to(build_dir).as_posix(): sha256_file(p) for p in copied}
    return bundle, manifest


# ---------------------------------------------------------------------------
# Packaging
# ---------------------------------------------------------------------------

#: A fixed timestamp for every archive member. Without it two builds of
#: identical content produce different bytes, which is a poor claim to
#: reproducibility and, with dist/ committed, four files permanently dirty in
#: git. The date a build happened is recoverable from the commit that carries
#: it; it does not belong in the artifact.
ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)


def _add_to_zip(zf: zipfile.ZipFile, path: Path, arcname: str) -> None:
    """Add one file with a fixed timestamp and mode, so builds are repeatable."""
    info = zipfile.ZipInfo(arcname, date_time=ZIP_EPOCH)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    zf.writestr(info, path.read_bytes())


def zip_skill(bundle_dir: Path, out_path: Path) -> None:
    """Write skill_name.skill at out_path."""
    skill_name = bundle_dir.name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(bundle_dir.rglob("*")):
            if path.is_dir():
                continue
            arcname = Path(skill_name) / path.relative_to(bundle_dir)
            _add_to_zip(zf, path, arcname.as_posix())


def zip_plugin(plugin_dir: Path, out_path: Path) -> None:
    """Write a clean plugin.zip with the plugin folder as its archive root."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(plugin_dir.rglob("*")):
            if path.is_dir():
                continue
            arcname = Path(plugin_dir.name) / path.relative_to(plugin_dir)
            _add_to_zip(zf, path, arcname.as_posix())


def claude_plugin_manifest(kernel_version: str, scribe_version: str) -> dict:
    return {
        "name": PLUGIN_NAME,
        "displayName": "Worldkeep",
        "version": PLUGIN_VERSION,
        "description": PLUGIN_DESCRIPTION,
        "author": {
            "name": PLUGIN_DEVELOPER,
            "url": PLUGIN_REPOSITORY,
        },
        "homepage": PLUGIN_REPOSITORY,
        "repository": PLUGIN_REPOSITORY,
        "license": "MIT",
        "keywords": ["worldbuilding", "canon", "capture", "visualization"],
        "metadata": {
            "kernelVersion": kernel_version,
            "scribeVersion": scribe_version,
        },
    }


def codex_plugin_manifest() -> dict:
    """Return the ChatGPT/Codex manifest accepted by plugin ingestion."""
    return {
        "name": PLUGIN_NAME,
        "version": PLUGIN_VERSION,
        "description": PLUGIN_DESCRIPTION,
        "author": {
            "name": PLUGIN_DEVELOPER,
            "url": PLUGIN_REPOSITORY,
        },
        "repository": PLUGIN_REPOSITORY,
        "keywords": ["worldbuilding", "canon", "capture", "visualization"],
        "skills": "./skills/",
        "interface": {
            "displayName": "Worldkeep",
            "shortDescription": "Capture and visualize structured worldbuilding canon.",
            "longDescription": (
                "Capture freeform worldbuilding into a Markdown/YAML canon, "
                "validate it, and render configurable offline graph views."
            ),
            "developerName": PLUGIN_DEVELOPER,
            "category": "Productivity",
            "capabilities": ["Read", "Write"],
            "defaultPrompt": [
                "Help me capture this worldbuilding into canon.",
                "Render a graph of my worldbuilding canon.",
                "Show me who rules what in this canon.",
            ],
            "composerIcon": "./assets/worldkeep-icon-128.png",
            "logo": "./assets/worldkeep-icon-512.png",
        },
    }


def assemble_plugin(build_dir: Path, plugin_dir: Path, kernel_version: str, scribe_version: str) -> None:
    """Assemble one clean dual-host plugin from the temporary skill build."""
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (plugin_dir / ".codex-plugin").mkdir(parents=True, exist_ok=True)
    # newline="\n" keeps the build byte-reproducible across platforms: every
    # other file is copied verbatim, so without it these two manifests are the
    # only outputs whose bytes — and therefore whose release checksums — depend
    # on the operating system that ran the build.
    (plugin_dir / ".claude-plugin" / "plugin.json").write_text(
        json.dumps(claude_plugin_manifest(kernel_version, scribe_version), indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (plugin_dir / ".codex-plugin" / "plugin.json").write_text(
        json.dumps(codex_plugin_manifest(), indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    assets_dir = plugin_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    for filename in ("worldkeep-icon-128.png", "worldkeep-icon-512.png"):
        shutil.copy2(DOCUMENTATION_ASSETS / filename, assets_dir / filename)

    skills_dir = plugin_dir / "skills"
    shutil.copytree(build_dir / "worldbuilding-scribe", skills_dir / "worldbuilding-scribe", dirs_exist_ok=True)
    shutil.copytree(build_dir / "canon-viewer", skills_dir / "canon-viewer", dirs_exist_ok=True)


def check_plugin_outputs(expected_plugin: Path, actual_plugin: Path, archive_path: Path) -> list[str]:
    """Compare the staged plugin with dist/plugin/ and dist/plugin.zip."""
    problems: list[str] = []
    expected_files = {
        path.relative_to(expected_plugin): sha256_file(path)
        for path in expected_plugin.rglob("*")
        if path.is_file()
    }
    actual_files = {
        path.relative_to(actual_plugin)
        for path in actual_plugin.rglob("*")
        if path.is_file()
    } if actual_plugin.is_dir() else set()

    for rel_path in sorted(actual_files - set(expected_files)):
        problems.append(f"unexpected extra file in dist/plugin: {rel_path.as_posix()}")

    for rel_path, expected_hash in sorted(expected_files.items()):
        actual_path = actual_plugin / rel_path
        if not actual_path.is_file():
            problems.append(f"missing from dist/plugin: {rel_path.as_posix()}")
        elif sha256_file(actual_path) != expected_hash:
            problems.append(f"changed in dist/plugin: {rel_path.as_posix()}")

    if not archive_path.is_file():
        problems.append("missing dist/plugin.zip")
        return problems

    try:
        with zipfile.ZipFile(archive_path) as zf:
            members = set(zf.namelist())
            for rel_path, expected_hash in sorted(expected_files.items()):
                member = (Path(expected_plugin.name) / rel_path).as_posix()
                if member not in members:
                    problems.append(f"missing from dist/plugin.zip: {member}")
                    continue
                digest = hashlib.sha256(zf.read(member)).hexdigest()
                if digest != expected_hash:
                    problems.append(f"changed in dist/plugin.zip: {member}")
    except zipfile.BadZipFile:
        problems.append("dist/plugin.zip is not a valid zip archive")

    return problems


def replace_plugin_output(staged_plugin: Path, plugin_output: Path) -> None:
    """Replace generated files, tolerating only empty Windows-locked folders."""
    if plugin_output.resolve().parent != DIST.resolve():
        raise RuntimeError(f"refusing to replace plugin output outside {DIST}: {plugin_output}")
    stale: list[str] = []
    if plugin_output.exists():
        staged_rel = {
            path.relative_to(staged_plugin).as_posix()
            for path in staged_plugin.rglob("*") if path.is_file()
        }
        paths = sorted(plugin_output.rglob("*"), key=lambda path: len(path.parts), reverse=True)
        for path in paths:
            if not (path.is_file() or path.is_symlink()):
                continue
            rel = path.relative_to(plugin_output).as_posix()
            if rel in staged_rel:
                continue  # will be overwritten in place
            try:
                path.unlink()
            except OSError:
                # Some mounts forbid deletion entirely (see CLEANUP.md). Overwrite
                # is always available; deletion is not. Report what could not be
                # removed rather than failing the whole build over a stale file.
                stale.append(rel)
        for path in paths:
            if path.is_dir():
                try:
                    path.rmdir()
                except OSError:
                    pass
    shutil.copytree(staged_plugin, plugin_output, dirs_exist_ok=True)
    if stale:
        print("  warning: could not delete stale files in dist/plugin "
              "(mount forbids deletion); remove by hand:")
        for rel in sorted(stale):
            print(f"    {rel}")


# ---------------------------------------------------------------------------
# Verification (run before packaging)
# ---------------------------------------------------------------------------

def run_validate(seed_world: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIBE_SRC / "scripts" / "validate.py"), str(seed_world)],
        capture_output=True, text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise SystemExit("build failed: validate.py reported errors on the seed world")


def check_skill_frontmatter(build_dir: Path) -> None:
    for name in ("worldbuilding-scribe", "canon-viewer"):
        skill_md = build_dir / name / "SKILL.md"
        fm = parse_skill_frontmatter(skill_md)
        if fm["name"] != name:
            raise SystemExit(
                f"build failed: {skill_md} frontmatter name '{fm['name']}' != folder name '{name}'"
            )


def run_viewer_tests() -> None:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(VENDOR_DIR) + (os.pathsep + existing_pythonpath if existing_pythonpath else "")
    )
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "tests/", "-q"],
        cwd=str(VIEWER), capture_output=True, text=True, env=env,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise SystemExit("build failed: src/viewer pytest suite failed")


def run_wb_tests() -> None:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(VENDOR_DIR) + (os.pathsep + existing_pythonpath if existing_pythonpath else "")
    )
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "tests/", "-q"],
        cwd=str(WB), capture_output=True, text=True, env=env,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise SystemExit("build failed: src/wb pytest suite failed")


def run_scribe_tests() -> None:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(VENDOR_DIR) + (os.pathsep + existing_pythonpath if existing_pythonpath else "")
    )
    result = subprocess.run(
        [sys.executable, str(SCRIBE_SRC / "tests" / "test_apply.py")],
        cwd=str(ROOT), capture_output=True, text=True, env=env,
    )
    print(result.stdout)
    if result.stderr.strip():
        print(result.stderr)
    if result.returncode != 0:
        raise SystemExit("build failed: src/skills/worldbuilding-scribe/tests/test_apply.py failed")


def check_apply_flag_parity(build_dir: Path) -> None:
    """Every flag scripts/apply.py --help advertises in the bundle must also
    appear in the source apply.py --help. Hand-copying drifted twice in one
    afternoon under supervision; catch it here instead of a human catching it
    live."""
    bundled = build_dir / "worldbuilding-scribe" / "scripts" / "apply.py"
    source = SCRIBE_SRC / "scripts" / "apply.py"

    def flags(script: Path) -> set[str]:
        result = subprocess.run(
            [sys.executable, str(script), "--help"],
            capture_output=True, text=True,
        )
        return set(re.findall(r"--[a-zA-Z][a-zA-Z-]*", result.stdout))

    bundled_flags = flags(bundled)
    source_flags = flags(source)
    missing = bundled_flags - source_flags
    if missing:
        raise SystemExit(
            f"build failed: bundled apply.py advertises flags not in src/skills/worldbuilding-scribe/scripts/apply.py: {sorted(missing)}"
        )


# ---------------------------------------------------------------------------
# BUILD.txt provenance
# ---------------------------------------------------------------------------

def write_build_txt(
    dest: Path,
    *,
    kernel_version: str,
    scribe_version: str,
    manifests: dict[str, dict],
) -> None:
    lines = [
        f"KERNEL.md version: {kernel_version}",
        f"SCRIBE.md version: {scribe_version}",
        "",
    ]
    for skill_name, manifest in manifests.items():
        lines.append(f"[{skill_name}]")
        for rel_path, digest in sorted(manifest.items()):
            lines.append(f"  sha256 {digest}  {rel_path}")
        lines.append("")
    dest.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def parse_build_txt(path: Path) -> dict[str, str]:
    """Return {rel_path: sha256} across all skills, ignoring header lines."""
    hashes: dict[str, str] = {}
    if not path.exists():
        return hashes
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("sha256 "):
            _, rest = line.split("sha256 ", 1)
            digest, rel_path = rest.split("  ", 1)
            hashes[rel_path] = digest
    return hashes


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def do_build(build_dir: Path) -> dict:
    scribe_bundle, scribe_manifest = build_scribe(build_dir)
    viewer_bundle, viewer_manifest = build_viewer(build_dir)

    check_skill_frontmatter(build_dir)
    run_validate(build_dir / "worldbuilding-scribe" / "assets" / "seed-world")
    run_scribe_tests()
    run_viewer_tests()
    run_wb_tests()
    check_apply_flag_parity(build_dir)

    return {
        "worldbuilding-scribe": scribe_manifest,
        "canon-viewer": viewer_manifest,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify only, no write")
    args = parser.parse_args()

    kernel_version = parse_first_heading(SPEC / "KERNEL.md")
    scribe_version = parse_first_heading(SPEC / "SCRIBE.md")
    check_canonical_seed_kernel_version(SCRIBE_SRC / "assets" / "seed-world", kernel_version)

    if args.check:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_build = Path(tmp) / "build"
            manifests = do_build(tmp_build)
            tmp_plugin = Path(tmp) / "plugin"
            assemble_plugin(tmp_build, tmp_plugin, kernel_version, scribe_version)

            # manifests are keyed by rel_path relative to the build dir,
            # which already begins with the skill folder name — this
            # matches exactly what write_build_txt records in BUILD.txt.
            derived_flat: dict[str, str] = {}
            for skill_name, manifest in manifests.items():
                for rel_path, digest in manifest.items():
                    derived_flat[rel_path] = digest

            recorded = parse_build_txt(DIST / "BUILD.txt")
            # BUILD.txt may have been written on another OS. Paths are logical
            # identities, not filesystem paths, so compare them separator-blind:
            # otherwise every file reads as both missing and extra, and --check
            # is useless exactly when two machines share a repo.
            norm = lambda d: {k.replace("\\", "/"): v for k, v in d.items()}
            derived_flat, recorded = norm(derived_flat), norm(recorded)
            if derived_flat != recorded:
                missing = set(derived_flat) - set(recorded)
                changed = {
                    k for k in (set(derived_flat) & set(recorded))
                    if derived_flat[k] != recorded[k]
                }
                extra = set(recorded) - set(derived_flat)
                print("dist is stale or drifted from source:")
                if missing:
                    print(f"  new/untracked files: {sorted(missing)}")
                if changed:
                    print(f"  changed files: {sorted(changed)}")
                if extra:
                    print(f"  files only in BUILD.txt: {sorted(extra)}")
                return 1

            plugin_problems = check_plugin_outputs(
                tmp_plugin,
                DIST / "plugin",
                DIST / "plugin.zip",
            )
            if plugin_problems:
                print("plugin outputs are stale or incomplete:")
                for problem in plugin_problems:
                    print(f"  {problem}")
                return 1
            print("dist matches source. --check OK.")
            return 0

    DIST.mkdir(parents=True, exist_ok=True)
    # Build in a disposable temp directory so verification completes before
    # any release artifact under dist/ is replaced.
    with tempfile.TemporaryDirectory(prefix="wb-build-") as tmp:
        build_dir = Path(tmp) / "build"
        manifests = do_build(build_dir)

        zip_skill(build_dir / "worldbuilding-scribe", DIST / "worldbuilding-scribe.skill")
        zip_skill(build_dir / "canon-viewer", DIST / "canon-viewer.skill")

        staged_plugin = Path(tmp) / "plugin"
        assemble_plugin(build_dir, staged_plugin, kernel_version, scribe_version)
        replace_plugin_output(staged_plugin, DIST / "plugin")
        zip_plugin(staged_plugin, DIST / "plugin.zip")

        write_build_txt(
            DIST / "BUILD.txt",
            kernel_version=kernel_version,
            scribe_version=scribe_version,
            manifests=manifests,
        )

    def bundle_size(path: Path) -> str:
        n = path.stat().st_size
        for unit in ("B", "KB", "MB"):
            if n < 1024:
                return f"{n:.0f}{unit}"
            n /= 1024
        return f"{n:.1f}GB"

    print("\nBuild complete.")
    print(f"  KERNEL.md: {kernel_version}")
    print(f"  SCRIBE.md: {scribe_version}")
    print(f"  worldbuilding-scribe.skill: {bundle_size(DIST / 'worldbuilding-scribe.skill')} "
          f"({len(manifests['worldbuilding-scribe'])} files)")
    print(f"  canon-viewer.skill: {bundle_size(DIST / 'canon-viewer.skill')} "
          f"({len(manifests['canon-viewer'])} files)")
    print(f"  plugin.zip: {bundle_size(DIST / 'plugin.zip')} (Claude + ChatGPT/Codex)")
    print(f"  dist/plugin/ assembled with both plugin manifests")
    print(f"  dist/BUILD.txt written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
