"""Effective ``scribe.yaml`` settings, with their documented defaults.

`scribe.yaml` is behavioural: no code has ever enforced it, and none does here.
wb only reports what an assistant would otherwise have to open SCRIBE.md and
the file itself to work out.

The default table below is the one place wb restates SCRIBE.md, and it is not
allowed to drift: ``tests/test_spec_sync.py`` parses the settings block in
SCRIBE.md section 10 and fails if the names, allowed values, or defaults here
disagree with it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml


#: setting -> (documented default, allowed values in documented order)
SCRIBE_SETTINGS: dict[str, tuple[str, tuple[str, ...]]] = {
    "approval": ("strict", ("strict", "material_only", "deferred")),
    "prose": ("compose", ("compose", "quote", "none")),
    "types": ("ask", ("existing_only", "ask", "free")),
    "extraction": ("eager", ("eager", "stated_only")),
    "bundles": ("full", ("full", "terse", "none")),
}

CONFIG_NAME = "scribe.yaml"


class ScribeConfig:
    """One world's effective scribe preferences and where each value came from."""

    def __init__(
        self,
        values: Mapping[str, str],
        sources: Mapping[str, str],
        present: bool,
        warnings: tuple[str, ...] = (),
    ) -> None:
        self.values = dict(values)
        self.sources = dict(sources)
        self.present = present
        self.warnings = tuple(warnings)

    def as_json(self) -> dict[str, Any]:
        return {
            "file_present": self.present,
            "settings": {
                name: {"value": self.values[name], "source": self.sources[name]}
                for name in SCRIBE_SETTINGS
            },
            "warnings": list(self.warnings),
        }

    def non_default(self) -> dict[str, str]:
        return {
            name: value
            for name, value in self.values.items()
            if self.sources[name] == CONFIG_NAME
        }

    def summary_line(self) -> str:
        """One compact line naming every effective value."""
        return ", ".join(f"{name}={self.values[name]}" for name in SCRIBE_SETTINGS)


def load_scribe_config(world: Path) -> ScribeConfig:
    """Read ``scribe.yaml`` beside ``world.yaml``; absence means the defaults."""
    path = Path(world) / CONFIG_NAME
    values = {name: default for name, (default, _) in SCRIBE_SETTINGS.items()}
    sources = {name: "default" for name in SCRIBE_SETTINGS}
    warnings: list[str] = []

    if not path.is_file():
        return ScribeConfig(values, sources, present=False)

    try:
        parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        warnings.append(f"{CONFIG_NAME}: cannot be read ({exc}); using documented defaults")
        return ScribeConfig(values, sources, present=True, warnings=tuple(warnings))

    if parsed is None:
        return ScribeConfig(values, sources, present=True)
    if not isinstance(parsed, dict):
        warnings.append(f"{CONFIG_NAME}: not a mapping; using documented defaults")
        return ScribeConfig(values, sources, present=True, warnings=tuple(warnings))

    for key in sorted(parsed):
        if key not in SCRIBE_SETTINGS:
            warnings.append(f"{CONFIG_NAME}: unknown setting '{key}'; ignored")

    for name, (default, allowed) in SCRIBE_SETTINGS.items():
        if name not in parsed:
            continue
        raw = parsed[name]
        if not isinstance(raw, str) or raw.strip() not in allowed:
            warnings.append(
                f"{CONFIG_NAME}: {name}={raw!r} is not one of "
                f"{', '.join(allowed)}; using documented default '{default}'"
            )
            continue
        values[name] = raw.strip()
        sources[name] = CONFIG_NAME

    return ScribeConfig(values, sources, present=True, warnings=tuple(warnings))
