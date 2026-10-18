#!/usr/bin/env python3
"""Executable checks for the dynamic-delegation *instruction* contract.

The small evaluators below interpret its declarative tables in tests only. They
are neither a host scheduler nor proof that an LLM/host enforces those tables.
Deployment checks exercise the real payload builder in a disposable directory.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1] / "skill" / "development-delegation"
SPEC = importlib.util.spec_from_file_location(
    "dynamic_delegation_deploy", Path(__file__).with_name("deploy_skills.py")
)
deploy = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(deploy)


def _load(name):
    return yaml.safe_load((ROOT / "routing" / name).read_text(encoding="utf-8"))


def _check_local_links(root):
    """Resolve actual links, including private deployed MODULE.md entrypoints."""
    checked = 0
    for document in root.rglob("*.md"):
        for target in re.findall(r"\[[^\]]*\]\(([^\s)]+)\)", document.read_text(encoding="utf-8")):
            url = urlsplit(target)
            if url.scheme or url.netloc or not url.path:
                continue
            path = (document.parent / unquote(url.path)).resolve()
            assert path.is_relative_to(root.resolve()), (document, target)
            assert path.is_file(), (document, target)
            checked += 1
    assert checked > 10, "Expected navigable, on-demand role and workflow modules"


def test_source_links_are_self_contained():
    _check_local_links(ROOT)


def test_deployed_dynamic_contract_is_complete_and_private(tmp_path):
    payload = deploy.build_payload(deploy.DEFAULT_MANIFEST, tmp_path / "staging")
    deployed = payload["payload_root"] / "library" / ROOT.name
    assert (deployed / "MODULE.md").read_bytes() == (ROOT / "SKILL.md").read_bytes()
    assert not list(deployed.rglob("SKILL.md"))
    assert not (deployed / "agents" / "openai.yaml").exists()
    for directory in ("routing", "roles", "loops", "modules", "references"):
        sources = list((ROOT / directory).rglob("*"))
        assert sources, directory
        for source in sources:
            if source.is_file():
                assert (deployed / source.relative_to(ROOT)).read_bytes() == source.read_bytes()
    _check_local_links(deployed)
    result = deploy.apply_payload(tmp_path / "installed", payload)
    assert result["ok"]
    assert deploy.verify_target(tmp_path / "installed")["ok"]


@pytest.fixture
def policy():
    return _load("task-policy.yaml")


@pytest.fixture
def capabilities():
    return _load("capabilities.yaml")


def _classify(policy, *, unresolved=False, planning=False, complex_dag=False,
              high_risk=False, bounded=True, explicit=None):
    """Test-only interpretation of eligibility predicates and documented precedence."""
    predicates = {
        "unresolved_scope_or_solution": unresolved,
        "explicit_plan_or_complex_dependencies_or_high_risk": planning or complex_dag or high_risk,
        "bounded_known_low_risk": bounded and not unresolved and not high_risk,
    }
    if explicit:
        if explicit not in policy["modes"] or not predicates[policy["modes"][explicit]["eligibility"]]:
            return "BLOCKED"
        return explicit
    for predicate in policy["selection"]["precedence"]:
        if predicate == "explicit_valid_choice":
            continue
        if predicates[predicate]:
            return policy["selection"][predicate]
    return policy["selection"]["otherwise"].upper()


def _review_required(policy, review_policy, *, supervision, high_risk=False,
                     requested=False, material_risk=False, uncertain_evidence=False):
    assert supervision in policy["supervision"]
    if high_risk and policy["review"]["mandatory_high_risk"]:
        return True
    interpretation = {
        "explicit_request_or_mandatory_override": requested,
        "material_risk_or_uncertain_evidence_or_mandatory_override": requested or material_risk or uncertain_evidence,
        "every_plan_and_delivery_boundary": True,
    }
    return interpretation[policy["review"]["policies"][review_policy]]


def _budget_allows(policy, counters, *actions):
    return all(counters.get(name, 0) < policy["budgets"][name] for name in actions)


def _identity(capabilities, selected, available, authorized_default=None):
    rules = capabilities["identity_selection"]
    if selected:
        if selected in available:
            return selected
        if rules["preserve_explicit_choices"] and not rules["silent_model_or_quota_substitution"]:
            return "BLOCKED"
    if rules["generic_host_agent_allowed_when_authorized"] and authorized_default in available:
        return authorized_default
    return "BLOCKED"


@pytest.mark.parametrize("facts, expected", [
    ({}, "direct"),
    ({"planning": True}, "planned"),
    ({"complex_dag": True}, "planned"),
    ({"high_risk": True}, "planned"),
    ({"unresolved": True}, "exploratory"),
    ({"unresolved": True, "high_risk": True}, "exploratory"),
    ({"unresolved": True, "planning": True}, "exploratory"),
    ({"bounded": False}, "BLOCKED"),
    ({"explicit": "direct", "high_risk": True}, "BLOCKED"),
    ({"explicit": "unknown"}, "BLOCKED"),
    ({"explicit": "planned", "planning": True}, "planned"),
])
def test_dynamic_classification_contract(policy, facts, expected):
    assert _classify(policy, **facts) == expected


def test_no_master_plan_or_legacy_ceremony_for_dynamic_direct(policy):
    assert policy["defaults"]["compatibility"] == "dynamic"
    assert policy["defaults"]["mode"] == "auto"
    assert not policy["modes"]["direct"]["master_plan_required"]
    assert not policy["compatibility"]["dynamic"]["explicit_selection_required"]
    assert policy["compatibility"]["legacy"]["explicit_selection_required"]
    assert policy["supervision"]["interactive"]["missing_authority"] == "ask_and_pause_affected_work"
    assert policy["supervision"]["unattended"]["missing_authority"] == "block_and_report"


@pytest.mark.parametrize("supervision", ["interactive", "unattended"])
@pytest.mark.parametrize("review_policy", ["on_demand", "risk_based", "always"])
def test_review_and_human_availability_are_independent(policy, supervision, review_policy):
    assert _review_required(policy, review_policy, supervision=supervision) == (review_policy == "always")
    assert _review_required(policy, review_policy, supervision=supervision, high_risk=True)
    assert _review_required(policy, review_policy, supervision=supervision, requested=True)


@pytest.mark.parametrize("signal", ["material_risk", "uncertain_evidence"])
def test_risk_based_review_uses_evidence_not_human_presence(policy, signal):
    assert _review_required(policy, "risk_based", supervision="interactive", **{signal: True})
    assert not _review_required(policy, "on_demand", supervision="unattended", **{signal: True})


def test_mandatory_high_risk_categories_cannot_disappear(policy):
    assert set(policy["review"]["high_risk_triggers"]) >= {
        "security_or_permissions", "destructive_or_irreversible_changes",
        "migrations_or_data_loss", "external_or_production_effects",
        "consequential_api_or_compatibility_changes",
    }
    assert policy["review"]["mandatory_high_risk"] is True


def test_exploration_needs_separate_bounded_experiment_authority(policy):
    exploratory = policy["modes"]["exploratory"]
    assert exploratory["read_only_by_default"] is True
    assert exploratory["experiments_require_explicit_bounded_authority"] is True
    assert not _budget_allows(policy, {}, "max_experiments")
    assert _budget_allows(policy, {}, "max_exploration_passes", "max_total_assignments")


def test_every_budget_has_a_finite_boundary_and_never_auto_expands(policy):
    budgets = policy["budgets"]
    assert budgets["exhaustion"] == "blocked"
    assert budgets["automatic_expansion"] is False
    for name, limit in budgets.items():
        if not name.startswith("max_"):
            continue
        assert type(limit) is int and limit >= 0
        if limit:
            assert _budget_allows(policy, {name: limit - 1}, name)
        assert not _budget_allows(policy, {name: limit}, name)
        assert not _budget_allows(policy, {name: limit + 1}, name)
    # A free retry-specific counter cannot override the total assignment ceiling.
    assert not _budget_allows(policy, {"max_total_assignments": budgets["max_total_assignments"]},
                              "max_total_assignments", "max_implementation_retries_per_unit")


@pytest.mark.parametrize("selected, available, default, expected", [
    ("chosen", {"chosen", "generic"}, "generic", "chosen"),
    ("chosen", {"generic"}, "generic", "BLOCKED"),
    (None, {"generic"}, "generic", "generic"),
    (None, {"generic"}, None, "BLOCKED"),
    (None, set(), "generic", "BLOCKED"),
])
def test_exact_identity_or_authorized_generic_only(capabilities, selected, available, default, expected):
    assert _identity(capabilities, selected, available, default) == expected


def test_roles_and_capabilities_have_one_owner_and_real_local_modules(policy, capabilities):
    assert policy["schema_version"] == capabilities["schema_version"] == 1
    assert policy["kind"] == "declarative-supervisor-policy"
    assert capabilities["kind"] == "declarative-role-capabilities"
    assert set(policy["roles"]) == set(capabilities["roles"]) == {
        "scout", "planner", "implementer", "tester", "reviewer", "specialist"
    }
    assert len(set(policy["roles"].values())) == len(policy["roles"])
    for role, module in policy["roles"].items():
        spec = capabilities["roles"][role]
        assert spec["module"] == module
        path = (ROOT / module).resolve()
        assert path.is_relative_to(ROOT.resolve()) and path.is_file()
        assert len(spec["required"]) == len(set(spec["required"]))
        assert spec["required"]
    for role in ("scout", "planner", "reviewer"):
        assert capabilities["roles"][role]["mutation"] == "forbidden"
        assert "write_owned_scope" not in capabilities["roles"][role]["required"]
    assert capabilities["roles"]["reviewer"]["independent_context_required"] is True
    assert capabilities["roles"]["implementer"]["mutation"] == "bounded_authority_only"


def test_declarative_paths_are_self_contained_and_knowledge_not_duplicated(policy, capabilities):
    def paths(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"contract", "module"}:
                    yield item
                else:
                    yield from paths(item)
        elif isinstance(value, list):
            for item in value:
                yield from paths(item)
    for relative in [*paths(policy), *paths(capabilities)]:
        resolved = (ROOT / relative).resolve()
        assert resolved.is_relative_to(ROOT.resolve()) and resolved.is_file(), relative
    # There is one table of each kind, never a conflicting per-role copy.
    for filename, kind in [("task-policy.yaml", "declarative-supervisor-policy"),
                           ("capabilities.yaml", "declarative-role-capabilities")]:
        owners = []
        for candidate in ROOT.rglob("*.yaml"):
            data = yaml.safe_load(candidate.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("kind") == kind:
                owners.append(candidate)
        assert owners == [ROOT / "routing" / filename]


def _ready_batch(policy, units, *, accepted=(), failed=(), used=0):
    """Test-only DAG model; intentionally never dispatches or writes a workspace."""
    gates = policy["parallelism"]
    transitions = policy["transitions"]
    by_id = {unit["id"]: unit for unit in units}
    if len(by_id) != len(units):
        return "blocked", []
    if any(dep not in by_id for unit in units for dep in unit["deps"]):
        return transitions["missing_dependency"], []
    visiting, visited = set(), set()

    def cycle(identity):
        if identity in visiting:
            return True
        if identity in visited:
            return False
        visiting.add(identity)
        if any(cycle(dep) for dep in by_id[identity]["deps"]):
            return True
        visiting.remove(identity)
        visited.add(identity)
        return False

    if gates["acyclic_dependencies_required"] and any(cycle(identity) for identity in by_id):
        return transitions["dependency_cycle"], []
    available = policy["budgets"]["max_total_assignments"] - used
    limit = min(available, policy["budgets"]["max_concurrent_assignments"])
    if limit <= 0:
        return transitions["zero_remaining_budget"], []
    chosen = []
    for unit in sorted(units, key=lambda item: item["id"]):
        if unit["id"] in set(accepted) | set(failed):
            continue
        if gates["successful_dependencies_required"] and not set(unit["deps"]) <= set(accepted):
            continue
        conflict = False
        for other in chosen:
            if gates["mutable_work_requires_isolation"] and (unit["writes"] or other["writes"]):
                conflict |= not unit["workspace"] or not other["workspace"] or unit["workspace"] == other["workspace"]
            if gates["disjoint_ownership_required"]:
                conflict |= any(a == b or a.startswith(b + "/") or b.startswith(a + "/")
                                for a in unit["writes"] for b in other["writes"])
            if gates["shared_resource_conflicts_block"]:
                conflict |= bool(set(unit["resources"]) & set(other["resources"]))
        if not conflict:
            chosen.append(unit)
        if len(chosen) == limit:
            break
    return "ready", [unit["id"] for unit in chosen]


def _unit(identity, *, deps=(), writes=(), resources=(), workspace=None):
    return {"id": identity, "deps": list(deps), "writes": list(writes),
            "resources": list(resources), "workspace": workspace}


def test_dag_ready_selection_is_topological_stable_and_bounded(policy):
    units = [_unit("join", deps=["a", "b"]), _unit("b"), _unit("a")]
    assert _ready_batch(policy, units) == ("ready", ["a", "b"])
    assert _ready_batch(policy, units, accepted=["a"]) == ("ready", ["b"])
    assert _ready_batch(policy, units, accepted=["a", "b"]) == ("ready", ["join"])
    limit = policy["budgets"]["max_total_assignments"]
    assert _ready_batch(policy, units, used=limit - 1) == ("ready", ["a"])
    assert _ready_batch(policy, units, used=limit) == ("blocked", [])


@pytest.mark.parametrize("units", [
    [_unit("a", deps=["a"])],
    [_unit("a", deps=["b"]), _unit("b", deps=["a"])],
    [_unit("a", deps=["missing"])],
    [_unit("a"), _unit("a")],
])
def test_invalid_dag_never_dispatches(policy, units):
    assert _ready_batch(policy, units) == ("blocked", [])


def test_failed_prerequisite_blocks_dependants_not_independent_branch(policy):
    units = [_unit("failed"), _unit("dependent", deps=["failed"]), _unit("independent")]
    assert policy["transitions"]["failed_dependency"] == "block_dependants"
    assert _ready_batch(policy, units, failed=["failed"]) == ("ready", ["independent"])


@pytest.mark.parametrize("left,right,parallel", [
    (_unit("a"), _unit("b"), True),
    (_unit("a", writes=["src/a"], workspace="one"),
     _unit("b", writes=["src/b"], workspace="two"), True),
    (_unit("a", writes=["src/a"]), _unit("b", writes=["src/b"]), False),
    (_unit("a", writes=["src/a"], workspace="same"),
     _unit("b", writes=["src/b"], workspace="same"), False),
    (_unit("a", writes=["src"], workspace="one"),
     _unit("b", writes=["src/nested/file"], workspace="two"), False),
    (_unit("a", writes=["src/a"], workspace="one", resources=["database"]),
     _unit("b", writes=["src/b"], workspace="two", resources=["database"]), False),
    (_unit("a", writes=["src/a"], workspace="one", resources=["build-cache"]),
     _unit("b", writes=["src/b"], workspace="two", resources=["build-cache"]), False),
])
def test_parallelism_checks_workspace_ownership_and_hidden_resources(policy, left, right, parallel):
    assert _ready_batch(policy, [right, left]) == ("ready", ["a", "b"] if parallel else ["a"])


def _accept(policy, observed, current, integration_pass):
    if policy["parallelism"]["stale_evidence_blocks_acceptance"] and observed != current:
        return policy["transitions"]["stale_evidence"]
    if policy["parallelism"]["integration_validation_required"] and not integration_pass:
        return policy["transitions"]["integration_failure"]
    return "accepted"


@pytest.mark.parametrize("changed", ["revision", "dirty_files", "environment", "configuration", "criteria"])
def test_acceptance_is_bound_to_current_evidence_not_stale_pass(policy, changed):
    observed = dict.fromkeys(["revision", "dirty_files", "environment", "configuration", "criteria"], "v1")
    assert _accept(policy, observed, dict(observed), True) == "accepted"
    current = dict(observed, **{changed: "v2"})
    assert _accept(policy, observed, current, True) == "reverify"
    assert _accept(policy, observed, observed, False) == "invalidate_affected_acceptance"


def test_required_scheduler_gates_and_transitions_are_not_optional(policy):
    for gate, required in policy["parallelism"].items():
        if gate != "contract":
            assert required is True, gate
    assert policy["transitions"]["implicit_identity_fallback"] == "forbidden"
    assert policy["transitions"]["missing_authority"] == "blocked"
    assert policy["transitions"]["unavailable_selected_identity"] == "blocked"
    assert policy["transitions"]["parallel_without_isolation"] == "serialize"


def test_specialties_are_on_demand_bounded_contexts_with_owned_paths(capabilities):
    specialties = capabilities["specialties"]
    assert set(specialties) == {
        "architect", "debugger", "integrator", "security_auditor",
        "performance", "migration", "documentation",
    }
    for name, specialty in specialties.items():
        module = (ROOT / specialty["module"]).resolve()
        assert module.is_relative_to(ROOT.resolve()) and module.is_file(), name
        assert specialty["select_when"]
        assert specialty["limits"]
        assert specialty["evidence"]
        assert len(specialty["evidence"]) == len(set(specialty["evidence"]))
    assert specialties["integrator"]["module"] == "modules/integration.md"
    assert "combined_tree_validation" in specialties["integrator"]["evidence"]
    assert "rollback" in specialties["migration"]["evidence"]
    # Specialists reuse bounded role behavior rather than introducing registrations
    # or duplicating the complete host/permission authority per specialization.
    assert "integrator" not in capabilities["roles"]
    assert specialties["security_auditor"]["limits"] == "read_only_no_exploitation_or_permission_changes"


def test_incremental_dependency_acceptance_does_not_require_unfinished_phase(policy):
    units = [_unit("A"), _unit("B", deps=["A"])]
    acceptance = policy["acceptance"]
    assert acceptance["unit_requires_phase_exit"] is False
    assert acceptance["phase_requires_all_units"] is True
    assert acceptance["unit_checks_must_not_require_unfinished_successors"] is True
    accepted = []
    phase_exit = False
    assert _ready_batch(policy, units, accepted=accepted) == ("ready", ["A"])
    # A passes its integrated unit criteria while B (and phase exit) is pending.
    unit_pass = _accept(policy, {"tree": "A"}, {"tree": "A"}, True) == "accepted"
    if unit_pass and (phase_exit or not acceptance["unit_requires_phase_exit"]):
        accepted.append("A")
    assert accepted == ["A"]
    assert _ready_batch(policy, units, accepted=accepted) == ("ready", ["B"])
    assert not (phase_exit and (not acceptance["phase_requires_all_units"] or len(accepted) == len(units)))
    if _accept(policy, {"tree": "AB"}, {"tree": "AB"}, True) == "accepted":
        accepted.append("B")
    assert _ready_batch(policy, units, accepted=accepted) == ("ready", [])
    # Completing units still does not assert that overall exit criteria passed.
    assert not phase_exit
    phase_exit = True
    assert phase_exit and (not acceptance["phase_requires_all_units"] or len(accepted) == len(units))
