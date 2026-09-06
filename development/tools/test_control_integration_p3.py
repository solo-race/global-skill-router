"""P3 control-plane integration tests.

These tests exercise the v3 registry as one control surface: optional sources,
skill lifecycle edges, entrypoint metadata, adapter ABI gates, deterministic
route projection, and the disposable growth-loop probe from plan 040.
"""

import importlib.util
import shutil
from pathlib import Path

import pytest
import yaml

_SPEC = importlib.util.spec_from_file_location(
    "validate_skills_under_test",
    Path(__file__).with_name("validate_skills.py"),
)
validate_skills = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(validate_skills)

SCENARIOS = ["win-access-vba", "win-android", "wsl-python"]


def _skill(name, status="active", scenarios=None, entrypoint=False, **overrides):
    entry = {
        "name": name,
        "path": f"development/skill/{name}",
        "status": status,
        "deployment_role": "module",
        "scenarios": list(scenarios or SCENARIOS),
        "deps": [],
        "composed_of": [],
        "entrypoint": entrypoint,
        "version": "0.1.0",
        "description": f"{name} test skill.",
    }
    entry.update(overrides)
    return entry


def _source(source_id="optional-source", path="references/missing", required=False):
    return {
        "id": source_id,
        "path": path,
        "kind": "local-reference",
        "required": required,
        "version": "0.1.0",
        "description": "Test source.",
    }


def _write_skill(root, name, metadata=False):
    skill_dir = root / "development" / "skill" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        f"name: {name}\n"
        f"description: {name} test skill. Use when exercising P3.\n"
        "---\n\nBody.\n",
        encoding="utf-8",
    )
    if metadata:
        metadata_dir = skill_dir / "agents"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        (metadata_dir / "openai.yaml").write_text(
            "interface:\n"
            f"  display_name: {name}\n"
            f"  short_description: {name} entrypoint\n"
            f"  default_prompt: Load ${name} for this task.\n",
            encoding="utf-8",
        )
    return skill_dir


def _write_adapter(root, owner, name="synthetic", *, environments=None,
                   capabilities=None, task_modes=None,
                   verification_model_kind="independent_checks",
                   mutation_support="bounded", recovery=True,
                   raw_frontmatter=None):
    adapter_dir = root / "development" / "skill" / owner / "adapters"
    adapter_dir.mkdir(parents=True, exist_ok=True)
    path = adapter_dir / f"{name}.md"
    if raw_frontmatter is not None:
        text = raw_frontmatter
    else:
        frontmatter = {
            "adapter_schema_version": 1,
            "adapter": name,
            "environments": environments or ["wsl-python"],
            "capabilities": capabilities or ["source.read"],
            "task_modes": task_modes or {"closed": False, "modes": ["inspect"]},
            "verification_model_kind": verification_model_kind,
            "mutation_support": mutation_support,
        }
        text = "---\n" + yaml.safe_dump(frontmatter, sort_keys=False) + "---\n\n"
        if recovery:
            text += "## 7. Recovery model\n\nRestore the transaction snapshot.\n"
    path.write_text(text, encoding="utf-8")
    return path


def _write_manifest(root, skills, sources=None, adapters=None):
    skills = list(skills)
    if not any(entry.get("name") == "global-skill-router" for entry in skills):
        _write_skill(root, "global-skill-router", metadata=True)
        active_names = [
            entry["name"]
            for entry in skills
            if entry.get("status") == "active"
        ]
        skills.append(
            {
                "name": "global-skill-router",
                "path": "development/skill/global-skill-router",
                "status": "active",
                "deployment_role": "router",
                "scenarios": list(SCENARIOS),
                "deps": [],
                "composed_of": active_names,
                "entrypoint": True,
                "version": "0.1.0",
                "description": "Synthetic router. Use when selecting a test module.",
            }
        )
    manifest = root / "development" / "skill" / "manifest.yaml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        yaml.safe_dump(
            {
                "schema_version": 3,
                "sources": list(sources or []),
                "skills": list(skills),
                "adapters": list(adapters or []),
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return manifest


def _adapter_entry(name, owner="runtime-ops", status="active", environments=None):
    return {
        "name": name,
        "path": f"development/skill/{owner}/adapters/{name}.md",
        "status": status,
        "owner_skill": owner,
        "environments": list(environments or ["wsl-python"]),
        "version": "0.1.0",
        "description": f"{name} test adapter.",
    }


def _codes(report):
    return [error["code"] for error in report["errors"]]


def test_real_manifest_v3_is_green_and_routes_are_explicit():
    report = validate_skills.validate(validate_skills.DEFAULT_MANIFEST)
    assert report["ok"] is True, report["errors"]
    assert report["sources_checked"] == 3
    assert report["adapters_checked"] == 4
    assert report["routes"]["win-access-vba"]["skills"] == [
        {"name": "global-skill-router", "status": "active"},
        {"name": "runtime-ops", "status": "active"}
    ]
    assert report["routes"]["win-access-vba"]["adapters"] == [
        {"name": "sql-server", "owner_skill": "runtime-ops", "status": "planned"},
        {"name": "vba-office", "owner_skill": "runtime-ops", "status": "active"},
    ]
    assert report["routes"]["win-android"]["adapters"] == [
        {"name": "android-gradle", "owner_skill": "runtime-ops", "status": "planned"}
    ]
    assert report["routes"]["wsl-python"]["skills"] == [
        {"name": "global-skill-router", "status": "active"},
        {"name": "research-investigation", "status": "active"}
    ]


def test_optional_source_may_be_missing_but_required_source_cannot(tmp_path):
    _write_skill(tmp_path, "base")
    optional_manifest = _write_manifest(
        tmp_path,
        [_skill("base")],
        sources=[_source(required=False)],
    )
    assert validate_skills.validate(optional_manifest)["ok"] is True

    required_manifest = _write_manifest(
        tmp_path,
        [_skill("base")],
        sources=[_source(required=True)],
    )
    report = validate_skills.validate(required_manifest)
    assert "SOURCE_PATH_MISSING" in _codes(report)


def test_source_path_escape_is_rejected_and_source_skill_names_can_coexist(tmp_path):
    _write_skill(tmp_path, "runtime-ops")
    escaped = _write_manifest(
        tmp_path,
        [_skill("runtime-ops")],
        sources=[_source("runtime-ops", "../outside")],
    )
    report = validate_skills.validate(escaped)
    assert "SOURCE_PATH_INVALID" in _codes(report)

    valid = _write_manifest(
        tmp_path,
        [_skill("runtime-ops")],
        sources=[_source("runtime-ops")],
    )
    report = validate_skills.validate(valid)
    assert report["ok"] is True, report["errors"]


def test_entrypoint_metadata_gate_requires_interface_and_trigger(tmp_path):
    _write_skill(tmp_path, "entry", metadata=False)
    manifest = _write_manifest(tmp_path, [_skill("entry", entrypoint=True)])
    report = validate_skills.validate(manifest)
    assert "ENTRYPOINT_METADATA_MISSING" in _codes(report)

    _write_skill(tmp_path, "entry", metadata=True)
    metadata = tmp_path / "development" / "skill" / "entry" / "agents" / "openai.yaml"
    metadata.write_text(
        "interface:\n"
        "  display_name: Entry\n"
        "  short_description: Entry\n"
        "  default_prompt: Do the task.\n",
        encoding="utf-8",
    )
    report = validate_skills.validate(manifest)
    assert "ENTRYPOINT_PROMPT_NO_TRIGGER" in _codes(report)

    metadata.unlink()
    non_entrypoint_manifest = _write_manifest(tmp_path, [_skill("entry", entrypoint=False)])
    report = validate_skills.validate(non_entrypoint_manifest)
    assert report["ok"] is True, report["errors"]


@pytest.mark.parametrize(
    "field,code",
    [("deps", "DEP_NOT_ACTIVE"), ("composed_of", "COMPOSED_OF_NOT_ACTIVE")],
)
def test_active_edge_cannot_target_planned_skill(tmp_path, field, code):
    _write_skill(tmp_path, "active")
    skills = [_skill("active", **{field: ["planned"]}), _skill("planned", status="planned")]
    report = validate_skills.validate(_write_manifest(tmp_path, skills))
    assert code in _codes(report)


def test_dependency_and_composition_cycles_are_reported_separately(tmp_path):
    for name in ("a", "b"):
        _write_skill(tmp_path, name)
    skills = [
        _skill("a", deps=["b"], composed_of=["b"]),
        _skill("b", deps=["a"], composed_of=["a"]),
    ]
    report = validate_skills.validate(_write_manifest(tmp_path, skills))
    codes = _codes(report)
    assert "DEP_CYCLE" in codes
    assert "COMPOSED_OF_CYCLE" in codes


def test_real_vba_adapter_and_synthetic_independent_checks_adapter_pass(tmp_path):
    real = validate_skills.validate(validate_skills.DEFAULT_MANIFEST)
    assert not any(error["code"].startswith("ADAPTER_") for error in real["errors"])

    _write_skill(tmp_path, "owner")
    _write_adapter(tmp_path, "owner", name="independent")
    manifest = _write_manifest(
        tmp_path,
        [_skill("owner")],
        adapters=[_adapter_entry("independent", owner="owner")],
    )
    report = validate_skills.validate(manifest)
    assert report["ok"] is True, report["errors"]


def test_planned_adapter_is_forward_registerable_but_file_is_gated_when_present(tmp_path):
    _write_skill(tmp_path, "owner")
    adapter = _adapter_entry("future", owner="owner", status="planned")
    manifest = _write_manifest(tmp_path, [_skill("owner")], adapters=[adapter])
    assert validate_skills.validate(manifest)["ok"] is True

    _write_adapter(tmp_path, "owner", name="future", raw_frontmatter="# no contract\n")
    report = validate_skills.validate(manifest)
    assert "ADAPTER_FRONTMATTER_MISSING" in _codes(report)


def test_duplicate_adapter_names_are_rejected(tmp_path):
    _write_skill(tmp_path, "owner")
    adapters = [
        _adapter_entry("duplicate", owner="owner", status="planned"),
        _adapter_entry("duplicate", owner="owner", status="planned"),
    ]
    report = validate_skills.validate(_write_manifest(tmp_path, [_skill("owner")], adapters=adapters))
    assert "DUPLICATE_ADAPTER_NAME" in _codes(report)


def test_adapter_owner_environment_and_recovery_gates(tmp_path):
    _write_skill(tmp_path, "owner")
    _write_adapter(tmp_path, "owner", name="broken", environments=["win-access-vba"], recovery=False)
    adapter = _adapter_entry("broken", owner="owner", environments=["wsl-python"])
    manifest = _write_manifest(tmp_path, [_skill("owner")], adapters=[adapter])
    report = validate_skills.validate(manifest)
    codes = _codes(report)
    assert "ADAPTER_ENVIRONMENT_MISMATCH" in codes
    assert "ADAPTER_RECOVERY_SECTION_MISSING" in codes

    unknown = _write_manifest(
        tmp_path,
        [_skill("owner")],
        adapters=[_adapter_entry("broken", owner="ghost")],
    )
    report = validate_skills.validate(unknown)
    assert "ADAPTER_OWNER_UNKNOWN" in _codes(report)


def _adapter_document(frontmatter, body="## 7. Recovery model\n\nRestore the transaction snapshot.\n"):
    return "---\n" + yaml.safe_dump(frontmatter, sort_keys=False) + "---\n\n" + body


def _valid_adapter_frontmatter(name="broken"):
    return {
        "adapter_schema_version": 1,
        "adapter": name,
        "environments": ["wsl-python"],
        "capabilities": ["source.read"],
        "task_modes": {"closed": False, "modes": ["inspect"]},
        "verification_model_kind": "independent_checks",
        "mutation_support": "bounded",
    }


@pytest.mark.parametrize(
    "mutate, code",
    [
        (lambda value: value.update(adapter_schema_version=2), "ADAPTER_SCHEMA_VERSION_UNSUPPORTED"),
        (lambda value: value.update(adapter="other"), "ADAPTER_ID_MISMATCH"),
        (lambda value: value.update(environments=[]), "ADAPTER_ENVIRONMENTS_INVALID"),
        (lambda value: value.update(environments=["unknown"]), "ADAPTER_ENVIRONMENTS_INVALID"),
        (lambda value: value.update(environments=["wsl-python", "wsl-python"]), "ADAPTER_ENVIRONMENTS_INVALID"),
        (lambda value: value.update(capabilities=[]), "ADAPTER_CAPABILITIES_INVALID"),
        (lambda value: value.update(capabilities=["source.read", "source.read"]), "ADAPTER_CAPABILITY_DUPLICATE"),
        (lambda value: value.update(task_modes={"modes": ["inspect"]}), "ADAPTER_TASK_MODES_INVALID"),
        (lambda value: value.update(task_modes={"closed": "false", "modes": ["inspect"]}), "ADAPTER_TASK_MODES_INVALID"),
        (lambda value: value.update(task_modes={"closed": False, "modes": []}), "ADAPTER_TASK_MODES_INVALID"),
        (lambda value: value.update(task_modes={"closed": False, "modes": ["inspect", "inspect"]}), "ADAPTER_TASK_MODES_INVALID"),
        (lambda value: value.update(verification_model_kind="unknown"), "ADAPTER_VERIFICATION_KIND_INVALID"),
        (lambda value: value.update(mutation_support="unknown"), "ADAPTER_MUTATION_SUPPORT_INVALID"),
    ],
)
def test_adapter_abi_negative_matrix(tmp_path, mutate, code):
    _write_skill(tmp_path, "owner")
    frontmatter = _valid_adapter_frontmatter()
    mutate(frontmatter)
    _write_adapter(
        tmp_path,
        "owner",
        name="broken",
        raw_frontmatter=_adapter_document(frontmatter),
    )
    report = validate_skills.validate(
        _write_manifest(
            tmp_path,
            [_skill("owner")],
            adapters=[_adapter_entry("broken", owner="owner")],
        )
    )
    assert code in _codes(report)


def test_mutating_adapter_requires_nonempty_recovery_section(tmp_path):
    _write_skill(tmp_path, "owner")
    frontmatter = _valid_adapter_frontmatter()
    _write_adapter(
        tmp_path,
        "owner",
        name="broken",
        raw_frontmatter=_adapter_document(
            frontmatter,
            "## 7. Recovery model\n\n## 8. Environment\nNormal environment.\n",
        ),
    )
    report = validate_skills.validate(
        _write_manifest(
            tmp_path,
            [_skill("owner")],
            adapters=[_adapter_entry("broken", owner="owner")],
        )
    )
    assert "ADAPTER_RECOVERY_SECTION_MISSING" in _codes(report)


def test_non_mutating_adapter_does_not_require_recovery_section(tmp_path):
    _write_skill(tmp_path, "owner")
    _write_adapter(tmp_path, "owner", name="readonly", mutation_support="none", recovery=False)
    report = validate_skills.validate(
        _write_manifest(
            tmp_path,
            [_skill("owner")],
            adapters=[_adapter_entry("readonly", owner="owner")],
        )
    )
    assert report["ok"] is True, report["errors"]


def test_adapter_manifest_name_and_file_stem_must_match(tmp_path):
    _write_skill(tmp_path, "owner")
    frontmatter = _valid_adapter_frontmatter(name="manifest-name")
    _write_adapter(
        tmp_path,
        "owner",
        name="file-name",
        raw_frontmatter=_adapter_document(frontmatter),
    )
    manifest_entry = _adapter_entry("manifest-name", owner="owner")
    manifest_entry["path"] = "development/skill/owner/adapters/file-name.md"
    report = validate_skills.validate(
        _write_manifest(tmp_path, [_skill("owner")], adapters=[manifest_entry])
    )
    assert "ADAPTER_ID_MISMATCH" in _codes(report)


@pytest.mark.parametrize(
    "path",
    [
        "../escape.md",
        "development/skill/other/adapters/broken.md",
        "development/skill/owner/adapters/other.md",
    ],
)
def test_adapter_canonical_path_gate(tmp_path, path):
    _write_skill(tmp_path, "owner")
    _write_adapter(tmp_path, "owner", name="broken")
    entry = _adapter_entry("broken", owner="owner")
    entry["path"] = path
    report = validate_skills.validate(
        _write_manifest(tmp_path, [_skill("owner")], adapters=[entry])
    )
    assert "ADAPTER_PATH_INVALID" in _codes(report)


@pytest.mark.parametrize("owner_status, code", [("planned", "ADAPTER_OWNER_NOT_ACTIVE"), ("unknown", "ADAPTER_OWNER_UNKNOWN")])
def test_active_adapter_owner_must_be_active_and_registered(tmp_path, owner_status, code):
    owner = "owner" if owner_status == "planned" else "ghost"
    if owner_status == "planned":
        _write_skill(tmp_path, owner)
        skills = [_skill(owner, status="planned")]
    else:
        _write_skill(tmp_path, "base")
        skills = [_skill("base")]
    _write_adapter(tmp_path, "owner", name="broken")
    report = validate_skills.validate(
        _write_manifest(
            tmp_path,
            skills,
            adapters=[_adapter_entry("broken", owner=owner)],
        )
    )
    assert code in _codes(report)


def test_route_projection_is_deterministic_and_keeps_planned_distinct(tmp_path):
    _write_skill(tmp_path, "base")
    skills = [_skill("zeta", status="planned"), _skill("base")]
    adapters = [
        _adapter_entry("zeta-adapter", owner="base", status="planned"),
        _adapter_entry("alpha-adapter", owner="base", status="planned"),
    ]
    report = validate_skills.validate(_write_manifest(tmp_path, skills, adapters=adapters))
    assert report["ok"] is True, report["errors"]
    assert [item["name"] for item in report["routes"]["wsl-python"]["skills"]] == [
        "base",
        "global-skill-router",
        "zeta",
    ]
    assert [item["name"] for item in report["routes"]["wsl-python"]["adapters"]] == [
        "alpha-adapter",
        "zeta-adapter",
    ]
    assert all(item["status"] == "planned" for item in report["routes"]["wsl-python"]["adapters"])


def test_disposable_growth_loop_register_validate_route_negative_gate_and_remove(tmp_path):
    _write_skill(tmp_path, "base")
    _write_skill(tmp_path, "probe-worker")
    _write_skill(tmp_path, "probe-orchestrator", metadata=True)
    worker = _skill("probe-worker", entrypoint=False)
    orchestrator = _skill(
        "probe-orchestrator",
        entrypoint=True,
        composed_of=["probe-worker"],
    )
    base = _skill("base")
    manifest = _write_manifest(tmp_path, [worker, orchestrator, base])

    report = validate_skills.validate(manifest)
    assert report["ok"] is True, report["errors"]
    assert any(item["name"] == "probe-orchestrator" for item in report["routes"]["wsl-python"]["skills"])

    worker["status"] = "planned"
    _write_manifest(tmp_path, [worker, orchestrator, base])
    report = validate_skills.validate(manifest)
    assert "COMPOSED_OF_NOT_ACTIVE" in _codes(report)

    worker["status"] = "active"
    _write_manifest(tmp_path, [worker, orchestrator, base])
    assert validate_skills.validate(manifest)["ok"] is True

    for name in ("probe-worker", "probe-orchestrator"):
        shutil.rmtree(tmp_path / "development" / "skill" / name)
    _write_manifest(tmp_path, [base])
    report = validate_skills.validate(manifest)
    assert report["ok"] is True, report["errors"]
