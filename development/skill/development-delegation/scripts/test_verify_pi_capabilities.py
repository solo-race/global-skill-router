"""Tests for Pi role capability injection verification."""

import importlib.util
import json
import shutil
from pathlib import Path

import yaml

SPEC = importlib.util.spec_from_file_location(
    "verify_pi_capabilities", Path(__file__).with_name("verify_pi_capabilities.py")
)
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)

ROOT = Path(__file__).resolve().parents[1]
BINDINGS = ROOT / "routing" / "pi-bindings.yaml"
PROFILES = ROOT / "agents" / "pi"


def _catalog():
    return {
        "servers": [
            {
                "name": "codebase-memory-mcp",
                "enabled": True,
                "state": "connected",
                "tools": [
                    "search_graph", "query_graph", "trace_path", "get_file_outline",
                    "get_code_snippet", "get_graph_schema", "compare_graphs",
                    "get_architecture", "search_code", "list_projects", "index_status",
                    "check_index_coverage",
                ],
            }
        ]
    }


def _agent_dir(tmp_path):
    target = tmp_path / "agents"
    target.mkdir()
    for profile in PROFILES.glob("*.md"):
        shutil.copy(profile, target / profile.name)
    return target


def _codes(result):
    return {error["code"] for error in result["errors"]}


def test_shipped_bindings_inject_every_declared_capability(tmp_path):
    result = VERIFY.verify(BINDINGS, ROOT, _agent_dir(tmp_path), _catalog())
    assert result["ok"], result["errors"]
    assert result["summary"]["blocked"] == []
    assert result["summary"]["roles"] == 6
    # The live catalog was supplied, so no not-checked warning remains.
    assert not any("live MCP catalog not checked" in warning for warning in result["warnings"])


def test_missing_installed_identity_blocks_the_role(tmp_path):
    empty = tmp_path / "agents"
    empty.mkdir()
    result = VERIFY.verify(BINDINGS, ROOT, empty, _catalog())
    assert not result["ok"]
    assert "IDENTITY_NOT_INSTALLED" in _codes(result)
    assert {"planner", "tester", "scout.graph"} <= {
        error["subject"] for error in result["errors"]
        if error["code"] == "IDENTITY_NOT_INSTALLED"
    }


def test_live_catalog_must_expose_every_selected_mcp_tool(tmp_path):
    catalog = _catalog()
    catalog["servers"][0]["tools"].remove("search_graph")
    result = VERIFY.verify(BINDINGS, ROOT, _agent_dir(tmp_path), catalog)
    assert not result["ok"]
    assert "MCP_TOOL_UNAVAILABLE" in _codes(result)


def test_unavailable_mcp_server_blocks_graph_scout(tmp_path):
    catalog = _catalog()
    catalog["servers"][0]["state"] = "error"
    result = VERIFY.verify(BINDINGS, ROOT, _agent_dir(tmp_path), catalog)
    assert not result["ok"]
    assert "MCP_SERVER_UNAVAILABLE" in _codes(result)


def test_profile_must_carry_the_mcp_selectors_the_variant_requires(tmp_path):
    skill_root = tmp_path / "skill"
    shutil.copytree(ROOT, skill_root)
    profile = skill_root / "agents" / "pi" / "codebase-memory-scout.md"
    text = profile.read_text(encoding="utf-8").replace(
        "  - mcp:codebase-memory-mcp/search_graph\n", ""
    )
    profile.write_text(text, encoding="utf-8")
    result = VERIFY.verify(BINDINGS, skill_root, _agent_dir(tmp_path), _catalog())
    assert not result["ok"]
    assert "REQUIRED_MCP_NOT_INJECTED" in _codes(result)


def test_forbidden_mutation_tool_is_rejected(tmp_path):
    bindings = yaml.safe_load(BINDINGS.read_text(encoding="utf-8"))
    bindings["roles"]["reviewer"]["tools"].append("edit")
    modified = tmp_path / "pi-bindings.yaml"
    modified.write_text(yaml.safe_dump(bindings, sort_keys=False), encoding="utf-8")
    result = VERIFY.verify(modified, ROOT, _agent_dir(tmp_path), _catalog())
    assert not result["ok"]
    assert "CAPABILITY_FORBIDDEN_TOOL" in _codes(result)
    assert "ROLE_MUTATION_CONTRADICTION" in _codes(result)


def test_unknown_capability_is_reported(tmp_path):
    bindings = yaml.safe_load(BINDINGS.read_text(encoding="utf-8"))
    bindings["roles"]["scout"]["capabilities"].append("unspecified_capability")
    modified = tmp_path / "pi-bindings.yaml"
    modified.write_text(yaml.safe_dump(bindings, sort_keys=False), encoding="utf-8")
    result = VERIFY.verify(modified, ROOT, _agent_dir(tmp_path), _catalog())
    assert "CAPABILITY_RULE_UNKNOWN" in _codes(result)


def test_missing_injection_failure_semantics_is_rejected(tmp_path):
    bindings = yaml.safe_load(BINDINGS.read_text(encoding="utf-8"))
    bindings["injection"]["missing_identity_or_tool"] = "warn"
    modified = tmp_path / "pi-bindings.yaml"
    modified.write_text(yaml.safe_dump(bindings, sort_keys=False), encoding="utf-8")
    result = VERIFY.verify(modified, ROOT, _agent_dir(tmp_path), _catalog())
    assert "INJECTION_FAILURE_NOT_BLOCKED" in _codes(result)


def test_tester_modes_bind_separate_identities(tmp_path):
    bindings = yaml.safe_load(BINDINGS.read_text(encoding="utf-8"))
    modes = bindings["roles"]["tester"]["modes"]
    assert set(modes) == {"test_executor", "test_author"}
    assert modes["test_executor"]["agent_profile"] != modes["test_author"]["agent_profile"]
    assert not {"edit", "write"} & set(modes["test_executor"]["tools"])
    assert {"edit", "write"} <= set(modes["test_author"]["tools"])
    assert "write_owned_scope" in modes["test_author"]["capabilities"]
    assert modes["test_author"]["requires_owned_test_paths"] is True
    result = VERIFY.verify(BINDINGS, ROOT, _agent_dir(tmp_path), _catalog())
    assert result["ok"], result["errors"]


def test_executor_with_shared_write_surface_is_rejected(tmp_path):
    bindings = yaml.safe_load(BINDINGS.read_text(encoding="utf-8"))
    bindings["roles"]["tester"]["tools"].append("edit")
    bindings["roles"]["tester"]["modes"]["test_executor"]["tools"].append("edit")
    modified = tmp_path / "pi-bindings.yaml"
    modified.write_text(yaml.safe_dump(bindings, sort_keys=False), encoding="utf-8")
    result = VERIFY.verify(modified, ROOT, _agent_dir(tmp_path), _catalog())
    assert not result["ok"]
    assert "WRITE_SURFACE_UNDECLARED" in _codes(result)


def test_missing_author_identity_blocks_only_that_mode(tmp_path):
    agents = _agent_dir(tmp_path)
    (agents / "tester-author.md").unlink()
    result = VERIFY.verify(BINDINGS, ROOT, agents, _catalog())
    assert not result["ok"]
    missing = {
        error["subject"] for error in result["errors"]
        if error["code"] == "IDENTITY_NOT_INSTALLED"
    }
    assert missing == {"tester.test_author"}


def test_frontmatter_parser_reads_tools_and_identity():
    profile = VERIFY._frontmatter(PROFILES / "planner.md")
    assert profile["name"] == "planner"
    assert profile["acceptanceRole"] == "read-only"
    assert "edit" not in profile["tools"]


def test_cli_reports_json_and_exit_codes(tmp_path, capsys):
    agent_dir = _agent_dir(tmp_path)
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps(_catalog()), encoding="utf-8")
    code = VERIFY.main([
        "--bindings", str(BINDINGS),
        "--skill-root", str(ROOT),
        "--agent-dir", str(agent_dir),
        "--mcp-catalog", str(catalog_path),
    ])
    assert code == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True

    code = VERIFY.main([
        "--bindings", str(BINDINGS),
        "--skill-root", str(ROOT),
        "--agent-dir", str(tmp_path / "absent"),
    ])
    assert code == 1
    assert json.loads(capsys.readouterr().out)["ok"] is False
