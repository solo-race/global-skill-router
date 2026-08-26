"""Tests for development/tools/validate_skills.py (plan 010 section 4)."""

import importlib.util
import json
import sys
from pathlib import Path

import yaml

_SPEC = importlib.util.spec_from_file_location(
    "validate_skills_under_test",
    Path(__file__).with_name("validate_skills.py"),
)
validate_skills = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(validate_skills)


def _entry(name, path, status="external", **overrides):
    entry = {
        "name": name,
        "path": path,
        "status": status,
        "scenarios": [],
        "deps": [],
        "composed_of": [],
        "version": "1.0.0",
        "description": "placeholder description",
    }
    entry.update(overrides)
    return entry


def _write_skill_md(skill_dir, name=None, description="Use when testing skills.", raw=None):
    skill_dir.mkdir(parents=True, exist_ok=True)
    target = skill_dir / "SKILL.md"
    if raw is not None:
        target.write_text(raw, encoding="utf-8")
    else:
        target.write_text(
            "---\n" f"name: {name}\n" f"description: {description}\n" "---\n\nBody.\n",
            encoding="utf-8",
        )


def _build_tree(tmp_path, entries, probe_dirs=(), create_external=True):
    skill_dir = tmp_path / "development" / "skill"
    skill_dir.mkdir(parents=True, exist_ok=True)
    for probe in probe_dirs:
        (skill_dir / probe).mkdir(parents=True, exist_ok=True)
    for entry in entries:
        if create_external and entry["status"] == "external":
            (tmp_path / entry["path"]).mkdir(parents=True, exist_ok=True)
    manifest = skill_dir / "manifest.yaml"
    manifest.write_text(
        yaml.safe_dump({"schema_version": 1, "skills": entries}, sort_keys=False),
        encoding="utf-8",
    )
    return manifest


def _run(tmp_path, entries, probe_dirs=(), create_external=True):
    manifest = _build_tree(tmp_path, entries, probe_dirs, create_external)
    return validate_skills.validate(manifest)


def _codes(report):
    return [error["code"] for error in report["errors"]]


def _green_entries():
    return [
        _entry("spine-lib", "references/spine-lib", "external"),
        _entry(
            "research-investigation",
            "development/skill/research-investigation",
            "planned",
            version="0.1.0",
        ),
        _entry(
            "runtime-ops",
            "development/skill/runtime-ops",
            "active",
            scenarios=["win-access-vba"],
            version="0.1.0",
        ),
    ]


def _green_tree(tmp_path):
    _write_skill_md(tmp_path / "development" / "skill" / "runtime-ops", name="runtime-ops")
    return _run(tmp_path, _green_entries())


def test_green_tree_passes(tmp_path):
    report = _green_tree(tmp_path)
    assert report["ok"] is True
    assert report["errors"] == []
    assert report["skills_checked"] == 3


def test_planned_forward_registration_without_dir_ok(tmp_path):
    entries = [
        _entry("spine-lib", "references/spine-lib", "external"),
        _entry(
            "future-skill",
            "development/skill/future-skill",
            "planned",
            version="0.1.0",
        ),
    ]
    report = _run(tmp_path, entries)
    assert report["ok"] is True
    assert report["errors"] == []


def test_planned_with_skill_md_checked(tmp_path):
    entries = [_entry("early-skill", "development/skill/early-skill", "planned")]
    _write_skill_md(tmp_path / "development" / "skill" / "early-skill", name="wrong-name")
    report = _run(tmp_path, entries)
    assert _codes(report) == ["NAME_MISMATCH"]


def test_active_requires_skill_md(tmp_path):
    entries = [
        _entry(
            "runtime-ops",
            "development/skill/runtime-ops",
            "active",
            scenarios=["win-access-vba"],
        )
    ]
    (tmp_path / "development" / "skill" / "runtime-ops").mkdir(parents=True)
    report = _run(tmp_path, entries)
    assert "ACTIVE_SKILL_MD_MISSING" in _codes(report)


def test_active_empty_scenarios_rejected(tmp_path):
    entries = [_entry("runtime-ops", "development/skill/runtime-ops", "active")]
    _write_skill_md(tmp_path / "development" / "skill" / "runtime-ops", name="runtime-ops")
    report = _run(tmp_path, entries)
    assert "ACTIVE_EMPTY_SCENARIOS" in _codes(report)


def test_external_missing_path_detected(tmp_path):
    entries = [_entry("ghost-lib", "references/ghost-lib", "external")]
    report = _run(tmp_path, entries, create_external=False)
    assert "EXTERNAL_PATH_MISSING" in _codes(report)


def test_name_mismatch_detected(tmp_path):
    entries = [
        _entry(
            "runtime-ops",
            "development/skill/runtime-ops",
            "active",
            scenarios=["win-access-vba"],
        )
    ]
    _write_skill_md(
        tmp_path / "development" / "skill" / "runtime-ops", name="other-name"
    )
    report = _run(tmp_path, entries)
    assert "NAME_MISMATCH" in _codes(report)


def test_missing_use_when_detected(tmp_path):
    entries = [
        _entry(
            "runtime-ops",
            "development/skill/runtime-ops",
            "active",
            scenarios=["win-access-vba"],
        )
    ]
    _write_skill_md(
        tmp_path / "development" / "skill" / "runtime-ops",
        name="runtime-ops",
        description="Runs runtime operations.",
    )
    report = _run(tmp_path, entries)
    assert "DESCRIPTION_NO_TRIGGER" in _codes(report)


def test_missing_frontmatter_detected(tmp_path):
    entries = [
        _entry(
            "runtime-ops",
            "development/skill/runtime-ops",
            "active",
            scenarios=["win-access-vba"],
        )
    ]
    _write_skill_md(
        tmp_path / "development" / "skill" / "runtime-ops",
        raw="# Just prose, no fence.\n",
    )
    report = _run(tmp_path, entries)
    assert "FRONTMATTER_MISSING" in _codes(report)


def test_unregistered_dir_detected(tmp_path):
    _write_skill_md(
        tmp_path / "development" / "skill" / "tmp-probe", raw="probe\n"
    )
    report = _run(tmp_path, _green_entries(), probe_dirs=["tmp-probe"])
    matches = [
        error
        for error in report["errors"]
        if error["code"] == "UNREGISTERED_SKILL" and error["skill"] == "tmp-probe"
    ]
    assert len(matches) == 1


def test_duplicate_names_rejected(tmp_path):
    entries = [
        _entry("dupe", "references/lib-a", "external"),
        _entry("dupe", "references/lib-b", "external"),
    ]
    report = _run(tmp_path, entries)
    assert "DUPLICATE_NAME" in _codes(report)


def test_unknown_composed_of_ref_rejected(tmp_path):
    entries = [
        _entry("spine-lib", "references/spine-lib", "external", composed_of=["ghost"])
    ]
    report = _run(tmp_path, entries)
    assert "COMPOSED_OF_UNKNOWN_REF" in _codes(report)


def test_invalid_scenario_value_rejected(tmp_path):
    entries = [
        _entry("spine-lib", "references/spine-lib", "external", scenarios=["wsl-bash"])
    ]
    report = _run(tmp_path, entries)
    assert "INVALID_SCENARIO" in _codes(report)


def test_report_shape_and_exit_code(tmp_path, monkeypatch, capsys):
    _write_skill_md(tmp_path / "development" / "skill" / "runtime-ops", name="runtime-ops")
    manifest = _build_tree(tmp_path, _green_entries())
    monkeypatch.setattr(sys, "argv", ["validate_skills.py", "--manifest", str(manifest)])
    exit_code = validate_skills.main()
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert exit_code == 0
    assert set(report) == {"ok", "manifest", "skills_checked", "errors"}
    assert report["ok"] is True
    assert report["skills_checked"] == 3
    assert report["errors"] == []

    broken = {"schema_version": 1, "skills": [
        _entry("dupe", "references/lib-a", "external"),
        _entry("dupe", "references/lib-b", "external"),
    ]}
    manifest.write_text(yaml.safe_dump(broken, sort_keys=False), encoding="utf-8")
    exit_code = validate_skills.main()
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert exit_code == 1
    assert report["ok"] is False
    assert report["skills_checked"] == 2
    for error in report["errors"]:
        assert set(error) == {"code", "skill", "message"}
    assert "DUPLICATE_NAME" in captured.err
