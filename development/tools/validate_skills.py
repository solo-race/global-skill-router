#!/usr/bin/env python3
"""Skill registry validator for development/skill/manifest.yaml.

Checks the registry against the matrix in development/docs/plans/010-p0-foundation.md
section 3 (E1-E10, F1-F3, U1) with the per-status layered semantics of its
section 2(c): external/active paths must exist; planned entries may be
forward-registered before their directory exists.

Third-party dependency: PyYAML (yaml.safe_load for manifest and frontmatter
parsing); declared in AGENTS.md Core Rule 5.

Output contract: one JSON report document on stdout; one stderr line per
violation, "CODE skill: message". Exit codes: 0 all green, 1 violations,
130 on KeyboardInterrupt.
"""

import argparse
import json
import sys
from pathlib import Path, PurePosixPath

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPO_ROOT / "development" / "skill" / "manifest.yaml"
REQUIRED_FIELDS = ("name", "path", "status", "version", "description")
LIST_FIELDS = ("scenarios", "deps", "composed_of")
VALID_STATUSES = frozenset({"external", "planned", "active"})
VALID_SCENARIOS = frozenset({"win-access-vba", "win-android", "wsl-python"})


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Validate the skill registry manifest."
    )
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST),
        help="path to manifest.yaml (default: %(default)s)",
    )
    return parser.parse_args(argv)


def _err(code, skill, message):
    return {"code": code, "skill": skill, "message": message}


def _report(ok, manifest, skills_checked, errors):
    return {
        "ok": ok,
        "manifest": manifest,
        "skills_checked": skills_checked,
        "errors": errors,
    }


def _load_manifest(manifest_path, errors):
    """E1/E2: manifest must exist and parse to {schema_version: 1, skills: [...]}."""
    if not manifest_path.is_file():
        errors.append(
            _err("MANIFEST_NOT_FOUND", "(manifest)", f"manifest not found: {manifest_path}")
        )
        return None
    try:
        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        errors.append(_err("MANIFEST_PARSE_ERROR", "(manifest)", str(exc)))
        return None
    if not isinstance(data, dict) or not isinstance(data.get("skills"), list):
        errors.append(
            _err(
                "MANIFEST_PARSE_ERROR",
                "(manifest)",
                "manifest must be a mapping with a 'skills' list",
            )
        )
        return None
    if data.get("schema_version") != 1:
        errors.append(
            _err(
                "SCHEMA_VERSION_UNSUPPORTED",
                "(manifest)",
                f"schema_version must be 1, got {data.get('schema_version')!r}",
            )
        )
        return None
    return data


def _frontmatter_errors(skill_dir, entry_name, dir_basename):
    """F1-F3 against <skill_dir>/SKILL.md; caller guarantees the file exists."""
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    close = None
    if lines and lines[0].strip() == "---":
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                close = index
                break
    if close is None:
        return [
            _err(
                "FRONTMATTER_MISSING",
                entry_name,
                "SKILL.md has no '---' fenced frontmatter block",
            )
        ]
    try:
        frontmatter = yaml.safe_load("\n".join(lines[1:close]))
    except yaml.YAMLError:
        frontmatter = None
    if not isinstance(frontmatter, dict):
        frontmatter = {}
    errors = []
    fm_name = frontmatter.get("name")
    if fm_name != entry_name or dir_basename != entry_name:
        errors.append(
            _err(
                "NAME_MISMATCH",
                entry_name,
                (
                    f"frontmatter name {fm_name!r}, directory basename "
                    f"{dir_basename!r} and entry name {entry_name!r} must be equal"
                ),
            )
        )
    description = frontmatter.get("description")
    if not isinstance(description, str) or "Use when" not in description:
        errors.append(
            _err(
                "DESCRIPTION_NO_TRIGGER",
                entry_name,
                "frontmatter description must contain a 'Use when' trigger phrase",
            )
        )
    return errors


def _check_entry(entry, index, known_names, root, errors):
    """E3-E10 plus F1-F3 for one manifest entry; appends to errors."""
    if not isinstance(entry, dict):
        errors.append(_err("MISSING_FIELD", f"<entry {index}>", "entry must be a mapping"))
        return
    name = entry.get("name")
    label = name if isinstance(name, str) and name else f"<entry {index}>"
    for field in REQUIRED_FIELDS:
        value = entry.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(
                _err(
                    "MISSING_FIELD",
                    label,
                    f"required field '{field}' must be a non-empty string",
                )
            )
    status = entry.get("status")
    if status not in VALID_STATUSES:
        errors.append(
            _err(
                "INVALID_STATUS",
                label,
                f"status must be one of {sorted(VALID_STATUSES)}, got {status!r}",
            )
        )
    lists = {}
    for field in LIST_FIELDS:
        value = entry.get(field)
        if value is None:
            value = []
        if not isinstance(value, list):
            errors.append(_err("MISSING_FIELD", label, f"'{field}' must be a list"))
            value = []
        lists[field] = value
    for scenario in lists["scenarios"]:
        if scenario not in VALID_SCENARIOS:
            errors.append(
                _err(
                    "INVALID_SCENARIO",
                    label,
                    f"scenario '{scenario}' not in {sorted(VALID_SCENARIOS)}",
                )
            )
    for ref in lists["composed_of"]:
        if ref not in known_names:
            errors.append(
                _err(
                    "COMPOSED_OF_UNKNOWN_REF",
                    label,
                    f"composed_of reference '{ref}' does not resolve to an entry in this manifest",
                )
            )
    rel_path = entry.get("path")
    abs_path = root / rel_path if isinstance(rel_path, str) and rel_path else None
    if status == "external":
        if abs_path is not None and not abs_path.exists():
            errors.append(
                _err("EXTERNAL_PATH_MISSING", label, f"path does not exist: {rel_path}")
            )
    elif status == "planned":
        # Layered semantics (010 section 2(c)): a planned entry may exist as a
        # forward registration without any directory; F1-F3 run only when both
        # the directory and its SKILL.md are present.
        if abs_path is not None and (abs_path / "SKILL.md").is_file():
            basename = PurePosixPath(rel_path).name
            errors.extend(_frontmatter_errors(abs_path, name, basename))
    elif status == "active":
        if abs_path is not None:
            if not abs_path.exists():
                errors.append(
                    _err("ACTIVE_PATH_MISSING", label, f"path does not exist: {rel_path}")
                )
            elif not (abs_path / "SKILL.md").is_file():
                errors.append(
                    _err(
                        "ACTIVE_SKILL_MD_MISSING",
                        label,
                        f"missing SKILL.md under: {rel_path}",
                    )
                )
            else:
                basename = PurePosixPath(rel_path).name
                errors.extend(_frontmatter_errors(abs_path, name, basename))
        if not lists["scenarios"]:
            errors.append(
                _err(
                    "ACTIVE_EMPTY_SCENARIOS",
                    label,
                    "active entries must declare at least one scenario",
                )
            )


def validate(manifest_path):
    """Run the full check matrix; returns the report dict."""
    manifest_path = Path(manifest_path)
    errors = []
    loaded = _load_manifest(manifest_path, errors)
    if loaded is None:
        return _report(False, str(manifest_path), 0, errors)
    # Entry paths resolve against the repo root that contains this manifest
    # (<root>/development/skill/manifest.yaml -> root).
    root = manifest_path.resolve().parents[2]
    entries = loaded["skills"]
    all_names = [
        entry.get("name")
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("name"), str)
    ]
    seen = set()
    duplicates = set()
    for entry_name in all_names:
        if entry_name in seen:
            duplicates.add(entry_name)
        seen.add(entry_name)
    skills_checked = 0
    for index, entry in enumerate(entries):
        skills_checked += 1
        _check_entry(entry, index, seen, root, errors)
    for duplicate in sorted(duplicates):
        errors.append(
            _err("DUPLICATE_NAME", duplicate, "duplicate skill name in manifest")
        )
    scan_dir = manifest_path.parent
    if scan_dir.is_dir():
        registered = {entry.get("path") for entry in entries if isinstance(entry, dict)}
        for child in sorted(scan_dir.iterdir()):
            if child.is_dir():
                relative = child.relative_to(root).as_posix()
                if relative not in registered:
                    errors.append(
                        _err(
                            "UNREGISTERED_SKILL",
                            child.name,
                            f"directory under development/skill/ has no manifest entry: {relative}",
                        )
                    )
    return _report(not errors, str(manifest_path), skills_checked, errors)


def main(argv=None):
    args = parse_args(argv)
    report = validate(args.manifest)
    for error in report["errors"]:
        print(f"{error['code']} {error['skill']}: {error['message']}", file=sys.stderr)
    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
