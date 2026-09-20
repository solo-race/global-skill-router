"""P6 M4 gates for the assembled VBA bundle and selective adapter contract."""

import importlib.util
import re
from pathlib import Path

import pytest
import yaml


SPEC = importlib.util.spec_from_file_location(
    "deploy_skills", Path(__file__).with_name("deploy_skills.py")
)
deploy_skills = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(deploy_skills)

RUNTIME_ROOT = Path(__file__).resolve().parents[1] / "skill" / "runtime-ops"
BUNDLE_FILES = (
    "workflows/vba-office/diagnose.md",
    "workflows/vba-office/modify.md",
    "workflows/vba-office/review.md",
    "workflows/vba-office/test.md",
    "references/vba-office/shared/sources.md",
    "references/vba-office/shared/error-handling.md",
    "references/vba-office/shared/vba-encoding.md",
    "references/vba-office/access/saveastext-source.md",
    "references/vba-office/access/form-lifecycle.md",
    "references/vba-office/access/controls.md",
    "references/vba-office/access/record-navigation.md",
    "references/vba-office/access/form-state.md",
    "references/vba-office/access/dao.md",
    "references/vba-office/excel/workbook-worksheet-model.md",
    "references/vba-office/excel/worksheet-events.md",
    "references/vba-office/excel/userform-model.md",
    "references/vba-office/excel/ribbon-xml.md",
    "references/vba-office/excel/addin-xlam.md",
    "scripts/vba-office/extract_access_saveastext.py",
    "scripts/vba-office/test_extract_access_saveastext.py",
)


@pytest.fixture(scope="module")
def payload_root(tmp_path_factory):
    staging = tmp_path_factory.mktemp("vba-m4-payload")
    return deploy_skills.build_payload(
        deploy_skills.DEFAULT_MANIFEST, staging
    )["payload_root"]


@pytest.fixture(scope="module")
def adapter():
    return (RUNTIME_ROOT / "adapters" / "vba-office.md").read_text(encoding="utf-8")


def _section(text, heading):
    assert heading in text, f"Missing adapter contract section: {heading}"
    return text.split(heading, 1)[1].split("\n## ", 1)[0]


def test_assembled_vba_bundle_is_complete_without_duplicate_contract_trees(payload_root):
    runtime = payload_root / "library" / "runtime-ops"
    for relative in BUNDLE_FILES:
        assert (runtime / relative).is_file(), f"VBA payload omitted {relative}"
    for directory in ("tool-contracts", "profiles"):
        assert not (runtime / directory).exists(), (
            f"VBA ABI/profile policy must remain in the adapter, not {directory}/"
        )


def test_lazy_load_paths_are_present_and_skill_root_contained(adapter, payload_root):
    index = _section(adapter, "### Lazy-load index")
    listed = {
        value for value in re.findall(r"`([^`]+)`", index)
        if "/" in value and value.endswith((".md", ".py"))
    }
    expected = set(BUNDLE_FILES) - {"scripts/vba-office/test_extract_access_saveastext.py"}
    assert expected <= listed, f"Lazy-load index omitted: {sorted(expected - listed)}"
    for relative in listed:
        assert not Path(relative).is_absolute(), f"Absolute lazy-load path: {relative}"
        assert "references/access-vba-dev" not in relative, (
            f"Runtime path depends on repository provenance: {relative}"
        )
        for root in (RUNTIME_ROOT, payload_root / "library" / "runtime-ops"):
            resolved = (root / relative).resolve()
            assert root.resolve() in resolved.parents, f"Lazy-load path escapes skill root: {relative}"
            assert resolved.is_file(), f"Missing lazy-load file under {root}: {relative}"


def test_vba_verification_keeps_compile_dispatch_unverified(adapter):
    frontmatter = yaml.safe_load(adapter.split("---", 2)[1])
    assert frontmatter["verification_model_kind"] == "independent_checks"
    verification = _section(adapter, "## 6. Verification model")
    compile_row = next(line for line in verification.splitlines() if line.startswith("| Compile |"))
    assert "Access compile is unsupported" in compile_row
    assert 'status: "unverified"' in compile_row
    assert "compile: unverified via vba-doctor" in compile_row
    assert "compile dispatch: unverified" in compile_row
    assert "no check implies another" in verification
    assert not re.search(r"\blinear\b|highest[- ]achieved", adapter, re.IGNORECASE), (
        "VBA verification must not revert to a linear/highest-achieved ladder"
    )
    dispatch = next(line for line in adapter.splitlines() if line.startswith("- `compile_vba_project("))
    assert 'status: "unverified"' in dispatch
    assert "dispatch never establishes Compile Verified" in dispatch, (
        "Excel compile dispatch must explicitly deny Compile Verified evidence"
    )


def test_access_baseline_is_no_argument_public_function_through_eval(adapter):
    execution = next(line for line in adapter.splitlines() if line.startswith("- `run_macro("))
    plain = execution.replace("`", "").replace("**", "")
    assert "no-argument Public Function invoked through Eval" in plain
    assert 'without args uses Application.Eval("MacroName()")' in plain
    assert "with args uses Application.Run(macro_name, *args)" in plain
    assert "do not substitute a parameterized macro or an ordinary Public Sub" in plain


@pytest.mark.parametrize("scenario", ["win-access-vba", "win-android", "wsl-python"])
def test_runtime_ops_is_only_in_the_office_scenario(payload_root, scenario):
    shard = yaml.safe_load(
        (payload_root / "_platform" / "routes" / f"{scenario}.yaml").read_text(encoding="utf-8")
    )
    names = [item["name"] for item in shard["skills"]]
    assert ("runtime-ops" in names) == (scenario == "win-access-vba"), (
        f"Unexpected runtime-ops route in {scenario}: {names}"
    )
    for entry in shard["skills"]:
        assert entry["skill_path"] == f"library/{entry['name']}/SKILL.md", (
            "Scenario routes select module entrypoints, never VBA companion files"
        )


def test_no_match_index_and_adapter_preserve_selective_loading(payload_root, adapter):
    # A no-match task stops at the index; do not invent a runtime router here.
    index_text = (payload_root / "_platform" / "routes" / "index.yaml").read_text(encoding="utf-8")
    index = yaml.safe_load(index_text)
    assert all(entry["name"] != "runtime-ops" for entry in index["global_routes"])
    assert "library/runtime-ops" not in index_text
    assert "vba-office" not in index_text, "The route index must not preload VBA companion paths"

    lazy = _section(adapter, "### Lazy-load index")
    assert "Load only the selected workflow and references needed for the identified host and question" in lazy
    assert "never scan or preload the whole `references/vba-office` tree" in lazy
    assert "Load the other host's references only for an explicit cross-host question" in lazy
    assert "add host references only when the test depends on their semantics" in lazy
