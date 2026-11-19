#!/usr/bin/env python3
"""Report or apply the pi-subagents duplicate-functionality filter.

Reads ``references/pi-package-filter.json`` from this skill root and merges it into a
Pi settings JSON file (``~/.pi/agent/settings.json`` by default). The merge is
additive and idempotent: it rewrites only the filtered package's ``prompts`` and
``skills`` selectors and the ``disabled`` flag of the named builtin agents. Unrelated
settings, packages, and other per-agent override fields are preserved.

Read-only by default; ``--apply`` writes atomically. Output is one JSON document on
stdout. Exit codes: 0 in sync, 1 drift reported (or a controlled error), 130 on
KeyboardInterrupt.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FILTER = SKILL_ROOT / "references" / "pi-package-filter.json"
DEFAULT_SETTINGS = Path.home() / ".pi" / "agent" / "settings.json"


class FilterError(RuntimeError):
    """A controlled refusal: unreadable input or an unusable filter shape."""


def load_filter(path: Path) -> dict:
    """Load the canonical filter and validate the shape this tool relies on."""

    try:
        spec = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FilterError(f"cannot read filter {path}: {exc}") from exc
    packages = spec.get("packages")
    if not isinstance(packages, list) or len(packages) != 1:
        raise FilterError("filter.packages must contain exactly one package entry")
    entry = packages[0]
    if not isinstance(entry, dict) or not isinstance(entry.get("source"), str):
        raise FilterError("filter package entry must be an object with a source")
    if not isinstance(entry.get("prompts"), list) or not isinstance(entry.get("skills"), list):
        raise FilterError("filter package entry needs prompts and skills lists")
    overrides = spec.get("subagents", {}).get("agentOverrides")
    if not isinstance(overrides, dict) or not overrides:
        raise FilterError("filter.subagents.agentOverrides must be a non-empty object")
    for name, override in overrides.items():
        if not isinstance(override, dict) or override.get("disabled") is not True:
            raise FilterError(f"filter override for {name!r} must set disabled: true")
    return spec


def _package_source(package):
    if isinstance(package, str):
        return package
    if isinstance(package, dict):
        return package.get("source")
    return None


def merge_settings(settings: dict, filter_spec: dict) -> dict:
    """Return a new settings mapping with the filter enforced."""

    entry = filter_spec["packages"][0]
    source = entry["source"]
    packages = list(settings.get("packages") or [])
    merged = dict(settings)
    replaced = False
    for index, package in enumerate(packages):
        if _package_source(package) != source:
            continue
        base = dict(package) if isinstance(package, dict) else {"source": source}
        base["prompts"] = list(entry["prompts"])
        base["skills"] = list(entry["skills"])
        packages[index] = base
        replaced = True
        break
    if not replaced:
        packages.append(
            {
                "source": source,
                "prompts": list(entry["prompts"]),
                "skills": list(entry["skills"]),
            }
        )
    merged["packages"] = packages

    subagents = dict(merged.get("subagents") or {})
    overrides = dict(subagents.get("agentOverrides") or {})
    for name, override in filter_spec["subagents"]["agentOverrides"].items():
        current = dict(overrides.get(name) or {})
        current["disabled"] = override["disabled"]
        overrides[name] = current
    subagents["agentOverrides"] = overrides
    merged["subagents"] = subagents
    return merged


def changed_keys(settings: dict, merged: dict) -> list[str]:
    """Name the settings paths the filter would change."""

    changed = []
    if settings.get("packages") != merged.get("packages"):
        changed.append("packages")
    for name, override in merged["subagents"]["agentOverrides"].items():
        current = (settings.get("subagents") or {}).get("agentOverrides", {}).get(name) or {}
        if bool(current.get("disabled")) != bool(override["disabled"]):
            changed.append(f"subagents.agentOverrides.{name}.disabled")
    return changed


def _read_settings(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        settings = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FilterError(f"cannot read settings {path}: {exc}") from exc
    if not isinstance(settings, dict):
        raise FilterError(f"settings must be a JSON object: {path}")
    return settings


def _write_settings(path: Path, settings: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(settings, indent=2, ensure_ascii=False, sort_keys=False))
            stream.write("\n")
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Report or apply the pi-subagents duplicate-functionality filter."
    )
    parser.add_argument("--settings", default=str(DEFAULT_SETTINGS), help="Pi settings file")
    parser.add_argument("--filter", default=str(DEFAULT_FILTER), help="canonical filter JSON")
    parser.add_argument("--apply", action="store_true", help="write the merged settings")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    settings_path = Path(args.settings).expanduser()
    filter_path = Path(args.filter).expanduser()
    try:
        spec = load_filter(filter_path)
        current = _read_settings(settings_path)
        merged = merge_settings(current, spec)
        changed = changed_keys(current, merged)
        applied = False
        if args.apply and changed:
            _write_settings(settings_path, merged)
            applied = True
        result = {
            "ok": not changed or applied,
            "applied": applied,
            "settings": str(settings_path),
            "filter": str(filter_path),
            "status": "in_sync" if not changed else "drift",
            "changes": changed,
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ok"] else 1
    except FilterError as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
