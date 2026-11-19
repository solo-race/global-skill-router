"""Tests for the pi-subagents duplicate-functionality filter merge."""

import copy
import importlib.util
import json
import sys
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "apply_pi_filter", Path(__file__).with_name("apply_pi_filter.py")
)
FILTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FILTER)

CANONICAL = Path(__file__).resolve().parents[1] / "references" / "pi-package-filter.json"
SOURCE = "npm:pi-subagents"


def _spec():
    return FILTER.load_filter(CANONICAL)


def test_canonical_filter_shape_is_the_adapter_contract():
    spec = _spec()
    entry = spec["packages"][0]
    assert entry["source"] == SOURCE
    assert entry["prompts"] == []
    assert entry["skills"] == ["!pi-subagents", "!council-mode"]
    assert set(spec["subagents"]["agentOverrides"]) == {
        "delegate", "oracle", "researcher", "evidence-auditor"
    }
    assert all(
        override == {"disabled": True}
        for override in spec["subagents"]["agentOverrides"].values()
    )


def test_merge_converts_a_plain_package_string_and_preserves_other_packages():
    settings = {"packages": [SOURCE, "npm:other-package"]}
    merged = FILTER.merge_settings(settings, _spec())
    assert merged["packages"] == [
        {"source": SOURCE, "prompts": [], "skills": ["!pi-subagents", "!council-mode"]},
        "npm:other-package",
    ]
    # The input mapping is never mutated.
    assert settings["packages"] == [SOURCE, "npm:other-package"]


def test_merge_preserves_unrelated_package_selectors_and_agent_override_fields():
    settings = {
        "packages": [
            {"source": SOURCE, "extensions": ["bundle/index.js"], "themes": []},
        ],
        "subagents": {
            "agentOverrides": {
                "worker": {"model": "fast-model"},
                "oracle": {"model": "pinned-model", "disabled": False},
            }
        },
        "lastChangelogVersion": "1.5.2",
    }
    merged = FILTER.merge_settings(settings, _spec())
    package = merged["packages"][0]
    assert package["extensions"] == ["bundle/index.js"]
    assert package["themes"] == []
    assert package["skills"] == ["!pi-subagents", "!council-mode"]
    assert merged["subagents"]["agentOverrides"]["worker"] == {"model": "fast-model"}
    assert merged["subagents"]["agentOverrides"]["oracle"] == {
        "model": "pinned-model",
        "disabled": True,
    }
    assert merged["lastChangelogVersion"] == "1.5.2"


def test_merge_is_idempotent():
    once = FILTER.merge_settings({"packages": [SOURCE]}, _spec())
    twice = FILTER.merge_settings(copy.deepcopy(once), _spec())
    assert once == twice


def test_changed_keys_reports_only_filter_owned_paths():
    current = {"packages": [SOURCE]}
    merged = FILTER.merge_settings(current, _spec())
    assert FILTER.changed_keys(current, merged) == [
        "packages",
        "subagents.agentOverrides.delegate.disabled",
        "subagents.agentOverrides.oracle.disabled",
        "subagents.agentOverrides.researcher.disabled",
        "subagents.agentOverrides.evidence-auditor.disabled",
    ]
    assert FILTER.changed_keys(merged, FILTER.merge_settings(merged, _spec())) == []


def test_missing_settings_file_reports_drift_and_apply_creates_it(tmp_path):
    settings_path = tmp_path / "settings.json"
    assert FILTER.main(["--settings", str(settings_path), "--filter", str(CANONICAL)]) == 1
    assert not settings_path.exists()

    assert FILTER.main(
        ["--settings", str(settings_path), "--filter", str(CANONICAL), "--apply"]
    ) == 0
    written = json.loads(settings_path.read_text(encoding="utf-8"))
    assert written["packages"][0]["skills"] == ["!pi-subagents", "!council-mode"]
    assert written["subagents"]["agentOverrides"]["delegate"] == {"disabled": True}

    # A second apply is a no-op verification pass.
    assert FILTER.main(["--settings", str(settings_path), "--filter", str(CANONICAL)]) == 0


def test_apply_preserves_unrelated_settings_on_disk(tmp_path):
    settings_path = tmp_path / "settings.json"
    original = {
        "packages": ["npm:other-package", SOURCE],
        "subagents": {"disableBuiltins": False},
        "extensionChangelogVersions": {"x": "1.0.0"},
    }
    settings_path.write_text(json.dumps(original), encoding="utf-8")
    assert FILTER.main(
        ["--settings", str(settings_path), "--filter", str(CANONICAL), "--apply"]
    ) == 0
    written = json.loads(settings_path.read_text(encoding="utf-8"))
    assert written["packages"][0] == "npm:other-package"
    assert written["packages"][1]["source"] == SOURCE
    assert written["subagents"]["disableBuiltins"] is False
    assert written["subagents"]["agentOverrides"]["researcher"] == {"disabled": True}
    assert written["extensionChangelogVersions"] == {"x": "1.0.0"}


def test_invalid_filter_shape_is_refused(tmp_path):
    broken = tmp_path / "filter.json"
    broken.write_text(json.dumps({"packages": [], "subagents": {"agentOverrides": {}}}), encoding="utf-8")
    assert FILTER.main(["--settings", str(tmp_path / "settings.json"), "--filter", str(broken)]) == 1
