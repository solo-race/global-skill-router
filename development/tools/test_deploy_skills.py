"""Focused tests for the P4 routed deployment manager."""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
from pathlib import Path

import pytest
import yaml


SCRIPT = Path(__file__).with_name("deploy_skills.py")
SPEC = importlib.util.spec_from_file_location("deploy_skills", SCRIPT)
deploy_skills = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(deploy_skills)


SCENARIOS = ["win-access-vba", "win-android", "wsl-python"]


def _write_skill(root: Path, name: str, *, role: str, description: str | None = None) -> Path:
    skill = root / "development" / "skill" / name
    skill.mkdir(parents=True, exist_ok=True)
    description = description or f"{name} module. Use when the matching scenario is selected."
    (skill / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n\nUse this module only after route selection.\n",
        encoding="utf-8",
    )
    (skill / "agents").mkdir(exist_ok=True)
    (skill / "agents" / "openai.yaml").write_text(
        "interface:\n"
        f"  display_name: {name}\n"
        f"  short_description: {name} route.\n"
        f"  default_prompt: Load ${name}.\n",
        encoding="utf-8",
    )
    return skill


def _write_adapter(
    root: Path,
    owner: str,
    name: str,
    *,
    status: str = "active",
    environments: list[str] | None = None,
) -> Path:
    adapter_dir = root / "development" / "skill" / owner / "adapters"
    adapter_dir.mkdir(parents=True, exist_ok=True)
    path = adapter_dir / f"{name}.md"
    environments = environments or ["wsl-python"]
    path.write_text(
        "---\n"
        "adapter_schema_version: 1\n"
        f"adapter: {name}\n"
        f"environments: [{', '.join(environments)}]\n"
        "capabilities: [source.read]\n"
        "task_modes:\n"
        "  closed: false\n"
        "  modes: [inspect]\n"
        "verification_model_kind: independent_checks\n"
        "mutation_support: none\n"
        "---\n\n"
        f"# {name}\n\n{status} adapter fixture.\n",
        encoding="utf-8",
    )
    return path


def _fixture_repo(
    tmp_path: Path,
    module_count: int = 2,
    planned: bool = False,
    module_scenarios: list[str] | None = None,
    adapter_fixture: bool = False,
) -> tuple[Path, list[str]]:
    root = tmp_path / "repo"
    skill_root = root / "development" / "skill"
    router = _write_skill(root, "global-skill-router", role="router")
    module_names = [f"module-{index:02d}" for index in range(module_count)]
    for name in module_names:
        _write_skill(root, name, role="module")
    skills = [
        {
            "name": name,
            "path": f"development/skill/{name}",
            "status": "active",
            "deployment_role": "module",
            "routing_priority": 0,
            "routing_outcome": "terminal",
            "scenarios": [
                module_scenarios[index]
                if module_scenarios is not None
                else "wsl-python"
            ],
            "deps": [],
            "composed_of": [],
            "entrypoint": True,
            "version": "0.1.0",
            "description": f"{name} framework. Use when routed.",
        }
        for index, name in enumerate(module_names)
    ]
    adapters = []
    if adapter_fixture:
        active_path = _write_adapter(root, module_names[0], "active-adapter")
        planned_path = _write_adapter(root, module_names[0], "planned-adapter", status="planned")
        adapters = [
            {
                "name": "active-adapter",
                "path": active_path.relative_to(root).as_posix(),
                "status": "active",
                "owner_skill": module_names[0],
                "environments": ["wsl-python"],
                "version": "0.1.0",
                "description": "Active adapter fixture.",
            },
            {
                "name": "planned-adapter",
                "path": planned_path.relative_to(root).as_posix(),
                "status": "planned",
                "owner_skill": module_names[0],
                "environments": ["wsl-python"],
                "version": "0.1.0",
                "description": "Planned adapter fixture.",
            },
        ]
    if planned:
        planned_name = "module-planned"
        _write_skill(root, planned_name, role="module")
        skills.append(
            {
                "name": planned_name,
                "path": f"development/skill/{planned_name}",
                "status": "planned",
                "deployment_role": "module",
                "routing_priority": 0,
                "routing_outcome": "terminal",
                "scenarios": ["wsl-python"],
                "deps": [],
                "composed_of": [],
                "entrypoint": True,
                "version": "0.1.0",
                "description": "Planned module. Use when it becomes active.",
            }
        )
    skills.append(
        {
            "name": "global-skill-router",
            "path": "development/skill/global-skill-router",
            "status": "active",
            "deployment_role": "router",
            "scenarios": SCENARIOS,
            "deps": [],
            "composed_of": module_names,
            "entrypoint": True,
            "version": "0.1.0",
            "description": "Thin router. Use when selecting a managed module.",
        }
    )
    manifest = skill_root / "manifest.yaml"
    manifest.write_text(
        yaml.safe_dump(
            {"schema_version": 4, "sources": [], "skills": skills, "adapters": adapters},
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    assert router.is_dir()
    return manifest, module_names


def _build(manifest: Path, tmp_path: Path):
    staging = tmp_path / "staging"
    staging.mkdir(parents=True)
    return deploy_skills.build_payload(manifest, staging)


def test_first_install_and_legacy_coexistence(tmp_path):
    manifest, module_names = _fixture_repo(tmp_path)
    payload = _build(manifest, tmp_path)
    target_root = tmp_path / "skills"
    legacy = target_root / "vba-skill"
    legacy.mkdir(parents=True)
    legacy_file = legacy / "legacy.txt"
    legacy_file.write_text("leave me", encoding="utf-8")

    result = deploy_skills.apply_payload(target_root, payload)

    assert result["action"] == "applied"
    assert deploy_skills.verify_target(target_root)["ok"]
    assert sorted(path.name for path in target_root.iterdir()) == [
        "global-skill-router",
        "vba-skill",
    ]
    assert sorted(path.name for path in (target_root / "global-skill-router" / "library").iterdir()) == module_names
    assert legacy_file.read_text(encoding="utf-8") == "leave me"


def test_real_payload_has_only_router_discovery_entrypoint(tmp_path):
    payload = _build(deploy_skills.DEFAULT_MANIFEST, tmp_path / "staging")
    router = payload["payload_root"]
    library = router / "library"
    discovery_roots = {
        path.parent for path in router.parent.rglob("SKILL.md")
    } | {
        path.parent.parent for path in router.parent.rglob("agents/openai.yaml")
    }

    assert discovery_roots == {router}
    assert (router / "SKILL.md").is_file()
    assert not list(library.rglob("SKILL.md"))
    assert not list(library.rglob("agents/openai.yaml"))
    for module in payload["modules"]:
        source = deploy_skills.DEFAULT_MANIFEST.parent / module["name"]
        deployed = library / module["name"]
        assert (deployed / "MODULE.md").read_bytes() == (source / "SKILL.md").read_bytes()
        assert (source / "agents" / "openai.yaml").is_file()
        assert not (source / "MODULE.md").exists()
    source_agents = deploy_skills.DEFAULT_MANIFEST.parent / "development-delegation" / "agents"
    profiles = list(source_agents.glob("*.toml"))
    assert profiles
    for profile in profiles:
        deployed = library / "development-delegation" / "agents" / profile.name
        assert deployed.read_bytes() == profile.read_bytes()


@pytest.mark.parametrize("relative", ["references/nested/SKILL.md", "references/nested/agents/openai.yaml"])
def test_build_rejects_nested_module_discovery_files(tmp_path, relative):
    manifest, _ = _fixture_repo(tmp_path)
    forbidden = manifest.parent / "module-00" / relative
    forbidden.parent.mkdir(parents=True)
    forbidden.write_text("unexpected discovery file\n", encoding="utf-8")

    with pytest.raises(deploy_skills.DeploymentError, match="forbidden discovery entrypoint"):
        _build(manifest, tmp_path / "staging")


@pytest.mark.parametrize("relative", ["SKILL.md", "agents/openai.yaml", "references/nested/SKILL.md", "references/nested/agents/openai.yaml"])
def test_cli_verify_rejects_module_discovery_files(tmp_path, capsys, monkeypatch, relative):
    payload = _build(deploy_skills.DEFAULT_MANIFEST, tmp_path / "staging")
    target = tmp_path / "skills"
    deploy_skills.apply_payload(target, payload)
    forbidden = target / "global-skill-router" / "library" / "runtime-ops" / relative
    forbidden.parent.mkdir(parents=True, exist_ok=True)
    forbidden.write_text("unexpected discovery file\n", encoding="utf-8")
    monkeypatch.setattr(deploy_skills, "REPO_ROOT", tmp_path)

    assert deploy_skills.main(["--verify", "--target-root", str(target)]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["ok"] is False
    assert f"library contains forbidden discovery entrypoint: library/runtime-ops/{relative}" in result["errors"]
    assert forbidden.is_file()


def test_verify_requires_router_discovery_entrypoint(tmp_path):
    manifest, _ = _fixture_repo(tmp_path)
    payload = _build(manifest, tmp_path / "staging")
    target = tmp_path / "skills"
    deploy_skills.apply_payload(target, payload)
    (target / "global-skill-router" / "SKILL.md").unlink()

    result = deploy_skills.verify_target(target)

    assert result["ok"] is False
    assert "router discovery entrypoint SKILL.md is missing" in result["errors"]


def test_noop_and_content_update(tmp_path):
    manifest, _ = _fixture_repo(tmp_path)
    target_root = tmp_path / "skills"
    legacy = target_root / "vba-skill" / "legacy.bin"
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"legacy bytes")
    first = _build(manifest, tmp_path / "first")
    assert deploy_skills.apply_payload(target_root, first)["action"] == "applied"

    second = _build(manifest, tmp_path / "second")
    assert deploy_skills.apply_payload(target_root, second)["action"] == "noop"

    module_file = manifest.parent / "module-00" / "SKILL.md"
    module_file.write_text(module_file.read_text(encoding="utf-8") + "\nupdated\n", encoding="utf-8")
    updated = _build(manifest, tmp_path / "updated")
    assert deploy_skills.apply_payload(target_root, updated)["action"] == "applied"
    assert "updated" in (target_root / "global-skill-router" / "library" / "module-00" / "MODULE.md").read_text(encoding="utf-8")
    assert legacy.read_bytes() == b"legacy bytes"


def test_failure_recovery_restores_previous_payload(tmp_path, monkeypatch):
    manifest, _ = _fixture_repo(tmp_path)
    target_root = tmp_path / "skills"
    legacy = target_root / "vba-skill" / "legacy.bin"
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"legacy bytes")
    first = _build(manifest, tmp_path / "first")
    deploy_skills.apply_payload(target_root, first)
    old_text = (target_root / "global-skill-router" / "library" / "module-00" / "MODULE.md").read_text(encoding="utf-8")
    module_file = manifest.parent / "module-00" / "SKILL.md"
    module_file.write_text(old_text + "\nnew version\n", encoding="utf-8")
    updated = _build(manifest, tmp_path / "updated")

    original_verify = deploy_skills.verify_target
    calls = []

    def fail_once(*args, **kwargs):
        calls.append(True)
        if len(calls) == 1:
            return {"ok": False, "errors": ["injected verify failure"]}
        return original_verify(*args, **kwargs)

    monkeypatch.setattr(deploy_skills, "verify_target", fail_once)
    with pytest.raises(deploy_skills.DeploymentError, match="previous snapshot restored and verified"):
        deploy_skills.apply_payload(target_root, updated)
    assert (target_root / "global-skill-router" / "library" / "module-00" / "MODULE.md").read_text(encoding="utf-8") == old_text
    assert original_verify(target_root)["ok"]
    assert legacy.read_bytes() == b"legacy bytes"


def test_failure_recovery_failure_retains_manual_snapshot_path(tmp_path, monkeypatch):
    manifest, _ = _fixture_repo(tmp_path)
    target_root = tmp_path / "skills"
    first = _build(manifest, tmp_path / "first")
    deploy_skills.apply_payload(target_root, first)
    module_file = manifest.parent / "module-00" / "SKILL.md"
    module_file.write_text(module_file.read_text(encoding="utf-8") + "\nnew\n", encoding="utf-8")
    updated = _build(manifest, tmp_path / "updated")

    monkeypatch.setattr(
        deploy_skills,
        "verify_target",
        lambda *args, **kwargs: {"ok": False, "errors": ["injected verify failure"]},
    )
    with pytest.raises(deploy_skills.DeploymentError, match="manual recovery snapshot") as caught:
        deploy_skills.apply_payload(target_root, updated)
    snapshot = deploy_skills.backup_root(target_root) / "previous"
    assert str(snapshot) in str(caught.value)
    assert snapshot.is_dir()


def test_rollback_restores_previous_snapshot(tmp_path):
    manifest, _ = _fixture_repo(tmp_path)
    target_root = tmp_path / "skills"
    legacy = target_root / "vba-skill" / "legacy.bin"
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"legacy bytes")
    first = _build(manifest, tmp_path / "first")
    deploy_skills.apply_payload(target_root, first)
    module_file = manifest.parent / "module-00" / "SKILL.md"
    module_file.write_text(module_file.read_text(encoding="utf-8") + "\nsecond\n", encoding="utf-8")
    second = _build(manifest, tmp_path / "second")
    deploy_skills.apply_payload(target_root, second)
    assert "second" in (target_root / "global-skill-router" / "library" / "module-00" / "MODULE.md").read_text(encoding="utf-8")

    result = deploy_skills.rollback_payload(target_root)

    assert result["action"] == "rollback"
    assert "second" not in (target_root / "global-skill-router" / "library" / "module-00" / "MODULE.md").read_text(encoding="utf-8")
    assert deploy_skills.verify_target(target_root)["ok"]
    assert legacy.read_bytes() == b"legacy bytes"


def test_rollback_failure_restores_current_payload_and_keeps_snapshot(tmp_path, monkeypatch):
    manifest, _ = _fixture_repo(tmp_path)
    target_root = tmp_path / "skills"
    first = _build(manifest, tmp_path / "first")
    deploy_skills.apply_payload(target_root, first)
    module_file = manifest.parent / "module-00" / "SKILL.md"
    module_file.write_text(module_file.read_text(encoding="utf-8") + "\nsecond\n", encoding="utf-8")
    second = _build(manifest, tmp_path / "second")
    deploy_skills.apply_payload(target_root, second)
    original_verify = deploy_skills.verify_target
    calls = []

    def fail_once(*args, **kwargs):
        calls.append(True)
        if len(calls) == 1:
            return {"ok": False, "errors": ["injected rollback verification failure"]}
        return original_verify(*args, **kwargs)

    monkeypatch.setattr(deploy_skills, "verify_target", fail_once)
    with pytest.raises(deploy_skills.DeploymentError, match="current payload restored and verified"):
        deploy_skills.rollback_payload(target_root)
    assert "second" in (target_root / "global-skill-router" / "library" / "module-00" / "MODULE.md").read_text(encoding="utf-8")
    assert original_verify(target_root)["ok"]
    assert (deploy_skills.backup_root(target_root) / "previous").is_dir()


def test_drift_is_reported_without_overwrite(tmp_path):
    manifest, _ = _fixture_repo(tmp_path)
    target_root = tmp_path / "skills"
    deploy_skills.apply_payload(target_root, _build(manifest, tmp_path / "staging"))
    installed = target_root / "global-skill-router" / "library" / "module-00" / "MODULE.md"
    installed.write_text(installed.read_text(encoding="utf-8") + "\nmanual edit\n", encoding="utf-8")

    result = deploy_skills.verify_target(target_root)

    assert result["ok"] is False
    assert any("hash mismatch" in error for error in result["errors"])
    assert "manual edit" in installed.read_text(encoding="utf-8")


def test_planned_module_is_excluded(tmp_path):
    manifest, module_names = _fixture_repo(tmp_path, planned=True)
    payload = _build(manifest, tmp_path / "staging")
    names = [item["name"] for item in payload["state"]["modules"]]
    assert names == module_names
    assert not (payload["payload_root"] / "library" / "module-planned").exists()
    assert "module-planned" not in (payload["payload_root"] / "_platform" / "routes" / "wsl-python.yaml").read_text(encoding="utf-8")


def test_route_index_paths_selectors_and_self_validation(tmp_path):
    manifest, _ = _fixture_repo(tmp_path)
    payload = _build(manifest, tmp_path / "staging")
    index_path = payload["payload_root"] / "_platform" / "routes" / "index.yaml"
    index = yaml.safe_load(index_path.read_text(encoding="utf-8"))

    assert deploy_skills._validate_route_index(index, payload["payload_root"])
    assert index["schema_version"] == 4
    assert index["global_routes"] == []
    assert {item["name"] for item in index["scenarios"]} == set(SCENARIOS)
    for item in index["scenarios"]:
        assert item["shard"] == f"_platform/routes/{item['name']}.yaml"
        assert item["selector"]
        assert item["name"] not in item["selector"]

    index["scenarios"][0]["shard"] = "routes/win-access-vba.yaml"
    with pytest.raises(deploy_skills.DeploymentError, match="_platform/routes"):
        deploy_skills._validate_route_index(index, payload["payload_root"])


@pytest.mark.parametrize("bad_path", ["/absolute.yaml", "_platform/routes/../escape.yaml"])
def test_route_index_rejects_absolute_or_parent_paths(tmp_path, bad_path):
    manifest, _ = _fixture_repo(tmp_path)
    payload = _build(manifest, tmp_path / "staging")
    index = yaml.safe_load(
        (payload["payload_root"] / "_platform" / "routes" / "index.yaml").read_text(encoding="utf-8")
    )
    index["scenarios"][0]["shard"] = bad_path
    with pytest.raises(deploy_skills.DeploymentError):
        deploy_skills._validate_route_index(index, payload["payload_root"])


def test_route_index_rejects_unregistered_shard_file(tmp_path):
    manifest, _ = _fixture_repo(tmp_path)
    payload = _build(manifest, tmp_path / "staging")
    extra = payload["payload_root"] / "_platform" / "routes" / "extra.yaml"
    extra.write_text("scenario: extra\nskills: []\n", encoding="utf-8")
    index = yaml.safe_load(
        (payload["payload_root"] / "_platform" / "routes" / "index.yaml").read_text(encoding="utf-8")
    )
    with pytest.raises(deploy_skills.DeploymentError, match="shard set mismatch"):
        deploy_skills._validate_route_index(index, payload["payload_root"])


def test_planned_adapter_file_is_excluded_from_assembled_payload(tmp_path):
    manifest, _ = _fixture_repo(tmp_path, adapter_fixture=True)
    payload = _build(manifest, tmp_path / "staging")
    module_root = payload["payload_root"] / "library" / "module-00"

    assert (module_root / "adapters" / "active-adapter.md").is_file()
    assert not (module_root / "adapters" / "planned-adapter.md").exists()
    assert (manifest.parent / "module-00" / "adapters" / "planned-adapter.md").is_file()
    route_text = (payload["payload_root"] / "_platform" / "routes" / "wsl-python.yaml").read_text(encoding="utf-8")
    assert "planned-adapter" not in route_text


def test_v4_route_contains_active_adapters_with_owner_and_scenario_closure(tmp_path):
    manifest, module_names = _fixture_repo(tmp_path, adapter_fixture=True)
    registry = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    second_active = _write_adapter(tmp_path / "repo", module_names[0], "second-adapter")
    other_owner = _write_adapter(tmp_path / "repo", module_names[1], "other-owner")
    android_only = _write_adapter(
        tmp_path / "repo", module_names[0], "android-only", environments=["win-android"]
    )
    for name, path, owner, environments in (
        ("second-adapter", second_active, module_names[0], ["wsl-python"]),
        ("other-owner", other_owner, module_names[1], ["wsl-python"]),
        ("android-only", android_only, module_names[0], ["win-android"]),
    ):
        registry["adapters"].append(
            {
                "name": name,
                "path": path.relative_to(tmp_path / "repo").as_posix(),
                "status": "active",
                "owner_skill": owner,
                "environments": environments,
                "version": "0.1.0",
                "description": f"{name} adapter fixture.",
            }
        )
    manifest.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")

    payload = _build(manifest, tmp_path / "staging")
    shard = yaml.safe_load(
        (payload["payload_root"] / "_platform" / "routes" / "wsl-python.yaml").read_text(
            encoding="utf-8"
        )
    )
    module_zero = next(item for item in shard["skills"] if item["name"] == module_names[0])
    module_one = next(item for item in shard["skills"] if item["name"] == module_names[1])

    assert [item["name"] for item in module_zero["adapters"]] == [
        "active-adapter",
        "second-adapter",
    ]
    assert module_zero["adapters"][0] == {
        "name": "active-adapter",
        "description": "Active adapter fixture.",
        "adapter_path": f"library/{module_names[0]}/adapters/active-adapter.md",
        "status": "active",
    }
    assert [item["name"] for item in module_one["adapters"]] == ["other-owner"]
    assert all(item["name"] != "android-only" for item in module_zero["adapters"])
    assert deploy_skills._validate_route_index(
        yaml.safe_load(
            (payload["payload_root"] / "_platform" / "routes" / "index.yaml").read_text(
                encoding="utf-8"
            )
        ),
        payload["payload_root"],
    )


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (lambda adapter: adapter.update(status="planned"), "planned route adapter"),
        (lambda adapter: adapter.update(adapter_path="library/module-00/adapters/../escape.md"), "must not be absolute or contain dot segments"),
        (lambda adapter: adapter.update(adapter_path="library/module-00/adapters/other.md"), "must be 'library/module-00/adapters/active-adapter.md'"),
        (lambda adapter: adapter.update(description=""), "description is invalid"),
    ],
)
def test_v4_route_rejects_invalid_nested_adapter_mapping(tmp_path, mutator, message):
    manifest, _ = _fixture_repo(tmp_path, adapter_fixture=True)
    payload = _build(manifest, tmp_path / "staging")
    index_path = payload["payload_root"] / "_platform" / "routes" / "index.yaml"
    index = yaml.safe_load(index_path.read_text(encoding="utf-8"))
    shard_path = payload["payload_root"] / "_platform" / "routes" / "wsl-python.yaml"
    shard = yaml.safe_load(shard_path.read_text(encoding="utf-8"))
    candidate = next(item for item in shard["skills"] if item["name"] == "module-00")
    mutator(candidate["adapters"][0])
    shard_path.write_text(yaml.safe_dump(shard, sort_keys=False), encoding="utf-8")

    with pytest.raises(deploy_skills.DeploymentError, match=message):
        deploy_skills._validate_route_index(index, payload["payload_root"])


def test_v4_route_rejects_duplicate_nested_adapter_names(tmp_path):
    manifest, _ = _fixture_repo(tmp_path, adapter_fixture=True)
    payload = _build(manifest, tmp_path / "staging")
    index_path = payload["payload_root"] / "_platform" / "routes" / "index.yaml"
    index = yaml.safe_load(index_path.read_text(encoding="utf-8"))
    shard_path = payload["payload_root"] / "_platform" / "routes" / "wsl-python.yaml"
    shard = yaml.safe_load(shard_path.read_text(encoding="utf-8"))
    candidate = next(item for item in shard["skills"] if item["name"] == "module-00")
    candidate["adapters"].append(dict(candidate["adapters"][0]))
    shard_path.write_text(yaml.safe_dump(shard, sort_keys=False), encoding="utf-8")

    with pytest.raises(deploy_skills.DeploymentError, match="duplicate name"):
        deploy_skills._validate_route_index(index, payload["payload_root"])


def test_v4_route_rejects_unknown_shard_fields(tmp_path):
    manifest, _ = _fixture_repo(tmp_path, adapter_fixture=True)
    payload = _build(manifest, tmp_path / "staging")
    index = yaml.safe_load(
        (payload["payload_root"] / "_platform" / "routes" / "index.yaml").read_text(
            encoding="utf-8"
        )
    )
    shard_path = payload["payload_root"] / "_platform" / "routes" / "wsl-python.yaml"
    shard = yaml.safe_load(shard_path.read_text(encoding="utf-8"))
    shard["unexpected"] = True
    shard_path.write_text(yaml.safe_dump(shard, sort_keys=False), encoding="utf-8")

    with pytest.raises(deploy_skills.DeploymentError, match="route shard fields"):
        deploy_skills._validate_route_index(index, payload["payload_root"])


def test_v4_route_rejects_canonical_adapter_for_wrong_scenario(tmp_path):
    manifest, _ = _fixture_repo(tmp_path, adapter_fixture=True)
    payload = _build(manifest, tmp_path / "staging")
    index = yaml.safe_load(
        (payload["payload_root"] / "_platform" / "routes" / "index.yaml").read_text(
            encoding="utf-8"
        )
    )
    shard_path = payload["payload_root"] / "_platform" / "routes" / "win-android.yaml"
    shard_path.write_text(
        yaml.safe_dump(
            {
                "scenario": "win-android",
                "skills": [
                    {
                        "name": "module-00",
                        "description": "module-00 route.",
                        "skill_path": "library/module-00/MODULE.md",
                        "status": "active",
                        "skill_path": "library/module-00/MODULE.md",
                        "status": "active",
                        "routing_priority": 0,
                        "routing_outcome": "terminal",
                        "adapters": [
                            {
                                "name": "active-adapter",
                                "description": "Active adapter fixture.",
                                "adapter_path": "library/module-00/adapters/active-adapter.md",
                                "status": "active",
                            }
                        ],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        deploy_skills.DeploymentError,
        match="frontmatter environments do not include scenario 'win-android'",
    ):
        deploy_skills._validate_route_index(index, payload["payload_root"])


def test_real_manifest_routes_runtime_ops_and_copies_only_active_adapters(tmp_path):
    payload = _build(deploy_skills.DEFAULT_MANIFEST, tmp_path / "staging")
    runtime_ops = payload["payload_root"] / "library" / "runtime-ops"
    index = yaml.safe_load(
        (payload["payload_root"] / "_platform" / "routes" / "index.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert index["global_routes"] == [
        {
            "name": "development-delegation",
            "routing_priority": 100,
            "routing_outcome": "continue",
            "selector": "Repository work explicitly requiring planning or re-planning, lacking a usable detailed current-phase plan, or requiring delegated implementation and validation under an existing contract.",
            "skill_path": "library/development-delegation/MODULE.md",
        }
    ]
    assert not (runtime_ops / "adapters" / "gpt-repo-local.md").exists()
    assert (runtime_ops / "adapters" / "vba-office.md").is_file()
    assert (runtime_ops / "adapters" / "android-gradle.md").is_file()
    for planned_name in ("sql-server.md", "wsl-python.md"):
        assert not (runtime_ops / "adapters" / planned_name).exists()

    for scenario in SCENARIOS:
        shard = yaml.safe_load(
            (payload["payload_root"] / "_platform" / "routes" / f"{scenario}.yaml").read_text(
                encoding="utf-8"
            )
        )
        names = [item["name"] for item in shard["skills"]]
        for item in shard["skills"]:
            assert item["skill_path"] == f"library/{item['name']}/MODULE.md"
            assert (payload["payload_root"] / item["skill_path"]).is_file()
        assert "development-delegation" not in names
        if scenario == "wsl-python":
            assert "runtime-ops" not in names
            assert names == ["research-investigation"]
            continue
        runtime_entry = next(
            item for item in shard["skills"] if item["name"] == "runtime-ops"
        )
        assert runtime_entry["name"] == "runtime-ops"
        assert runtime_entry["skill_path"] == "library/runtime-ops/MODULE.md"
        assert runtime_entry["status"] == "active"
        assert runtime_entry["description"]
        adapter_name, adapter_description = {
            "win-access-vba": ("vba-office", "Microsoft Office VBA runtime adapter."),
            "win-android": ("android-gradle", "Android and Gradle runtime adapter."),
        }[scenario]
        assert runtime_entry["adapters"] == [
            {
                "name": adapter_name,
                "description": adapter_description,
                "adapter_path": f"library/runtime-ops/adapters/{adapter_name}.md",
                "status": "active",
            }
        ]

    target_root = tmp_path / "skills"
    deploy_skills.apply_payload(target_root, payload)
    assert sorted(path.name for path in target_root.iterdir()) == ["global-skill-router"]


def test_p5_gradle_contract_and_source_independent_deployment(tmp_path):
    # Copy only managed artifacts: optional reference checkouts are absent.
    candidate_root = tmp_path / "candidate"
    candidate_skills = candidate_root / "development" / "skill"
    shutil.copytree(deploy_skills.DEFAULT_MANIFEST.parent, candidate_skills)
    manifest_path = candidate_skills / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    runtime = next(item for item in manifest["skills"] if item["name"] == "runtime-ops")
    kotlin = next(item for item in manifest["skills"] if item["name"] == "kotlin-tooling")
    adapter = next(item for item in manifest["adapters"] if item["name"] == "android-gradle")
    assert adapter["status"] == "active"
    assert "win-android" in runtime["scenarios"]
    assert kotlin == {
        "name": "kotlin-tooling",
        "path": "development/skill/kotlin-tooling",
        "status": "active",
        "deployment_role": "module",
        "routing_priority": 10,
        "routing_outcome": "continue",
        "routing_scope": "scenario",
        "scenarios": ["win-android"],
        "deps": [],
        "composed_of": [],
        "entrypoint": True,
        "version": "0.1.0",
        "description": "Kotlin-specific toolchain, project, and migration decision guidance.",
    }

    contract_path = candidate_root / adapter["path"]
    contract = contract_path.read_text(encoding="utf-8")
    frontmatter = yaml.safe_load(contract.split("---", 2)[1])
    assert frontmatter["adapter_schema_version"] == 1
    assert frontmatter["adapter"] == adapter["name"]
    assert frontmatter["environments"] == adapter["environments"] == ["win-android"]
    assert frontmatter["mutation_support"] == "bounded"
    assert frontmatter["verification_model_kind"] == "independent_checks"
    models = [
        yaml.safe_load(block)
        for block in re.findall(r"```yaml\n(.*?)\n```", contract, re.DOTALL)
    ]
    model = next(block["verification_model"] for block in models if "verification_model" in block)
    assert model["kind"] == frontmatter["verification_model_kind"]
    assert model["relations"] == []
    states = {state["id"]: state for state in model["states"]}
    assert set(states) == {
        "configuration_resolved", "requested_tasks_succeeded", "requested_tests_passed"
    }
    assert all(state["required_evidence"] and state["does_not_prove"] for state in states.values())
    assert any(item["id"] == "target_runtime_exercised" and item["reason"] for item in model["unsupported"])
    assert not (candidate_root / "development" / "skill-repos").exists()

    kotlin_contract_path = candidate_root / kotlin["path"] / "SKILL.md"
    assert kotlin_contract_path.is_file()
    kotlin_contract = kotlin_contract_path.read_text(encoding="utf-8")
    assert "pure Gradle" in kotlin_contract
    assert "runtime-ops" in kotlin_contract
    assert "`ROUTE_CONTINUE`" in kotlin_contract
    assert "only when the task" in kotlin_contract
    assert "Do not guess" in kotlin_contract

    payload = _build(manifest_path, tmp_path / "p5-stage")
    relative_adapter = "library/runtime-ops/adapters/android-gradle.md"
    routes = payload["payload_root"] / "_platform" / "routes"
    android = yaml.safe_load((routes / "win-android.yaml").read_text(encoding="utf-8"))
    runtime_route = next(item for item in android["skills"] if item["name"] == "runtime-ops")
    kotlin_route = next(item for item in android["skills"] if item["name"] == "kotlin-tooling")
    assert runtime_route["adapters"] == [{
        "name": "android-gradle",
        "description": adapter["description"],
        "adapter_path": relative_adapter,
        "status": "active",
    }]
    assert kotlin_route["name"] == "kotlin-tooling"
    assert kotlin_route["description"]
    assert kotlin_route["skill_path"] == "library/kotlin-tooling/MODULE.md"
    assert kotlin_route["status"] == "active"
    assert kotlin_route["adapters"] == []
    assert kotlin_route["routing_priority"] == 10
    assert kotlin_route["routing_outcome"] == "continue"
    assert runtime_route["routing_priority"] == 0
    assert runtime_route["routing_outcome"] == "terminal"
    assert [item["name"] for item in android["skills"]] == ["kotlin-tooling", "runtime-ops"]
    assert all(
        skill["name"] != "kotlin-tooling"
        for scenario in ("win-access-vba", "wsl-python")
        for skill in yaml.safe_load((routes / f"{scenario}.yaml").read_text(encoding="utf-8"))["skills"]
    )
    for scenario in ("win-access-vba", "wsl-python"):
        shard = yaml.safe_load((routes / f"{scenario}.yaml").read_text(encoding="utf-8"))
        assert all(
            mapped["name"] != "android-gradle"
            for skill in shard["skills"] for mapped in skill.get("adapters", [])
        )
    target = tmp_path / "p5-target"
    assert deploy_skills.apply_payload(target, payload)["action"] == "applied"
    assert deploy_skills.verify_target(target)["ok"]
    deployed = target / "global-skill-router" / relative_adapter
    assert deployed.read_bytes() == contract_path.read_bytes()
    assert not any("skill-repos" in path.parts for path in target.rglob("*"))


def test_route_index_rejects_invalid_global_skill_path(tmp_path):
    payload = _build(deploy_skills.DEFAULT_MANIFEST, tmp_path / "staging")
    index = yaml.safe_load(
        (payload["payload_root"] / "_platform" / "routes" / "index.yaml").read_text(
            encoding="utf-8"
        )
    )
    index["global_routes"][0]["skill_path"] = "../development-delegation/SKILL.md"
    with pytest.raises(deploy_skills.DeploymentError, match="global route skill path"):
        deploy_skills._validate_route_index(index, payload["payload_root"])


def test_legacy_v1_route_index_remains_verifiable_for_recovery(tmp_path):
    manifest, _ = _fixture_repo(tmp_path)
    payload = _build(manifest, tmp_path / "staging")
    index = yaml.safe_load(
        (payload["payload_root"] / "_platform" / "routes" / "index.yaml").read_text(
            encoding="utf-8"
        )
    )
    index["schema_version"] = 1
    index.pop("global_routes")
    assert deploy_skills._validate_route_index(index, payload["payload_root"])


def test_legacy_v2_route_index_remains_verifiable_for_recovery(tmp_path):
    manifest, _ = _fixture_repo(tmp_path)
    payload = _build(manifest, tmp_path / "staging")
    index = yaml.safe_load(
        (payload["payload_root"] / "_platform" / "routes" / "index.yaml").read_text(
            encoding="utf-8"
        )
    )
    index["schema_version"] = 2
    for scenario in index["scenarios"]:
        shard_path = payload["payload_root"] / "_platform" / "routes" / f"{scenario['name']}.yaml"
        shard = yaml.safe_load(shard_path.read_text(encoding="utf-8"))
        for candidate in shard["skills"]:
            candidate.pop("adapters", None)
        shard_path.write_text(yaml.safe_dump(shard, sort_keys=False), encoding="utf-8")
    assert deploy_skills._validate_route_index(index, payload["payload_root"])


def test_adapter_canonical_path_gate_blocks_deploy(tmp_path):
    manifest, _ = _fixture_repo(tmp_path, adapter_fixture=True)
    payload = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    payload["adapters"][0]["path"] = "development/skill/other/adapters/active-adapter.md"
    manifest.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(deploy_skills.DeploymentError, match="validation failed"):
        _build(manifest, tmp_path / "staging")


@pytest.mark.parametrize("victim", ["managed", "backup"])
def test_reparse_preflight_rejects_managed_and_backup_paths(tmp_path, monkeypatch, victim):
    target_root = tmp_path / "skills"
    target_root.mkdir()
    managed = target_root / "global-skill-router"
    managed.mkdir()
    backup = deploy_skills.backup_root(target_root)
    backup.mkdir()
    selected = managed if victim == "managed" else backup
    monkeypatch.setattr(
        deploy_skills,
        "_is_reparse_point",
        lambda path: Path(path) == selected,
    )

    with pytest.raises(deploy_skills.DeploymentError, match="symlink/junction/reparse"):
        deploy_skills._assert_target_root(target_root)


def test_reparse_helper_uses_windows_junction_hook(tmp_path, monkeypatch):
    junction = tmp_path / "junction"
    junction.mkdir()
    monkeypatch.setattr(
        Path,
        "is_junction",
        lambda path: Path(path) == junction,
        raising=False,
    )
    assert deploy_skills._is_reparse_point(junction)


def test_route_and_state_are_deterministic(tmp_path):
    manifest, _ = _fixture_repo(tmp_path)
    first = _build(manifest, tmp_path / "first")
    second = _build(manifest, tmp_path / "second")
    first_root = first["payload_root"]
    second_root = second["payload_root"]
    paths = sorted(path.relative_to(first_root) for path in first_root.rglob("*") if path.is_file())
    assert paths == sorted(path.relative_to(second_root) for path in second_root.rglob("*") if path.is_file())
    for relative in paths:
        assert (first_root / relative).read_bytes() == (second_root / relative).read_bytes()


def test_path_escape_is_rejected(tmp_path):
    manifest, _ = _fixture_repo(tmp_path)
    payload = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    payload["skills"][0]["path"] = "development/skill/../escape"
    manifest.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(deploy_skills.DeploymentError, match="validation failed"):
        _build(manifest, tmp_path / "staging")


def test_development_repositories_do_not_change_payload_or_routes(tmp_path):
    manifest, _ = _fixture_repo(tmp_path)
    baseline = _build(manifest, tmp_path / "baseline")
    baseline_root = baseline["payload_root"]
    expected_files = {
        path.relative_to(baseline_root): path.read_bytes()
        for path in baseline_root.rglob("*")
        if path.is_file()
        and path.relative_to(baseline_root).as_posix() != "_platform/deployment-state.json"
    }
    registry = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    repo_root = manifest.parents[2]
    for index, name in enumerate(("first-repo", "second-repo"), start=1):
        source_path = f"development/skill-repos/{name}"
        source_dir = repo_root / source_path
        source_dir.mkdir(parents=True)
        (source_dir / "SKILL.md").write_text("Not a managed Skill.\n", encoding="utf-8")
        registry["sources"].append({
            "id": name,
            "path": source_path,
            "kind": "development-repository",
            "required": False,
            "origin": f"https://example.com/{name}",
            "pinned_ref": "refs/tags/v1.0.0",
            "version": "1.0.0",
            "description": "Independent development source.",
        })
        manifest.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
        payload = _build(manifest, tmp_path / f"with-{index}-sources")
        payload_root = payload["payload_root"]
        actual_files = {
            path.relative_to(payload_root): path.read_bytes()
            for path in payload_root.rglob("*")
            if path.is_file()
            and path.relative_to(payload_root).as_posix() != "_platform/deployment-state.json"
        }
        assert actual_files == expected_files
        # Deployment state changes only in the manifest provenance hash.
        assert payload["state"]["manifest"]["sha256"] != baseline["state"]["manifest"]["sha256"]
        expected_state = {
            **baseline["state"],
            "manifest": {
                **baseline["state"]["manifest"],
                "sha256": payload["state"]["manifest"]["sha256"],
            },
        }
        assert payload["state"] == expected_state

    target_root = tmp_path / "skills"
    deploy_skills.apply_payload(target_root, payload)
    assert sorted(path.name for path in target_root.iterdir()) == ["global-skill-router"]


def test_growth_keeps_one_top_level_router_and_fixed_index(tmp_path):
    small_manifest, _ = _fixture_repo(tmp_path / "small", module_count=2)
    large_manifest, large_names = _fixture_repo(tmp_path / "large", module_count=55)
    small = _build(small_manifest, tmp_path / "small-stage")
    large = _build(large_manifest, tmp_path / "large-stage")
    target_root = tmp_path / "skills"
    deploy_skills.apply_payload(target_root, large)

    assert len(large["state"]["modules"]) == 55
    assert sorted(path.name for path in target_root.iterdir()) == ["global-skill-router"]
    assert len(list((target_root / "global-skill-router" / "library").iterdir())) == 55
    assert (small["payload_root"] / "_platform" / "routes" / "index.yaml").read_bytes() == (large["payload_root"] / "_platform" / "routes" / "index.yaml").read_bytes()
    assert (small["payload_root"] / "SKILL.md").read_bytes() == (large["payload_root"] / "SKILL.md").read_bytes()
    assert (small["payload_root"] / "agents" / "openai.yaml").read_bytes() == (large["payload_root"] / "agents" / "openai.yaml").read_bytes()
    assert large_names == [f"module-{index:02d}" for index in range(55)]


def test_growth_changes_only_matching_scenario_shard(tmp_path):
    small_manifest, _ = _fixture_repo(
        tmp_path / "small",
        module_count=2,
        module_scenarios=["win-access-vba", "win-android"],
    )
    large_manifest, _ = _fixture_repo(
        tmp_path / "large",
        module_count=55,
        module_scenarios=["win-access-vba", "win-android"] + ["wsl-python"] * 53,
    )
    small = _build(small_manifest, tmp_path / "small-stage")
    large = _build(large_manifest, tmp_path / "large-stage")
    small_routes = small["payload_root"] / "_platform" / "routes"
    large_routes = large["payload_root"] / "_platform" / "routes"

    assert (small_routes / "index.yaml").read_bytes() == (large_routes / "index.yaml").read_bytes()
    assert (small_routes / "win-access-vba.yaml").read_bytes() == (large_routes / "win-access-vba.yaml").read_bytes()
    assert (small_routes / "win-android.yaml").read_bytes() == (large_routes / "win-android.yaml").read_bytes()
    assert (small_routes / "wsl-python.yaml").read_bytes() != (large_routes / "wsl-python.yaml").read_bytes()


def test_cli_plan_is_read_only(tmp_path, capsys):
    manifest, _ = _fixture_repo(tmp_path)
    target_root = tmp_path / "skills"
    assert deploy_skills.main(["--manifest", str(manifest), "--target-root", str(target_root), "--dry-run"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["action"] == "plan"
    assert result["managed_scope"] == ["global-skill-router"]
    assert result["unmanaged_paths_untouched"] is True
    assert not target_root.exists()


def _routing_contract(payload):
    # Contract regression only: Markdown is interpreted by Codex, not by Python.
    return " ".join((payload["payload_root"] / "SKILL.md").read_text(encoding="utf-8").split())


def test_highest_priority_delegation_continues_to_available_child_contract(tmp_path):
    payload = _build(deploy_skills.DEFAULT_MANIFEST, tmp_path / "staging")
    routes = payload["payload_root"] / "_platform" / "routes"
    index = yaml.safe_load((routes / "index.yaml").read_text(encoding="utf-8"))
    android = yaml.safe_load((routes / "win-android.yaml").read_text(encoding="utf-8"))
    delegation = index["global_routes"][0]
    child = next(route for route in android["skills"] if route["name"] == "runtime-ops")

    assert delegation["name"] == "development-delegation"
    assert delegation["routing_priority"] > child["routing_priority"]
    assert delegation["routing_outcome"] == "continue"
    assert child["routing_outcome"] == "terminal"
    assert (payload["payload_root"] / child["skill_path"]).is_file()
    contract = _routing_contract(payload)
    assert "On `ROUTE_CONTINUE`, repeat step 2 while excluding `activated_modules`." in contract
    assert "When no unvisited global route matches, resolve exactly one scenario" in contract
    module = (payload["payload_root"] / delegation["skill_path"]).read_text(encoding="utf-8")
    assert "return `ROUTE_CONTINUE`" in module
    assert "routing middleware / an orchestrator" in module


def test_terminal_global_match_contract_stops_before_scenario_discovery(tmp_path):
    manifest, _ = _fixture_repo(tmp_path)
    registry = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    registry["skills"][0].update(
        routing_scope="global", routing_selector="Fully owned execution task.",
        scenarios=[], routing_priority=100, routing_outcome="terminal",
    )
    manifest.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    # Use the actual router contract, not the fixture's placeholder body.
    source_router = deploy_skills.DEFAULT_MANIFEST.parent / "global-skill-router" / "SKILL.md"
    shutil.copyfile(source_router, manifest.parent / "global-skill-router" / "SKILL.md")
    payload = _build(manifest, tmp_path / "staging")
    index = yaml.safe_load(
        (payload["payload_root"] / "_platform/routes/index.yaml").read_text(encoding="utf-8")
    )

    assert index["global_routes"][0]["routing_outcome"] == "terminal"
    assert "On `ROUTE_TERMINAL`, stop routing with zero scenario shards read." in _routing_contract(payload)


def test_multiple_orchestrator_contract_has_finite_unique_priority_order(tmp_path):
    manifest, names = _fixture_repo(tmp_path, module_count=4)
    registry = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    # Reverse lexical order by priority; leave one executable scenario child.
    for entry, priority in zip(registry["skills"][:3], (50, 100, 150)):
        entry.update(
            routing_scope="global", routing_selector="Matching orchestration layer.",
            scenarios=[], routing_priority=priority, routing_outcome="continue",
        )
    manifest.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    source_router = deploy_skills.DEFAULT_MANIFEST.parent / "global-skill-router" / "SKILL.md"
    shutil.copyfile(source_router, manifest.parent / "global-skill-router" / "SKILL.md")
    payload = _build(manifest, tmp_path / "staging")
    routes = payload["payload_root"] / "_platform/routes"
    index = yaml.safe_load((routes / "index.yaml").read_text(encoding="utf-8"))
    child_routes = yaml.safe_load((routes / "wsl-python.yaml").read_text(encoding="utf-8"))["skills"]

    assert [route["name"] for route in index["global_routes"]] == names[2::-1]
    assert all(route["routing_outcome"] == "continue" for route in index["global_routes"])
    assert [route["name"] for route in child_routes] == [names[3]]
    sequence = index["global_routes"] + child_routes
    assert len({route["name"] for route in sequence}) == len(sequence) == 4
    contract = _routing_contract(payload)
    assert "initialize each module at most once" in contract
    assert "Each continuing match consumes one unvisited route." in contract
    assert "Exhaustion ends discovery without revisiting earlier modules" in contract


@pytest.mark.parametrize("scope", ["global", "scenario"])
@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("routing_priority", True, "routing_priority must be an integer"),
        ("routing_priority", None, "routing_priority must be an integer"),
        ("routing_outcome", "stop", "routing_outcome must be continue or terminal"),
        ("routing_outcome", None, "routing_outcome must be continue or terminal"),
    ],
)
def test_v4_index_rejects_invalid_routing_controls(tmp_path, scope, field, value, message):
    payload = _build(deploy_skills.DEFAULT_MANIFEST, tmp_path / "staging")
    routes = payload["payload_root"] / "_platform/routes"
    index = yaml.safe_load((routes / "index.yaml").read_text(encoding="utf-8"))
    if scope == "global":
        index["global_routes"][0][field] = value
    else:
        shard_path = routes / "wsl-python.yaml"
        shard = yaml.safe_load(shard_path.read_text(encoding="utf-8"))
        shard["skills"][0][field] = value
        shard_path.write_text(yaml.safe_dump(shard, sort_keys=False), encoding="utf-8")
    with pytest.raises(deploy_skills.DeploymentError, match=message):
        deploy_skills._validate_route_index(index, payload["payload_root"])


def test_legacy_v3_route_index_remains_verifiable_for_recovery(tmp_path):
    payload = _build(deploy_skills.DEFAULT_MANIFEST, tmp_path / "staging")
    routes = payload["payload_root"] / "_platform/routes"
    index = yaml.safe_load((routes / "index.yaml").read_text(encoding="utf-8"))
    index["schema_version"] = 3
    for route in index["global_routes"]:
        route.pop("routing_priority")
        route.pop("routing_outcome")
    for scenario in index["scenarios"]:
        shard_path = payload["payload_root"] / scenario["shard"]
        shard = yaml.safe_load(shard_path.read_text(encoding="utf-8"))
        for route in shard["skills"]:
            route.pop("routing_priority")
            route.pop("routing_outcome")
        shard_path.write_text(yaml.safe_dump(shard, sort_keys=False), encoding="utf-8")
    assert deploy_skills._validate_route_index(index, payload["payload_root"])
