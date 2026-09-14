"""Tests for development/tools/validate_skills.py (plan 010 section 4)."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml

_SPEC = importlib.util.spec_from_file_location(
    "validate_skills_under_test",
    Path(__file__).with_name("validate_skills.py"),
)
validate_skills = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(validate_skills)


def _entry(name, path, status="planned", **overrides):
    entry = {
        "name": name,
        "path": path,
        "status": status,
        "scenarios": [],
        "deps": [],
        "composed_of": [],
        "entrypoint": False,
        "deployment_role": "module",
        "version": "1.0.0",
        "description": "placeholder description",
    }
    entry.update(overrides)
    return entry


def _source(source_id, path, required=False, **overrides):
    entry = {
        "id": source_id,
        "path": path,
        "kind": "local-reference",
        "required": required,
        "version": "1.0.0",
        "description": "placeholder source",
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


def _build_tree(tmp_path, entries, probe_dirs=(), create_external=True, sources=None):
    skill_dir = tmp_path / "development" / "skill"
    skill_dir.mkdir(parents=True, exist_ok=True)
    for probe in probe_dirs:
        (skill_dir / probe).mkdir(parents=True, exist_ok=True)
    skill_entries = []
    source_entries = list(sources or [])
    for entry in entries:
        if entry.get("status") == "external":
            source_entries.append(
                _source(
                    entry["name"],
                    entry["path"],
                    required=entry.get("required", False),
                )
            )
            if create_external:
                (tmp_path / entry["path"]).mkdir(parents=True, exist_ok=True)
        else:
            skill_entries.append(entry)
    if not any(
        isinstance(entry, dict) and entry.get("name") == "global-skill-router"
        for entry in skill_entries
    ):
        active_modules = [
            entry["name"]
            for entry in skill_entries
            if entry.get("status") == "active" and entry.get("name")
        ]
        router = _entry(
            "global-skill-router",
            "development/skill/global-skill-router",
            "active",
            deployment_role="router",
            scenarios=["win-access-vba", "win-android", "wsl-python"],
            composed_of=active_modules,
            entrypoint=True,
        )
        skill_entries.append(router)
        router_dir = tmp_path / router["path"]
        _write_skill_md(router_dir, name="global-skill-router")
        metadata_dir = router_dir / "agents"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        (metadata_dir / "openai.yaml").write_text(
            yaml.safe_dump(
                {
                    "interface": {
                        "display_name": "Global Skill Router",
                        "short_description": "Route managed modules.",
                        "default_prompt": "Load $global-skill-router.",
                    }
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
    manifest = skill_dir / "manifest.yaml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "schema_version": 3,
                "sources": source_entries,
                "skills": skill_entries,
                "adapters": [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return manifest


def _run(tmp_path, entries, probe_dirs=(), create_external=True, sources=None):
    manifest = _build_tree(
        tmp_path,
        entries,
        probe_dirs,
        create_external,
        sources=sources,
    )
    return validate_skills.validate(manifest)


def _codes(report):
    return [error["code"] for error in report["errors"]]


def _green_entries():
    return [
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
            scenarios=["win-access-vba", "win-android", "wsl-python"],
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
            scenarios=["win-access-vba", "win-android", "wsl-python"],
            version="0.1.0",
        ),
    ]
    report = _run(tmp_path, entries)
    assert report["ok"] is True
    assert report["errors"] == []


def test_planned_with_skill_md_checked(tmp_path):
    entries = [
        _entry(
            "early-skill",
            "development/skill/early-skill",
            "planned",
            scenarios=["win-access-vba", "win-android", "wsl-python"],
        )
    ]
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
    report = _run(
        tmp_path,
        [],
        create_external=False,
        sources=[_source("ghost-lib", "references/ghost-lib", required=True)],
    )
    assert "SOURCE_PATH_MISSING" in _codes(report)


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


def test_registered_source_under_skill_dir_is_not_reported_as_unregistered(tmp_path):
    manifest = _build_tree(tmp_path, _green_entries())
    source_dir = tmp_path / "development" / "skill" / "source-repo"
    source_dir.mkdir(parents=True)
    payload = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    payload["sources"] = [
        {
            "id": "source-repo-reference",
            "path": "development/skill/source-repo",
            "kind": "local-reference",
            "required": False,
            "version": "2026-09-14",
            "description": "Local source repository used to derive a managed skill.",
        }
    ]
    manifest.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    report = validate_skills.validate(manifest)
    assert not any(
        error["code"] == "UNREGISTERED_SKILL" and error["skill"] == "source-repo"
        for error in report["errors"]
    )


def test_duplicate_names_rejected(tmp_path):
    entries = [
        _entry("dupe", "development/skill/lib-a", "planned"),
        _entry("dupe", "development/skill/lib-b", "planned"),
    ]
    report = _run(tmp_path, entries)
    assert "DUPLICATE_NAME" in _codes(report)


def test_duplicate_source_ids_rejected(tmp_path):
    report = _run(
        tmp_path,
        [],
        sources=[
            _source("dupe", "references/lib-a"),
            _source("dupe", "references/lib-b"),
        ],
    )
    assert "DUPLICATE_SOURCE_ID" in _codes(report)


def test_unknown_composed_of_ref_rejected(tmp_path):
    entries = [
        _entry(
            "worker",
            "development/skill/worker",
            scenarios=["win-access-vba", "win-android", "wsl-python"],
            composed_of=["ghost"],
        )
    ]
    report = _run(tmp_path, entries)
    assert "COMPOSED_OF_UNKNOWN_REF" in _codes(report)


def test_invalid_scenario_value_rejected(tmp_path):
    entries = [
        _entry("worker", "development/skill/worker", scenarios=["wsl-bash"])
    ]
    report = _run(tmp_path, entries)
    assert "INVALID_SCENARIO" in _codes(report)


def test_schema_v3_required(tmp_path):
    manifest = _build_tree(tmp_path, _green_entries())
    payload = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    payload["schema_version"] = 2
    manifest.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    assert "SCHEMA_VERSION_UNSUPPORTED" in _codes(validate_skills.validate(manifest))


def test_deployment_role_gate(tmp_path):
    entries = [_entry("runtime-ops", "development/skill/runtime-ops", "planned", deployment_role="bad")]
    report = _run(tmp_path, entries)
    assert "DEPLOYMENT_ROLE_INVALID" in _codes(report)


def test_router_cardinality_gate(tmp_path):
    manifest = _build_tree(tmp_path, _green_entries())
    payload = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    payload["skills"] = [entry for entry in payload["skills"] if entry["name"] != "global-skill-router"]
    manifest.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    assert "ROUTER_CARDINALITY_INVALID" in _codes(validate_skills.validate(manifest))


def test_router_module_coverage_gate(tmp_path):
    entries = [
        _entry(
            "module-a",
            "development/skill/module-a",
            "active",
            scenarios=["wsl-python"],
            entrypoint=True,
        ),
        _entry(
            "global-skill-router",
            "development/skill/global-skill-router",
            "active",
            deployment_role="router",
            scenarios=["wsl-python"],
            entrypoint=True,
            composed_of=[],
        ),
    ]
    _write_skill_md(tmp_path / "development" / "skill" / "module-a", name="module-a")
    router_dir = tmp_path / "development" / "skill" / "global-skill-router"
    _write_skill_md(router_dir, name="global-skill-router")
    (router_dir / "agents").mkdir(parents=True, exist_ok=True)
    (router_dir / "agents" / "openai.yaml").write_text(
        "interface:\n  display_name: Router\n  short_description: Route modules.\n  default_prompt: Load $global-skill-router.\n",
        encoding="utf-8",
    )
    report = _run(tmp_path, entries)
    assert "ROUTER_MODULE_UNCOVERED" in _codes(report)


def test_non_entrypoint_module_reachability_gate(tmp_path):
    manifest = _build_tree(
        tmp_path,
        [_entry("module-a", "development/skill/module-a", "active", scenarios=["wsl-python"])],
    )
    payload = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    for entry in payload["skills"]:
        if entry["name"] == "global-skill-router":
            entry["composed_of"] = []
    manifest.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    assert "MODULE_UNREACHABLE" in _codes(validate_skills.validate(manifest))


def test_skill_path_containment_gate(tmp_path):
    manifest = _build_tree(tmp_path, _green_entries())
    payload = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    for entry in payload["skills"]:
        if entry["name"] == "runtime-ops":
            entry["path"] = "development/skill/../escape"
    manifest.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    assert "SKILL_PATH_INVALID" in _codes(validate_skills.validate(manifest))


def test_report_shape_and_exit_code(tmp_path, monkeypatch, capsys):
    _write_skill_md(tmp_path / "development" / "skill" / "runtime-ops", name="runtime-ops")
    manifest = _build_tree(tmp_path, _green_entries())
    monkeypatch.setattr(sys, "argv", ["validate_skills.py", "--manifest", str(manifest)])
    exit_code = validate_skills.main()
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert exit_code == 0
    assert set(report) == {
        "ok",
        "manifest",
        "skills_checked",
        "sources_checked",
        "adapters_checked",
        "routes",
        "errors",
    }
    assert report["ok"] is True
    assert report["skills_checked"] == 3
    assert report["errors"] == []

    broken = {
        "schema_version": 3,
        "sources": [],
        "skills": [
            _entry("dupe", "development/skill/lib-a"),
            _entry("dupe", "development/skill/lib-b"),
        ],
        "adapters": [],
    }
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


# --- Profile Contract gate (plan 020: mechanical profile ABI) -------------------------


def _valid_profile():
    return {
        "profile_schema_version": 1,
        "domain": "alpha-domain",
        "subject_type": "company",
        "investigation_dimensions": [
            {"id": "identity", "purpose": "Establish identity."},
            {"id": "activity", "purpose": "Establish activity."},
        ],
        "concept_groups": {"identity": ["company", "registry"]},
        "query_examples": ['"Name" registry'],
        "vocabulary_authority": None,
        "packet_extensions": {
            "relevance": {"placed_at": "profile_extensions.relevance", "fields": {}}
        },
        "pipeline_binding": {
            "mode": "canonical_candidates_when_supplied",
            "reference_stages": ["Acquisition", "Source", "Signal", "Fact", "Score"],
            "consumes": ["Source"],
            "produces": ["Fact-candidate"],
            "never_promotes_to": ["Score"],
        },
        "project_bindings": {
            "vocab": {
                "owner": "consuming_project",
                "reference": "config/search_terms.yaml",
                "required": False,
                "when_unavailable": "use_profile_vocabulary_only",
            }
        },
        "display": {"display_name": "Alpha"},
    }


def _profile_codes(tmp_path, payload, raw=None, slug="alpha-domain"):
    profile_dir = tmp_path / "profiles"
    profile_dir.mkdir(parents=True, exist_ok=True)
    path = profile_dir / f"{slug}.yaml"
    if raw is not None:
        path.write_text(raw, encoding="utf-8")
    else:
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return [error["code"] for error in validate_skills.profile_errors(path)]


def test_profile_gate_accepts_valid_profile(tmp_path):
    assert _profile_codes(tmp_path, _valid_profile()) == []


def test_profile_gate_accepts_resolved_vocabulary_authority(tmp_path):
    payload = _valid_profile()
    payload["vocabulary_authority"] = "vocab"
    assert _profile_codes(tmp_path, payload) == []


def test_profile_gate_rejects_duplicate_dimension_ids(tmp_path):
    payload = _valid_profile()
    payload["investigation_dimensions"][1]["id"] = "identity"
    assert "PROFILE_DIMENSION_DUPLICATE_ID" in _profile_codes(tmp_path, payload)


@pytest.mark.parametrize(
    "bad_id",
    [
        "release_status",
        "ReleaseStatus",
        "release status",
    ],
)
def test_profile_gate_rejects_non_kebab_dimension_id(tmp_path, bad_id):
    payload = _valid_profile()
    payload["investigation_dimensions"][0]["id"] = bad_id
    assert "PROFILE_DIMENSION_ID_FORMAT" in _profile_codes(tmp_path, payload)


def test_profile_gate_rejects_binding_missing_owner(tmp_path):
    payload = _valid_profile()
    del payload["project_bindings"]["vocab"]["owner"]
    assert "PROFILE_BINDING_INCOMPLETE" in _profile_codes(tmp_path, payload)


def test_profile_gate_rejects_non_boolean_required(tmp_path):
    payload = _valid_profile()
    payload["project_bindings"]["vocab"]["required"] = "false"
    assert "PROFILE_BINDING_REQUIRED_TYPE" in _profile_codes(tmp_path, payload)


def test_profile_gate_rejects_unresolved_vocabulary_authority(tmp_path):
    payload = _valid_profile()
    payload["vocabulary_authority"] = "ghost-binding"
    assert "PROFILE_VOCAB_AUTHORITY_UNRESOLVED" in _profile_codes(tmp_path, payload)


def test_profile_gate_rejects_unsupported_schema_version(tmp_path):
    payload = _valid_profile()
    payload["profile_schema_version"] = 2
    assert "PROFILE_SCHEMA_VERSION_UNSUPPORTED" in _profile_codes(tmp_path, payload)


def test_profile_gate_rejects_missing_schema_version(tmp_path):
    payload = _valid_profile()
    del payload["profile_schema_version"]
    assert "PROFILE_SCHEMA_VERSION_UNSUPPORTED" in _profile_codes(tmp_path, payload)


def test_profile_gate_rejects_bad_extension_placement(tmp_path):
    payload = _valid_profile()
    payload["packet_extensions"]["relevance"]["placed_at"] = "findings.extra"
    assert "PROFILE_EXTENSION_PLACEMENT" in _profile_codes(tmp_path, payload)


def test_profile_gate_rejects_relevance_extension_misplaced(tmp_path):
    payload = _valid_profile()
    payload["packet_extensions"]["relevance"]["placed_at"] = "profile_extensions.other"
    assert "PROFILE_EXTENSION_PLACEMENT" in _profile_codes(tmp_path, payload)


def test_profile_gate_rejects_bad_pipeline_binding(tmp_path):
    payload = _valid_profile()
    del payload["pipeline_binding"]["produces"]
    assert "PROFILE_PIPELINE_BINDING_INVALID" in _profile_codes(tmp_path, payload)


def test_profile_gate_rejects_unknown_top_level_field(tmp_path):
    payload = _valid_profile()
    payload["scoring_policy"] = {"weight": 1}
    assert "PROFILE_UNKNOWN_FIELD" in _profile_codes(tmp_path, payload)


def test_profile_gate_rejects_domain_slug_mismatch(tmp_path):
    payload = _valid_profile()
    payload["domain"] = "other-domain"
    assert "PROFILE_DOMAIN_MISMATCH" in _profile_codes(tmp_path, payload)


def test_profile_gate_rejects_non_kebab_domain(tmp_path):
    payload = _valid_profile()
    payload["domain"] = "Alpha Domain"
    assert "PROFILE_DOMAIN_FORMAT" in _profile_codes(tmp_path, payload)


def test_profile_gate_rejects_empty_dimensions(tmp_path):
    payload = _valid_profile()
    payload["investigation_dimensions"] = []
    assert "PROFILE_DIMENSIONS_INVALID" in _profile_codes(tmp_path, payload)


def test_profile_gate_rejects_dimension_without_purpose(tmp_path):
    payload = _valid_profile()
    del payload["investigation_dimensions"][0]["purpose"]
    assert "PROFILE_DIMENSION_INCOMPLETE" in _profile_codes(tmp_path, payload)


def test_profile_gate_rejects_bad_concept_groups_type(tmp_path):
    payload = _valid_profile()
    payload["concept_groups"] = ["company"]
    assert "PROFILE_CONCEPT_GROUPS_TYPE" in _profile_codes(tmp_path, payload)


def test_profile_gate_rejects_bad_query_examples_type(tmp_path):
    payload = _valid_profile()
    payload["query_examples"] = {"identity": "company"}
    assert "PROFILE_QUERY_EXAMPLES_TYPE" in _profile_codes(tmp_path, payload)


def test_profile_gate_rejects_malformed_yaml(tmp_path):
    assert "PROFILE_PARSE_ERROR" in _profile_codes(
        tmp_path, None, raw="profile_schema_version: [unclosed\n"
    )


def test_profile_gate_rejects_empty_subject_type(tmp_path):
    payload = _valid_profile()
    payload["subject_type"] = ""
    assert "PROFILE_SUBJECT_TYPE_INVALID" in _profile_codes(tmp_path, payload)


def test_profile_gate_rejects_bad_guidance_type(tmp_path):
    payload = _valid_profile()
    payload["profile_guidance"] = ["language_policy"]
    assert "PROFILE_GUIDANCE_TYPE" in _profile_codes(tmp_path, payload)


def test_profile_gate_rejects_bad_display_type(tmp_path):
    payload = _valid_profile()
    payload["display"] = ["alpha"]
    assert "PROFILE_DISPLAY_TYPE" in _profile_codes(tmp_path, payload)


def _profile_manifest_tree(tmp_path, payload, status="active"):
    skill_dir = tmp_path / "development" / "skill" / "research-investigation"
    _write_skill_md(skill_dir, name="research-investigation")
    profile_dir = skill_dir / "profiles"
    profile_dir.mkdir(parents=True, exist_ok=True)
    (profile_dir / "alpha-domain.yaml").write_text(
        yaml.safe_dump(payload, sort_keys=False), encoding="utf-8"
    )
    entries = [
        _entry(
            "research-investigation",
            "development/skill/research-investigation",
            status,
            scenarios=["win-access-vba", "win-android", "wsl-python"],
        ),
    ]
    return _run(tmp_path, entries)


def test_active_entry_profile_gate_wired(tmp_path):
    payload = _valid_profile()
    payload["scoring_policy"] = {"weight": 1}
    report = _profile_manifest_tree(tmp_path, payload, "active")
    assert any(
        error["code"] == "PROFILE_UNKNOWN_FIELD"
        and error["skill"] == "research-investigation"
        and error["message"].startswith("profiles/alpha-domain.yaml:")
        for error in report["errors"]
    )


def test_planned_entry_profiles_also_gated(tmp_path):
    payload = _valid_profile()
    payload["scoring_policy"] = {"weight": 1}
    report = _profile_manifest_tree(tmp_path, payload, "planned")
    assert "PROFILE_UNKNOWN_FIELD" in _codes(report)


def test_external_entry_profiles_not_gated(tmp_path):
    payload = _valid_profile()
    payload["scoring_policy"] = {"weight": 1}
    external_dir = tmp_path / "references" / "research-investigation"
    (external_dir / "profiles").mkdir(parents=True, exist_ok=True)
    (external_dir / "profiles" / "alpha-domain.yaml").write_text(
        yaml.safe_dump(payload, sort_keys=False), encoding="utf-8"
    )
    _write_skill_md(tmp_path / "development" / "skill" / "base", name="base")
    report = _run(
        tmp_path,
        [
            _entry("research-investigation", "references/research-investigation", "external"),
            _entry(
                "base",
                "development/skill/base",
                "active",
                scenarios=["win-access-vba", "win-android", "wsl-python"],
            ),
        ],
    )
    assert report["ok"] is True


def test_non_research_skill_with_profiles_not_gated(tmp_path):
    """Only research-investigation entries are held to the Research Profile Contract."""
    skill_dir = tmp_path / "development" / "skill" / "other-active"
    _write_skill_md(skill_dir, name="other-active")
    profile_dir = skill_dir / "profiles"
    profile_dir.mkdir(parents=True, exist_ok=True)
    (profile_dir / "foo.yaml").write_text(
        "scoring_policy:\n  weight: 1\n", encoding="utf-8"
    )
    entries = [
        _entry("spine-lib", "references/spine-lib", "external"),
        _entry(
            "other-active",
            "development/skill/other-active",
            "active",
            scenarios=["win-access-vba", "win-android", "wsl-python"],
        ),
    ]
    report = _run(tmp_path, entries)
    assert report["ok"] is True
    assert not any(error["code"].startswith("PROFILE_") for error in report["errors"])


def test_repo_manifest_passes_profile_gate():
    report = validate_skills.validate(validate_skills.DEFAULT_MANIFEST)
    assert report["errors"] == []
    assert report["ok"] is True
