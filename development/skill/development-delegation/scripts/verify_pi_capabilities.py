#!/usr/bin/env python3
"""Verify that Pi role bindings inject the tool surface each role requires.

Role mapping is not capability mapping. A Pi child receives only the tools in its
agent definition's strict allowlist, does not inherit skills, and receives no ambient
extension tools in the foreground. This read-only check compares the declarative
bindings and the shipped Pi agent profiles against those rules, and optionally
against two live facts: the installed agent directory and ``pi mcp list --json``.

Usage:
  uv run python scripts/verify_pi_capabilities.py
  pi mcp list --json > /tmp/mcp.json
  uv run python scripts/verify_pi_capabilities.py --mcp-catalog /tmp/mcp.json --agent-dir ~/.pi/agent/agents

Exit codes: 0 all declared capabilities are injected, 1 blocked or malformed
binding, 130 on KeyboardInterrupt. Output is one JSON report on stdout.

Third-party dependency: PyYAML, declared for repository tooling in the root AGENTS.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BINDINGS = SKILL_ROOT / "routing" / "pi-bindings.yaml"
DEFAULT_AGENT_DIR = Path.home() / ".pi" / "agent" / "agents"
READ_TOOLS = {"read", "grep", "find", "ls"}


class Report:
    """Collect structured errors and warnings."""

    def __init__(self):
        self.errors: list[dict] = []
        self.warnings: list[str] = []

    def error(self, code: str, subject: str, message: str) -> None:
        self.errors.append({"code": code, "subject": subject, "message": message})

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    _, _, rest = text.partition("---")
    header, separator, _body = rest.partition("\n---")
    if not separator:
        return {}
    data = yaml.safe_load(header)
    return data if isinstance(data, dict) else {}


def _tools(profile: dict) -> list[str]:
    tools = profile.get("tools")
    return list(tools) if isinstance(tools, list) else []


def _selector(server: str, tool: str) -> str:
    return f"mcp:{server}/{tool}"


def _capability_rule_errors(role: str, spec: dict, rules: dict, report: Report) -> None:
    tools = spec.get("tools")
    declared = list(tools) if isinstance(tools, list) else []
    for capability in spec.get("capabilities") or []:
        rule = rules.get(capability)
        if not isinstance(rule, dict):
            report.error(
                "CAPABILITY_RULE_UNKNOWN", f"{role}.{capability}",
                f"no capability rule declares what {capability!r} requires",
            )
            continue
        if "needs_one_of" in rule:
            required = set(rule["needs_one_of"])
            if not required & set(declared):
                report.error(
                    "CAPABILITY_NOT_INJECTED", f"{role}.{capability}",
                    f"declared tools {declared} provide none of {sorted(required)}",
                )
        if "needs_all" in rule:
            missing = set(rule["needs_all"]) - set(declared)
            if missing:
                report.error(
                    "CAPABILITY_NOT_INJECTED", f"{role}.{capability}",
                    f"declared tools miss {sorted(missing)}",
                )
        if "forbids" in rule:
            forbidden = set(rule["forbids"]) & set(declared)
            if forbidden:
                report.error(
                    "CAPABILITY_FORBIDDEN_TOOL", f"{role}.{capability}",
                    f"declared tools include forbidden {sorted(forbidden)}",
                )


def _profile_errors(
    subject: str,
    spec: dict,
    skill_root: Path,
    agent_dir: Path | None,
    report: Report,
) -> str | None:
    relative = spec.get("agent_profile")
    identity = spec.get("identity")
    if not isinstance(relative, str):
        return None
    path = (skill_root / relative).resolve()
    if not path.is_file():
        report.error("AGENT_PROFILE_MISSING", subject, f"agent profile is missing: {relative}")
        return None
    profile = _frontmatter(path)
    if profile.get("name") != identity:
        report.error(
            "AGENT_PROFILE_IDENTITY_MISMATCH", subject,
            f"profile name {profile.get('name')!r} does not match binding identity {identity!r}",
        )
    declared = spec.get("tools")
    required = set(declared) if isinstance(declared, list) else set()
    required.discard("assignment_scoped")
    missing = required - set(_tools(profile))
    if missing:
        report.error(
            "AGENT_PROFILE_TOOLS_INCOMPLETE", subject,
            f"profile tools miss the binding's declared tools {sorted(missing)}",
        )
    if spec.get("async_required") and profile.get("async") is not True:
        report.error(
            "AGENT_PROFILE_ASYNC_MISSING", subject,
            "profile must default to background async launches for its MCP surface",
        )
    if agent_dir is not None:
        if not agent_dir.is_dir():
            report.error(
                "AGENT_DIR_MISSING", subject, f"agent directory does not exist: {agent_dir}"
            )
        elif not _installed(agent_dir, identity):
            report.error(
                "IDENTITY_NOT_INSTALLED", subject,
                f"{identity!r} is not registered under {agent_dir}; the assignment is BLOCKED",
            )
    return relative


def _installed(agent_dir: Path, identity: str) -> bool:
    for candidate in agent_dir.rglob("*.md"):
        if _frontmatter(candidate).get("name") == identity:
            return True
    return False


def _mcp_errors(
    subject: str,
    required: dict,
    profile: dict | None,
    catalog: dict | None,
    report: Report,
) -> None:
    server = required.get("server")
    tools = required.get("tools")
    if not isinstance(server, str) or not isinstance(tools, list) or not tools:
        report.error("REQUIRED_MCP_INVALID", subject, "required_mcp needs a server and tool names")
        return
    if profile is not None:
        absent = [
            tool for tool in tools
            if _selector(server, tool) not in _tools(profile)
        ]
        if absent:
            report.error(
                "REQUIRED_MCP_NOT_INJECTED", subject,
                f"agent profile lacks MCP selectors for {absent}",
            )
    if catalog is None:
        report.warn(f"{subject}: live MCP catalog not checked (pass --mcp-catalog)")
        return
    servers = {
        entry.get("name"): entry
        for entry in catalog.get("servers", [])
        if isinstance(entry, dict)
    }
    entry = servers.get(server)
    if entry is None:
        report.error("MCP_SERVER_UNKNOWN", subject, f"unknown MCP server {server!r}")
        return
    if entry.get("enabled") is not True or entry.get("state") != "connected":
        report.error(
            "MCP_SERVER_UNAVAILABLE", subject,
            f"{server!r} is not connected (state={entry.get('state')!r})",
        )
    available = set(entry.get("tools") or [])
    missing = [tool for tool in tools if tool not in available]
    if missing:
        report.error(
            "MCP_TOOL_UNAVAILABLE", subject,
            f"{server!r} does not expose {missing}",
        )


WRITE_TOOLS = {"edit", "write"}


def _write_surface_errors(subject, spec, capabilities, tools, profile_tools, report) -> None:
    """A write tool is only legal for a declared write capability or bound output."""

    declared = set(tools) if isinstance(tools, list) else set()
    exposed = WRITE_TOOLS & (declared | set(profile_tools))
    if not exposed:
        return
    if "write_owned_scope" in capabilities:
        return
    if spec.get("write_scope") == "bound_output_only":
        return
    report.error(
        "WRITE_SURFACE_UNDECLARED", subject,
        f"exposes {sorted(exposed)} without write_owned_scope or bound_output_only",
    )


def _contract_errors(subject, spec, rules, skill_root, agent_dir, catalog, report) -> None:
    """Check one role, variant, or mode binding against its declared capability."""

    tools = spec.get("tools")
    if not (isinstance(tools, list) or tools == "assignment_scoped"):
        report.error("ROLE_TOOLS_INVALID", subject, "binding must declare tools or assignment_scoped")
        return
    capabilities = spec.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        report.error("ROLE_CAPABILITIES_MISSING", subject, "binding must declare capabilities")
        return
    if tools != "assignment_scoped":
        _capability_rule_errors(subject, spec, rules, report)
    forbidden = set((rules.get("independent_review") or {}).get("forbids") or [])
    if spec.get("mutation") == "forbidden" and forbidden & set(tools or []):
        report.error(
            "ROLE_MUTATION_CONTRADICTION", subject,
            f"mutation is forbidden but tools include {sorted(forbidden & set(tools))}",
        )
    profile = _profile_errors(subject, spec, Path(skill_root), agent_dir, report)
    profile_tools = _tools(_frontmatter(Path(skill_root) / profile)) if profile else []
    _write_surface_errors(subject, spec, capabilities, tools, profile_tools, report)
    if "graph_discovery" in capabilities:
        _mcp_errors(
            subject,
            spec.get("required_mcp") or {},
            _frontmatter(Path(skill_root) / profile) if profile else None,
            catalog,
            report,
        )


def verify(
    bindings_path: Path = DEFAULT_BINDINGS,
    skill_root: Path = SKILL_ROOT,
    agent_dir: Path | None = DEFAULT_AGENT_DIR,
    catalog: dict | None = None,
) -> dict:
    report = Report()
    try:
        bindings = yaml.safe_load(Path(bindings_path).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        report.error("BINDINGS_UNREADABLE", "(bindings)", str(exc))
        return _report(report, {})
    if not isinstance(bindings, dict) or bindings.get("kind") != "declarative-pi-role-bindings":
        report.error("BINDINGS_INVALID", "(bindings)", "unexpected bindings document")
        return _report(report, {})
    injection = bindings.get("injection") or {}
    if injection.get("missing_identity_or_tool") != "BLOCKED":
        report.error(
            "INJECTION_FAILURE_NOT_BLOCKED", "injection",
            "missing identity or tool must resolve to BLOCKED",
        )
    for key in ("mechanism", "mcp_selector_prefix", "role_knowledge_source", "verifier"):
        if not injection.get(key):
            report.error("INJECTION_FIELD_MISSING", "injection", f"missing {key}")

    rules = bindings.get("capability_rules") or {}
    roles = bindings.get("roles") or {}
    for role, spec in roles.items():
        if not isinstance(spec, dict):
            report.error("ROLE_INVALID", role, "role binding must be a mapping")
            continue
        _contract_errors(role, spec, rules, skill_root, agent_dir, catalog, report)
        for name, variant in (spec.get("variants") or {}).items():
            subject = f"{role}.{name}"
            if not isinstance(variant, dict) or not variant.get("select_when"):
                report.error("VARIANT_INVALID", subject, "variant needs select_when and a binding")
                continue
            _contract_errors(subject, variant, rules, skill_root, agent_dir, catalog, report)
        for name, mode in (spec.get("modes") or {}).items():
            subject = f"{role}.{name}"
            if not isinstance(mode, dict):
                report.error("MODE_INVALID", subject, "mode binding must be a mapping")
                continue
            _contract_errors(subject, mode, rules, skill_root, agent_dir, catalog, report)
    if catalog is None:
        report.warn("live MCP catalog not checked; run `pi mcp list --json` and pass --mcp-catalog")
    blocked = sorted({error["subject"] for error in report.errors})
    return _report(report, {"roles": len(roles), "blocked": blocked})


def _report(report: Report, summary: dict) -> dict:
    return {
        "ok": not report.errors,
        "summary": summary,
        "errors": report.errors,
        "warnings": report.warnings,
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Verify Pi role capability injection.")
    parser.add_argument("--bindings", default=str(DEFAULT_BINDINGS))
    parser.add_argument("--skill-root", default=str(SKILL_ROOT))
    parser.add_argument("--agent-dir", default=str(DEFAULT_AGENT_DIR))
    parser.add_argument("--mcp-catalog", default=None, help="JSON from `pi mcp list --json`")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    catalog = None
    if args.mcp_catalog:
        try:
            catalog = json.loads(Path(args.mcp_catalog).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(json.dumps({"ok": False, "errors": [{"code": "CATALOG_UNREADABLE",
                                                       "message": str(exc)}]}, indent=2),
                  file=sys.stderr)
            return 1
    result = verify(
        Path(args.bindings),
        Path(args.skill_root),
        Path(args.agent_dir) if args.agent_dir else None,
        catalog,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
