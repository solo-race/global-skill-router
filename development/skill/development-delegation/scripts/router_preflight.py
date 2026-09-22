#!/usr/bin/env python3
"""Read-only preflight for DeepSeek subagents routed through Codex Router."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.9/3.10 can still import this module for tests.
    tomllib = None

ROUTE = "deepseek/deepseek-v4.1-flash"
AGENT_IDS = ("scout-deepseek", "implementer-deepseek", "tester-deepseek")
MAX_CATALOG_BYTES = 20_000_000
MAX_LIVE_CATALOG_BYTES = 10_000_000


class PreflightError(ValueError):
    """A local setup issue that can be reported without exposing credentials."""


def read_toml(path: Path) -> dict:
    if tomllib is None:
        raise PreflightError("Python 3.11 or newer is required for Router preflight.")
    try:
        with path.open("rb") as stream:
            return tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise PreflightError(
            f"Cannot read valid TOML from {path.name} ({type(exc).__name__})."
        ) from None


def merge_tables(base: dict, overlay: dict) -> dict:
    result = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_tables(result[key], value)
        else:
            result[key] = value
    return result


def active_config(codex_home: Path, requested_profile: str | None) -> tuple[dict, str | None]:
    config = read_toml(codex_home / "config.toml")
    selected = requested_profile or config.get("profile")
    if not selected:
        return config, None
    if not isinstance(selected, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", selected):
        raise PreflightError("The selected Codex profile name is invalid.")
    standalone = codex_home / f"{selected}.config.toml"
    inline = config.get("profiles", {}).get(selected)
    if standalone.is_file() and inline is not None:
        raise PreflightError("Both standalone and inline Codex profile definitions exist.")
    if standalone.is_file():
        return merge_tables(config, read_toml(standalone)), selected
    if isinstance(inline, dict):
        return merge_tables(config, inline), selected
    raise PreflightError("The selected Codex profile is not available as a readable config.")


def resolve_config_path(value: str, codex_home: Path) -> Path:
    home = Path.home()
    expanded = value.replace("${CODEX_HOME}", str(codex_home)).replace("$CODEX_HOME", str(codex_home))
    expanded = expanded.replace("${HOME}", str(home)).replace("$HOME", str(home))
    path = Path(expanded).expanduser()
    return path if path.is_absolute() else codex_home / path


def model_entries(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [entry for entry in payload if isinstance(entry, dict)]
    if isinstance(payload, dict):
        for key in ("models", "data"):
            if isinstance(payload.get(key), list):
                return model_entries(payload[key])
    raise PreflightError("The configured Codex model catalog has an unrecognized structure.")


def model_id(entry: dict) -> str | None:
    return entry.get("slug") or entry.get("id")


def is_router_url(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = urlsplit(value)
        loopback = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        path = parsed.path.rstrip("/")
        known_path = path == "/v1" or bool(
            re.fullmatch(r"/_codex-router/[A-Za-z0-9_-]+/v1", path)
        )
        _ = parsed.port
        return (
            parsed.scheme in {"http", "https"}
            and loopback
            and known_path
            and not parsed.query
            and not parsed.fragment
            and not parsed.username
            and not parsed.password
        )
    except (TypeError, ValueError):
        return False


def provider_url(config: dict) -> str | None:
    provider = config.get("model_provider", "openai")
    if provider == "openai":
        value = config.get("openai_base_url")
    else:
        providers = config.get("model_providers", {})
        definition = providers.get(provider, {}) if isinstance(providers, dict) else {}
        value = definition.get("base_url") if isinstance(definition, dict) else None
    return value if isinstance(value, str) else None


def load_catalog(config: dict, codex_home: Path) -> tuple[dict | None, list[str]]:
    value = config.get("model_catalog_json")
    if not isinstance(value, str) or not value:
        return None, ["No model_catalog_json is configured for the active Codex profile."]
    path = resolve_config_path(value, codex_home)
    try:
        if path.stat().st_size > MAX_CATALOG_BYTES:
            return None, ["The configured Codex model catalog exceeds the supported size."]
        payload = json.loads(path.read_text(encoding="utf-8"))
        entries = model_entries(payload)
    except PreflightError as exc:
        return None, [str(exc)]
    except (OSError, json.JSONDecodeError, UnicodeError) as exc:
        return None, [f"Cannot read the configured model catalog ({type(exc).__name__})."]
    matches = [entry for entry in entries if model_id(entry) == ROUTE]
    if len(matches) != 1:
        return None, [f"The Router route {ROUTE} is missing or duplicated in the local catalog."]
    return matches[0], []


def registered_agent_profile(config: dict, codex_home: Path, agent_id: str) -> tuple[dict | None, list[str]]:
    agents = config.get("agents", {})
    if not isinstance(agents, dict):
        return None, ["The active Codex config has no valid agents table."]
    if agents.get("enabled") is False:
        return None, ["Codex subagents are disabled in the active config."]
    registration = agents.get(agent_id)
    if not isinstance(registration, dict):
        return None, [f"{agent_id} is not registered in the active Codex config."]
    config_file = registration.get("config_file")
    if not isinstance(config_file, str) or not config_file:
        return None, [f"{agent_id} has no config_file registration."]
    try:
        role = read_toml(resolve_config_path(config_file, codex_home))
    except PreflightError as exc:
        return None, [f"Cannot load the registered profile for {agent_id}: {exc}."]
    reasons = []
    if role.get("name") != agent_id:
        reasons.append(f"The profile name does not match {agent_id}.")
    if role.get("model") != ROUTE:
        reasons.append(f"{agent_id} must use the Codex Router route slug {ROUTE}.")
    if "model_provider" in role:
        reasons.append(
            f"{agent_id} overrides model_provider; the profile must inherit the active Router provider."
        )
    return role, reasons


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise PreflightError("The local Router catalog redirected; the URL is withheld.")


def check_local_catalog(url: str, route: str = ROUTE) -> None:
    """GET the loopback Router model catalog without proxies or redirects."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(url.rstrip("/") + "/models", headers={"Accept": "application/json"})
    try:
        with opener.open(request, timeout=5) as response:
            body = response.read(MAX_LIVE_CATALOG_BYTES + 1)
        if len(body) > MAX_LIVE_CATALOG_BYTES:
            raise PreflightError("The local Router model catalog exceeds the supported size.")
        entries = model_entries(json.loads(body))
    except PreflightError:
        raise
    except (OSError, urllib.error.URLError, json.JSONDecodeError, UnicodeError) as exc:
        raise PreflightError(
            f"The local Router catalog check failed ({type(exc).__name__}); URL withheld."
        ) from None
    if not any(model_id(entry) == route for entry in entries):
        raise PreflightError(f"The live local Router catalog does not advertise {route}.")


def unavailable_report(reason: str, profile: str | None = None) -> dict:
    return {
        "status": "unavailable",
        "route": ROUTE,
        "profile_inspected": profile,
        "runtime_verified": False,
        "inference_request_made": False,
        "local_router_checked": False,
        "reasons": [reason],
        "agents": {
            agent_id: {"available": False, "reasons": [reason]}
            for agent_id in AGENT_IDS
        },
    }


def inspect(codex_home: Path, profile: str | None = None, check_live: bool = False) -> dict:
    """Return redacted readiness evidence; never make a model inference request."""
    try:
        config, selected = active_config(codex_home, profile)
    except PreflightError as exc:
        return unavailable_report(str(exc), profile)

    common_reasons = []
    router_url = provider_url(config)
    router_configured = is_router_url(router_url)
    if not router_configured:
        common_reasons.append(
            "The active Codex provider does not point to a recognized loopback Codex Router URL."
        )

    catalog_entry, catalog_reasons = load_catalog(config, codex_home)
    common_reasons.extend(catalog_reasons)
    route_v2 = catalog_entry is not None and catalog_entry.get("multi_agent_version") == "v2"
    if catalog_entry is not None and not route_v2:
        common_reasons.append(
            f"The Router route {ROUTE} is not advertised with multi_agent_version = v2."
        )

    role_reports = {}
    for agent_id in AGENT_IDS:
        role, role_reasons = registered_agent_profile(config, codex_home, agent_id)
        reasons = list(common_reasons) + role_reasons
        if role is not None and catalog_entry is not None:
            effort = role.get("model_reasoning_effort")
            levels = catalog_entry.get("supported_reasoning_levels")
            if effort and isinstance(levels, list) and levels:
                supported = [
                    item.get("effort") if isinstance(item, dict) else item
                    for item in levels
                ]
                if effort not in supported:
                    reasons.append(
                        f"{agent_id} requests a reasoning effort unsupported by the Router catalog."
                    )
        role_reports[agent_id] = {
            "available": not reasons,
            "model": role.get("model") if role is not None else None,
            "reasons": reasons,
        }

    live_checked = False
    live_route_visible = None
    if check_live and router_configured and route_v2 and not catalog_reasons:
        live_checked = True
        try:
            check_local_catalog(router_url)
            live_route_visible = True
        except PreflightError as exc:
            live_route_visible = False
            for report in role_reports.values():
                report["available"] = False
                report["reasons"].append(str(exc))

    available_agents = [
        agent_id for agent_id, report in role_reports.items() if report["available"]
    ]
    static_ready = bool(available_agents)
    if check_live and live_checked:
        static_ready = static_ready and live_route_visible is True

    reasons = []
    for agent_report in role_reports.values():
        for reason in agent_report["reasons"]:
            if reason not in reasons:
                reasons.append(reason)

    return {
        "status": "ready_for_runtime_probe" if static_ready else "unavailable",
        "route": ROUTE,
        "profile_inspected": selected,
        "router_provider_configured": router_configured,
        "catalog_route_present": catalog_entry is not None,
        "catalog_route_supports_native_subagents": route_v2,
        "local_router_checked": live_checked,
        "local_router_route_visible": live_route_visible,
        "runtime_verified": False,
        "inference_request_made": False,
        "available_agents": available_agents,
        "agents": role_reports,
        "reasons": reasons,
        "scope_note": "Static config checks do not observe UI/session overrides or prove a native child spawn.",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-home", help="Codex home containing config.toml; defaults to CODEX_HOME or ~/.codex.")
    parser.add_argument("--profile", help="Inspect this Codex profile instead of the configured default.")
    parser.add_argument(
        "--check-local-router",
        action="store_true",
        help="GET the loopback /models endpoint; no inference request is made.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    codex_home = Path(
        args.codex_home or os.environ.get("CODEX_HOME") or (Path.home() / ".codex")
    ).expanduser()
    report = inspect(codex_home, args.profile, args.check_local_router)
    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
