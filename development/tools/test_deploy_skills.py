"""Focused tests for the P4 routed deployment manager."""

from __future__ import annotations

import importlib.util
import json
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


def _write_adapter(root: Path, owner: str, name: str, *, status: str = "active") -> Path:
    adapter_dir = root / "development" / "skill" / owner / "adapters"
    adapter_dir.mkdir(parents=True, exist_ok=True)
    path = adapter_dir / f"{name}.md"
    path.write_text(
        "---\n"
        "adapter_schema_version: 1\n"
        f"adapter: {name}\n"
        "environments: [wsl-python]\n"
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
            {"schema_version": 3, "sources": [], "skills": skills, "adapters": adapters},
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
    assert "updated" in (target_root / "global-skill-router" / "library" / "module-00" / "SKILL.md").read_text(encoding="utf-8")
    assert legacy.read_bytes() == b"legacy bytes"


def test_failure_recovery_restores_previous_payload(tmp_path, monkeypatch):
    manifest, _ = _fixture_repo(tmp_path)
    target_root = tmp_path / "skills"
    legacy = target_root / "vba-skill" / "legacy.bin"
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"legacy bytes")
    first = _build(manifest, tmp_path / "first")
    deploy_skills.apply_payload(target_root, first)
    old_text = (target_root / "global-skill-router" / "library" / "module-00" / "SKILL.md").read_text(encoding="utf-8")
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
    assert (target_root / "global-skill-router" / "library" / "module-00" / "SKILL.md").read_text(encoding="utf-8") == old_text
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
    assert "second" in (target_root / "global-skill-router" / "library" / "module-00" / "SKILL.md").read_text(encoding="utf-8")

    result = deploy_skills.rollback_payload(target_root)

    assert result["action"] == "rollback"
    assert "second" not in (target_root / "global-skill-router" / "library" / "module-00" / "SKILL.md").read_text(encoding="utf-8")
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
    assert "second" in (target_root / "global-skill-router" / "library" / "module-00" / "SKILL.md").read_text(encoding="utf-8")
    assert original_verify(target_root)["ok"]
    assert (deploy_skills.backup_root(target_root) / "previous").is_dir()


def test_drift_is_reported_without_overwrite(tmp_path):
    manifest, _ = _fixture_repo(tmp_path)
    target_root = tmp_path / "skills"
    deploy_skills.apply_payload(target_root, _build(manifest, tmp_path / "staging"))
    installed = target_root / "global-skill-router" / "library" / "module-00" / "SKILL.md"
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


def test_real_manifest_routes_runtime_ops_and_copies_only_active_adapters(tmp_path):
    payload = _build(deploy_skills.DEFAULT_MANIFEST, tmp_path / "staging")
    runtime_ops = payload["payload_root"] / "library" / "runtime-ops"

    assert (runtime_ops / "adapters" / "gpt-repo-local.md").is_file()
    assert (runtime_ops / "adapters" / "vba-office.md").is_file()
    for planned_name in ("sql-server.md", "android-gradle.md", "wsl-python.md"):
        assert not (runtime_ops / "adapters" / planned_name).exists()

    for scenario in SCENARIOS:
        shard = yaml.safe_load(
            (payload["payload_root"] / "_platform" / "routes" / f"{scenario}.yaml").read_text(
                encoding="utf-8"
            )
        )
        runtime_entry = next(
            item for item in shard["skills"] if item["name"] == "runtime-ops"
        )
        assert runtime_entry["name"] == "runtime-ops"
        assert runtime_entry["skill_path"] == "library/runtime-ops/SKILL.md"
        assert runtime_entry["status"] == "active"
        assert runtime_entry["description"]

    target_root = tmp_path / "skills"
    deploy_skills.apply_payload(target_root, payload)
    assert sorted(path.name for path in target_root.iterdir()) == ["global-skill-router"]


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
