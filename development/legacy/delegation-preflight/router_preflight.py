#!/usr/bin/env python3
"""Static readiness preflight for session-selected Codex subagent roles.

Read-only: this helper never issues an inference request, never reads
credentials, and never changes state. It reports static configuration evidence
for the exact identities a session selected. Report contract:
references/preflight-report.md (schema_version preflight_report/1).
A passive runtime receipt may be supplied with --receipt to correlate existing
routing evidence with a role; supplying one never triggers a probe or an
inference request. Receipt contract: references/runtime-receipt.md.

Exit codes: 0 a complete report was produced (consumers still read the
readiness fields), 1 bootstrap or internal execution failure, 130 interrupted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.9/3.10 can still import this module for tests.
    tomllib = None

SCHEMA_VERSION = "preflight_report/1"
DEFAULT_ROLES = ("scout", "implementer", "tester")
ROLE_ID_PATTERN = re.compile(r"[A-Za-z0-9._-]+")
MAX_CATALOG_BYTES = 20_000_000
MAX_LIVE_CATALOG_BYTES = 10_000_000
CATALOG_TIMEOUT_SECONDS = 5
UNOBSERVABLE_LAYERS = ("cli_override", "project_config", "session_override")
ROUTE_LOOPBACK = "loopback"
ROUTE_REMOTE = "remote"
ROUTE_UNKNOWN = "unknown"
STATIC_SCOPE = "static_preflight"
STATIC_LIMITS = (
    "Static configuration evidence only: CLI, project, host-policy and session "
    "overrides are not observable here, and no child spawn or model identity is proved."
)
RECEIPT_SCHEMA_VERSION = "runtime_receipt/1"
MAX_RECEIPT_BYTES = 1_000_000
DEFAULT_RECEIPT_MAX_AGE_SECONDS = 86_400
RECEIPT_ROUTE_DECISIONS = ("router", "direct")
RECEIPT_REQUIRED_KEYS = (
    "schema_version",
    "role_id",
    "session_id",
    "request_id",
    "requested_slug",
    "route_decision",
    "upstream_provider",
    "upstream_model",
    "observed_at",
    "bindings",
    "source",
)
RECEIPT_BINDING_KEYS = ("config_sha256", "catalog_sha256", "profile_sha256")
RECEIPT_TEXT_KEYS = (
    "role_id",
    "session_id",
    "request_id",
    "requested_slug",
    "route_decision",
    "upstream_provider",
    "upstream_model",
    "observed_at",
    "source",
)


class PreflightError(ValueError):
    """A local setup issue that can be reported without exposing credentials."""


class ConfigUnreadable(PreflightError):
    """The active Codex configuration could not be read or parsed."""


class ReceiptInvalid(PreflightError):
    """A supplied passive runtime receipt could not be used as evidence."""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def host_platform() -> str:
    return "windows" if os.name == "nt" else "posix"


def read_toml(path: Path) -> dict:
    if tomllib is None:
        raise PreflightError("Python 3.11 or newer is required to read TOML.")
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
    config_path = codex_home / "config.toml"
    if not config_path.is_file():
        raise ConfigUnreadable("The active Codex config.toml is absent.")
    try:
        config = read_toml(config_path)
    except PreflightError as exc:
        raise ConfigUnreadable("The active Codex config.toml could not be read.") from exc
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


def logical_reference(path: Path, codex_home: Path) -> str:
    """Redacted logical reference: relative to the Codex home, else the file name."""
    try:
        return path.resolve().relative_to(codex_home.resolve()).as_posix()
    except (OSError, ValueError):
        return path.name


def file_sha256(path: Path) -> str | None:
    """SHA-256 of a file's bytes, or None when it cannot be read."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def model_entries(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [entry for entry in payload if isinstance(entry, dict)]
    if isinstance(payload, dict):
        for key in ("models", "data"):
            if isinstance(payload.get(key), list):
                return model_entries(payload[key])
    raise PreflightError("The configured model catalog has an unrecognized structure.")


def model_id(entry: dict) -> str | None:
    value = entry.get("slug") or entry.get("id")
    return value if isinstance(value, str) and value else None


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


def endpoint_classification(value: object) -> str:
    """Endpoint shape only: loopback, remote, or unknown. Never a raw URL."""
    if not isinstance(value, str) or not value:
        return ROUTE_UNKNOWN
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return ROUTE_UNKNOWN
        return ROUTE_LOOPBACK if parsed.hostname in {"127.0.0.1", "localhost", "::1"} else ROUTE_REMOTE
    except (TypeError, ValueError):
        return ROUTE_UNKNOWN


def default_provider(config: dict) -> str:
    value = config.get("model_provider")
    return value if isinstance(value, str) and value else "openai"


def provider_entry(config: dict, provider: str) -> dict:
    if provider == "openai":
        return {}
    providers = config.get("model_providers", {})
    definition = providers.get(provider, {}) if isinstance(providers, dict) else {}
    return definition if isinstance(definition, dict) else {}


def provider_base_url(config: dict, provider: str) -> str | None:
    if provider == "openai":
        value = config.get("openai_base_url")
    else:
        value = provider_entry(config, provider).get("base_url")
    return value if isinstance(value, str) and value else None


def provider_label(config: dict, provider: str) -> str | None:
    label = provider_entry(config, provider).get("name")
    return label if isinstance(label, str) and label else None


def host_feature_state(config: dict) -> dict:
    features = config.get("features", {})
    features = features if isinstance(features, dict) else {}
    multi_agent = features.get("multi_agent")
    v2 = features.get("multi_agent_v2", {})
    v2_enabled = v2.get("enabled") if isinstance(v2, dict) else None
    return {
        "multi_agent": multi_agent if isinstance(multi_agent, bool) else None,
        "multi_agent_v2": v2_enabled if isinstance(v2_enabled, bool) else None,
    }


def host_interface(feature_state: dict) -> str:
    """Selected delegation interface of the host, or none/unknown."""
    if feature_state.get("multi_agent_v2") is True:
        return "v2"
    if feature_state.get("multi_agent") is True:
        return "v1"
    if feature_state.get("multi_agent") is None and feature_state.get("multi_agent_v2") is None:
        return "unknown"
    return "none"


def load_catalog(
    config: dict, codex_home: Path
) -> tuple[str, list[dict] | None, str | None, str | None, str | None]:
    """Return (state, entries, reason_code, logical_reference, file_sha256)."""
    value = config.get("model_catalog_json")
    if not isinstance(value, str) or not value:
        return "unchecked", None, "catalog_unchecked", None, None
    path = resolve_config_path(value, codex_home)
    reference = logical_reference(path, codex_home)
    digest = file_sha256(path)
    try:
        if path.stat().st_size > MAX_CATALOG_BYTES:
            return "error", None, "catalog_malformed", reference, digest
        payload = json.loads(path.read_text(encoding="utf-8"))
        entries = model_entries(payload)
    except FileNotFoundError:
        return "missing", None, "catalog_missing", reference, None
    except OSError:
        return "missing", None, "catalog_missing", reference, None
    except (json.JSONDecodeError, UnicodeError, PreflightError):
        return "error", None, "catalog_malformed", reference, digest
    if not entries:
        return "missing", None, "catalog_missing", reference, digest
    return "present", entries, None, reference, digest


def read_receipt(path: Path) -> dict:
    """Load one runtime_receipt/1 document, or raise ReceiptInvalid."""
    try:
        if path.stat().st_size > MAX_RECEIPT_BYTES:
            raise ReceiptInvalid("The supplied receipt exceeds the supported size.")
        payload = json.loads(path.read_text(encoding="utf-8"))
    except ReceiptInvalid:
        raise
    except (OSError, json.JSONDecodeError, UnicodeError):
        raise ReceiptInvalid("The supplied receipt could not be read as JSON.") from None
    if not isinstance(payload, dict):
        raise ReceiptInvalid("The supplied receipt is not a JSON object.")
    if payload.get("schema_version") != RECEIPT_SCHEMA_VERSION:
        raise ReceiptInvalid("The supplied receipt schema_version is unsupported.")
    for key in RECEIPT_REQUIRED_KEYS:
        if key not in payload:
            raise ReceiptInvalid(f"The supplied receipt is missing {key}.")
    for key in RECEIPT_TEXT_KEYS:
        if not isinstance(payload.get(key), str) or not payload[key]:
            raise ReceiptInvalid(f"The supplied receipt has an invalid {key}.")
    if payload["route_decision"] not in RECEIPT_ROUTE_DECISIONS:
        raise ReceiptInvalid("The supplied receipt has an invalid route_decision.")
    parse_receipt_timestamp(payload["observed_at"])
    bindings = payload.get("bindings")
    if not isinstance(bindings, dict) or any(key not in bindings for key in RECEIPT_BINDING_KEYS):
        raise ReceiptInvalid("The supplied receipt has invalid bindings.")
    for key in RECEIPT_BINDING_KEYS:
        value = bindings.get(key)
        if value is not None and not isinstance(value, str):
            raise ReceiptInvalid("The supplied receipt has invalid bindings.")
    return payload


def parse_receipt_timestamp(value: str) -> datetime:
    """Parse an explicitly UTC ISO-8601 receipt timestamp."""
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        observed = datetime.fromisoformat(normalized)
    except ValueError:
        raise ReceiptInvalid("The supplied receipt has an invalid observed_at.") from None
    if observed.tzinfo is None or observed.utcoffset() != timedelta(0):
        raise ReceiptInvalid("The supplied receipt has an invalid observed_at.")
    return observed.astimezone(timezone.utc)


def receipt_route_decision(route_class: str) -> str | None:
    if route_class == ROUTE_LOOPBACK:
        return "router"
    if route_class == ROUTE_REMOTE:
        return "direct"
    return None


def expected_upstream_pair(
    *,
    route_class: str,
    effective_provider: str,
    declared_slug: str | None,
    catalog_entry: dict | None,
) -> tuple[str, str] | None:
    """Return only a source-backed expected upstream provider/model pair."""
    if catalog_entry is None or not declared_slug:
        return None
    if route_class == ROUTE_REMOTE:
        return effective_provider, declared_slug
    if route_class != ROUTE_LOOPBACK:
        return None
    provenance = catalog_entry.get("opencodex_capability_provenance")
    if not isinstance(provenance, dict):
        return None
    provider = provenance.get("provider")
    upstream_model = provenance.get("model_id")
    if not isinstance(provider, str) or not provider:
        return None
    if not isinstance(upstream_model, str) or not upstream_model:
        return None
    return provider, upstream_model


def receipt_outcome(
    receipt: dict,
    *,
    role_id: str,
    session_id: str,
    now: datetime,
    max_age_seconds: int,
    declared_slug: str | None,
    expected_route_decision: str,
    expected_upstream: tuple[str, str] | None,
    config_hash: str | None,
    catalog_hash: str | None,
    profile_hash: str | None,
) -> str:
    """Classify one receipt against one role.

    Returns one terminal classification from the receipt evaluation order.
    """
    if receipt.get("role_id") != role_id:
        return "other_role"
    if receipt.get("session_id") != session_id:
        return "other_session"
    observed_at = parse_receipt_timestamp(receipt["observed_at"])
    if (now - observed_at).total_seconds() > max_age_seconds:
        return "expired"
    bindings = receipt.get("bindings") or {}
    if (
        bindings.get("config_sha256") != config_hash
        or bindings.get("catalog_sha256") != catalog_hash
        or bindings.get("profile_sha256") != profile_hash
    ):
        return "stale"
    if receipt.get("route_decision") != expected_route_decision:
        return "route_mismatch"
    if not declared_slug or receipt.get("requested_slug") != declared_slug:
        return "slug_mismatch"
    if expected_upstream is None:
        return "mapping_unknown"
    expected_provider, expected_model = expected_upstream
    if (
        receipt.get("upstream_provider") != expected_provider
        or receipt.get("upstream_model") != expected_model
    ):
        return "upstream_mismatch"
    return "verified"


def receipt_attribution(receipt: dict) -> dict:
    """Attribution evidence: routing evidence only, never proof of model identity."""
    return {
        "session_id": receipt.get("session_id"),
        "request_id": receipt.get("request_id"),
        "observed_at": receipt.get("observed_at"),
        "requested_slug": receipt.get("requested_slug"),
        "route_decision": receipt.get("route_decision"),
        "upstream_provider": receipt.get("upstream_provider"),
        "upstream_model": receipt.get("upstream_model"),
        "attribution": "routing_evidence_only",
    }


def evaluate_receipts(
    receipts: list[dict],
    *,
    role_id: str,
    session_id: str,
    now: datetime,
    max_age_seconds: int,
    declared_slug: str | None,
    expected_route_decision: str,
    expected_upstream: tuple[str, str] | None,
    config_hash: str | None,
    catalog_hash: str | None,
    profile_hash: str | None,
) -> tuple[str, list[str], dict | None]:
    """Resolve one role's receipt verdict as (runtime_route, reason_codes, attribution)."""
    matching = [
        (outcome, receipt)
        for outcome, receipt in (
            (
                receipt_outcome(
                    item,
                    role_id=role_id,
                    session_id=session_id,
                    now=now,
                    max_age_seconds=max_age_seconds,
                    declared_slug=declared_slug,
                    expected_route_decision=expected_route_decision,
                    expected_upstream=expected_upstream,
                    config_hash=config_hash,
                    catalog_hash=catalog_hash,
                    profile_hash=profile_hash,
                ),
                item,
            )
            for item in receipts
        )
        if outcome != "other_role"
    ]
    if not matching:
        return "unverified", [], None
    mismatched = [receipt for outcome, receipt in matching if outcome == "upstream_mismatch"]
    if mismatched:
        newest = max(mismatched, key=lambda item: parse_receipt_timestamp(item["observed_at"]))
        return "mismatch", ["receipt_mismatch"], receipt_attribution(newest)
    if any(outcome in {"route_mismatch", "slug_mismatch"} for outcome, _ in matching):
        return "unverified", ["receipt_mismatch"], None
    verified = [receipt for outcome, receipt in matching if outcome == "verified"]
    if verified:
        newest = max(verified, key=lambda item: parse_receipt_timestamp(item["observed_at"]))
        return "verified", [], receipt_attribution(newest)
    if any(outcome == "mapping_unknown" for outcome, _ in matching):
        return "unverified", ["router_mapping_unknown"], None
    if any(outcome == "other_session" for outcome, _ in matching):
        return "unverified", ["receipt_other_session"], None
    if any(outcome == "expired" for outcome, _ in matching):
        return "unverified", ["receipt_expired"], None
    return "unverified", ["receipt_stale"], None


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise PreflightError("The local router catalog redirected; the URL is withheld.")


def read_live_catalog(url: str) -> set[str]:
    """GET the loopback router model list without credentials, proxies or redirects."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(
        url.rstrip("/") + "/models", headers={"Accept": "application/json"}
    )
    with opener.open(request, timeout=CATALOG_TIMEOUT_SECONDS) as response:
        body = response.read(MAX_LIVE_CATALOG_BYTES + 1)
    if len(body) > MAX_LIVE_CATALOG_BYTES:
        raise PreflightError("The live router model list exceeds the supported size.")
    entries = model_entries(json.loads(body))
    return {entry for entry in (model_id(item) for item in entries) if entry}


def unavailable_role_record(role_id: str, reason_codes: list[str]) -> dict:
    return {
        "role_id": role_id,
        "registration_source": None,
        "profile_path": None,
        "profile_hash": None,
        "declared_model_slug": None,
        "declared_overrides": None,
        "inherited_configuration": None,
        "effective_values": None,
        "codex_provider_identity": None,
        "endpoint_classification": ROUTE_UNKNOWN,
        "delegation_evidence": None,
        "router_evidence": None,
        "evidence": {
            "bootstrap": "unknown",
            "configuration": "unknown",
            "catalog": "unchecked",
            "delegation": "unknown",
            "endpoint": "unchecked",
            "runtime_route": "unverified",
        },
        "unresolved_layers": ["inspection_not_performed"],
        "reason_codes": list(reason_codes),
        "available": False,
    }


def build_role_record(
    *,
    config: dict,
    codex_home: Path,
    role_id: str,
    feature_state: dict,
    interface: str,
    catalog_state: str,
    catalog_entries: list[dict] | None,
    catalog_code: str | None,
    live_checked: bool,
    live_slugs: set[str] | None,
    inputs: list[str],
    receipts: list[dict] | None = None,
    config_hash: str | None = None,
    catalog_hash: str | None = None,
    require_runtime: bool = False,
    session_id: str | None = None,
    receipt_max_age_seconds: int = DEFAULT_RECEIPT_MAX_AGE_SECONDS,
    now: datetime | None = None,
) -> dict:
    reason_codes: list[str] = []
    unresolved: list[str] = list(UNOBSERVABLE_LAYERS)
    registration_source = f"config.toml:[agents.{role_id}]"
    profile_path = None
    profile_hash = None
    declared_model_slug = None
    declared_overrides = None
    profile = None

    agents = config.get("agents")
    registration = agents.get(role_id) if isinstance(agents, dict) else None
    if not isinstance(agents, dict) or agents.get("enabled") is False or not isinstance(registration, dict):
        reason_codes.append("role_not_registered")
        unresolved.append("registration")
    else:
        config_file = registration.get("config_file")
        if not isinstance(config_file, str) or not config_file:
            reason_codes.append("profile_missing")
            unresolved.append("registration.config_file")
        else:
            profile_file = resolve_config_path(config_file, codex_home)
            reference = logical_reference(profile_file, codex_home)
            if reference not in inputs:
                inputs.append(reference)
            try:
                raw = profile_file.read_bytes()
            except OSError:
                reason_codes.append("profile_missing")
                unresolved.append("profile_bytes")
            else:
                profile_path = reference
                profile_hash = hashlib.sha256(raw).hexdigest()
                try:
                    profile = tomllib.loads(raw.decode("utf-8"))
                except (UnicodeError, tomllib.TOMLDecodeError):
                    profile = None
                    reason_codes.append("profile_unreadable")
                    unresolved.append("profile_toml")

    if profile is not None:
        model = profile.get("model")
        declared_model_slug = model if isinstance(model, str) and model else None
        override = profile.get("model_provider")
        declared_overrides = {
            "model": declared_model_slug,
            "model_provider": override if isinstance(override, str) and override else None,
        }
        if profile.get("name") != role_id:
            reason_codes.append("profile_name_mismatch")
            unresolved.append("profile_name")

    inherited_model = config.get("model")
    inherited_model = inherited_model if isinstance(inherited_model, str) and inherited_model else None
    inherited_provider = config.get("model_provider")
    inherited_provider = inherited_provider if isinstance(inherited_provider, str) and inherited_provider else None
    inherited_configuration = {
        "layers": ["config.toml"],
        "model": inherited_model,
        "model_provider": inherited_provider,
        "limitations": (
            "CLI, project, host-policy and session layers are not observable from "
            "static files, so these are inherited defaults, not effective ones."
        ),
    }
    effective_model = declared_model_slug or inherited_model
    effective_provider = "openai"
    if declared_overrides is not None and declared_overrides.get("model_provider"):
        effective_provider = declared_overrides["model_provider"]
    elif inherited_provider:
        effective_provider = inherited_provider
    effective_values = {"model": effective_model, "model_provider": effective_provider}

    base_url = provider_base_url(config, effective_provider)
    route_class = endpoint_classification(base_url)
    if base_url is None:
        reason_codes.append("provider_override_unknown")
        unresolved.append("provider_base_url")

    role_catalog = catalog_state
    entry = None
    if catalog_entries is not None:
        if effective_model is None:
            role_catalog = "missing"
            reason_codes.append("catalog_entry_missing")
            unresolved.append("effective_model")
        else:
            matches = [item for item in catalog_entries if model_id(item) == effective_model]
            if len(matches) == 1:
                role_catalog = "present"
                entry = matches[0]
            elif matches:
                role_catalog = "ambiguous"
                reason_codes.append("catalog_entry_ambiguous")
            else:
                role_catalog = "missing"
                reason_codes.append("catalog_entry_missing")
    if catalog_code and role_catalog in {"missing", "error", "unchecked"}:
        if catalog_code not in reason_codes:
            reason_codes.append(catalog_code)

    advertised = None
    if entry is not None:
        value = entry.get("multi_agent_version")
        advertised = value if isinstance(value, str) and value else None
    if interface == "none":
        delegation = "unsupported"
        reason_codes.append("delegation_disabled")
    elif interface == "unknown":
        delegation = "unknown"
    elif entry is None:
        delegation = "unknown"
    elif advertised is None:
        delegation = "unknown"
        reason_codes.append("router_mapping_unknown")
    elif advertised == interface:
        delegation = "supported"
    else:
        delegation = "unknown"
        reason_codes.append("delegation_interface_mismatch")

    endpoint = "unchecked"
    router_evidence = {
        "classification": route_class,
        "product_identity": "unverified",
        "live_catalog_checked": False,
        "live_route_visible": None,
    }
    if live_checked and route_class == ROUTE_LOOPBACK:
        router_evidence["live_catalog_checked"] = True
        if live_slugs is None:
            endpoint = "unreachable"
            reason_codes.append("endpoint_unreachable")
        else:
            endpoint = "reachable"
            visible = effective_model is not None and effective_model in live_slugs
            router_evidence["live_route_visible"] = visible
            if not visible:
                reason_codes.append("router_mapping_unknown")

    runtime_route = "unverified"
    delegation_evidence = {
        "host_interface": interface,
        "host_product": None,
        "feature_state": dict(feature_state),
        "registration": registration_source,
        "catalog_declared_version": advertised,
        "route_class": route_class,
        "passive_child_evidence": None,
    }
    expected_route = receipt_route_decision(route_class)
    expected_upstream = expected_upstream_pair(
        route_class=route_class,
        effective_provider=effective_provider,
        declared_slug=declared_model_slug,
        catalog_entry=entry,
    )
    if (
        receipts
        and session_id
        and entry is not None
        and declared_model_slug is not None
        and expected_route is not None
    ):
        runtime_route, receipt_codes, attribution = evaluate_receipts(
            receipts,
            role_id=role_id,
            session_id=session_id,
            now=now or datetime.now(timezone.utc),
            max_age_seconds=receipt_max_age_seconds,
            declared_slug=declared_model_slug,
            expected_route_decision=expected_route,
            expected_upstream=expected_upstream,
            config_hash=config_hash,
            catalog_hash=catalog_hash,
            profile_hash=profile_hash,
        )
        for code in receipt_codes:
            if code not in reason_codes:
                reason_codes.append(code)
        if attribution is not None:
            delegation_evidence["passive_child_evidence"] = attribution

    if "role_not_registered" in reason_codes or "profile_name_mismatch" in reason_codes or base_url is None:
        configuration = "conflict"
    elif profile is None:
        configuration = "unknown"
    else:
        configuration = "consistent"

    evidence = {
        "bootstrap": "ready",
        "configuration": configuration,
        "catalog": role_catalog,
        "delegation": delegation,
        "endpoint": endpoint,
        "runtime_route": runtime_route,
    }
    available = (
        configuration == "consistent"
        and delegation == "supported"
        and role_catalog == "present"
        and endpoint != "unreachable"
        and router_evidence["live_route_visible"] is not False
    )
    if require_runtime:
        available = available and runtime_route == "verified"

    return {
        "role_id": role_id,
        "registration_source": registration_source,
        "profile_path": profile_path,
        "profile_hash": profile_hash,
        "declared_model_slug": declared_model_slug,
        "declared_overrides": declared_overrides,
        "inherited_configuration": inherited_configuration,
        "effective_values": effective_values,
        "codex_provider_identity": {
            "key": effective_provider,
            "label": provider_label(config, effective_provider),
        },
        "endpoint_classification": route_class,
        "delegation_evidence": delegation_evidence,
        "router_evidence": router_evidence,
        "evidence": evidence,
        "unresolved_layers": unresolved,
        "reason_codes": reason_codes,
        "available": available,
    }


def envelope(
    bootstrap: str,
    bootstrap_failure: str | None,
    provenance: dict,
    roles: list[dict],
    error: dict | None,
) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "bootstrap": bootstrap,
        "bootstrap_failure": bootstrap_failure,
        "provenance": provenance,
        "roles": roles,
        "error": error,
    }


def make_provenance(requested: tuple[str, ...], requirements: list[str], inputs: list[str]) -> dict:
    return {
        "generated_at": utc_now(),
        "roles": list(requested),
        "operation": "preflight",
        "requirements": requirements,
        "inputs": inputs,
        "interpreter": platform.python_version(),
        "host": {"platform": host_platform(), "shell": None},
        "scope": STATIC_SCOPE,
        "limits": STATIC_LIMITS,
    }


def inspect_report(
    codex_home: Path,
    roles: tuple[str, ...] | list[str] = DEFAULT_ROLES,
    profile: str | None = None,
    check_live: bool = False,
    receipts: list[Path] | None = None,
    session_id: str | None = None,
    receipt_max_age_seconds: int = DEFAULT_RECEIPT_MAX_AGE_SECONDS,
    now: datetime | None = None,
) -> tuple[dict, int]:
    """Return (report, exit_code). Never issues inference and never mutates state."""
    requested = tuple(roles) if roles else DEFAULT_ROLES
    requirements = (
        ["static"] + (["endpoint"] if check_live else []) + (["runtime"] if receipts else [])
    )
    inputs: list[str] = []
    provenance = make_provenance(requested, requirements, inputs)

    if tomllib is None:
        return (
            envelope(
                "blocked",
                "dependency_unavailable",
                provenance,
                [],
                {
                    "code": "bootstrap_blocked",
                    "message": "Python 3.11 or newer with tomllib is required for preflight.",
                },
            ),
            1,
        )

    try:
        config, _selected = active_config(codex_home, profile)
    except ConfigUnreadable:
        inputs.append("config.toml")
        return (
            envelope(
                "ready",
                None,
                provenance,
                [unavailable_role_record(role_id, ["config_unreadable"]) for role_id in requested],
                {
                    "code": "config_unreadable",
                    "message": "The active Codex configuration could not be read or parsed.",
                },
            ),
            1,
        )
    except PreflightError:
        inputs.append("config.toml")
        return (
            envelope(
                "ready",
                None,
                provenance,
                [unavailable_role_record(role_id, ["profile_unreadable"]) for role_id in requested],
                {
                    "code": "profile_unreadable",
                    "message": "The selected Codex profile could not be resolved.",
                },
            ),
            1,
        )

    inputs.append("config.toml")
    feature_state = host_feature_state(config)
    interface = host_interface(feature_state)
    config_hash = file_sha256(codex_home / "config.toml")
    catalog_state, catalog_entries, catalog_code, catalog_reference, catalog_hash = load_catalog(
        config, codex_home
    )
    if catalog_reference and catalog_reference not in inputs:
        inputs.append(catalog_reference)

    receipt_documents: list[dict] = []
    receipt_error: str | None = "receipt_invalid" if receipts and not session_id else None
    for receipt_path in receipts or []:
        if receipt_path.name not in inputs:
            inputs.append(receipt_path.name)
        if receipt_error is not None:
            continue
        try:
            receipt_documents.append(read_receipt(receipt_path))
        except ReceiptInvalid:
            receipt_error = "receipt_invalid"
    if receipt_error is not None:
        receipt_documents = []

    live_checked = False
    live_slugs: set[str] | None = None
    if check_live:
        default_url = provider_base_url(config, default_provider(config))
        if is_router_url(default_url):
            live_checked = True
            try:
                live_slugs = read_live_catalog(default_url or "")
            except (PreflightError, OSError, urllib.error.URLError, json.JSONDecodeError, UnicodeError):
                live_slugs = None

    records = [
        build_role_record(
            config=config,
            codex_home=codex_home,
            role_id=role_id,
            feature_state=feature_state,
            interface=interface,
            catalog_state=catalog_state,
            catalog_entries=catalog_entries,
            catalog_code=catalog_code,
            live_checked=live_checked,
            live_slugs=live_slugs,
            inputs=inputs,
            receipts=receipt_documents or None,
            config_hash=config_hash,
            catalog_hash=catalog_hash,
            require_runtime=bool(receipts),
            session_id=session_id,
            receipt_max_age_seconds=receipt_max_age_seconds,
            now=now,
        )
        for role_id in requested
    ]
    if receipt_error is not None:
        return (
            envelope(
                "ready",
                None,
                provenance,
                records,
                {
                    "code": receipt_error,
                    "message": (
                        "A supplied passive receipt could not be used; "
                        "no receipt evidence was applied."
                    ),
                },
            ),
            1,
        )
    return envelope("ready", None, provenance, records, None), 0


def inspect(
    codex_home: Path,
    roles: tuple[str, ...] | list[str] = DEFAULT_ROLES,
    profile: str | None = None,
    check_live: bool = False,
    receipts: list[Path] | None = None,
    session_id: str | None = None,
    receipt_max_age_seconds: int = DEFAULT_RECEIPT_MAX_AGE_SECONDS,
    now: datetime | None = None,
) -> dict:
    """Convenience wrapper returning only the report document."""
    return inspect_report(
        codex_home,
        roles,
        profile,
        check_live,
        receipts,
        session_id,
        receipt_max_age_seconds,
        now,
    )[0]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--codex-home",
        help="Codex home containing config.toml; defaults to CODEX_HOME or ~/.codex.",
    )
    parser.add_argument("--profile", help="Inspect this Codex profile instead of the configured default.")
    parser.add_argument(
        "--role",
        action="append",
        dest="roles",
        metavar="ID",
        help=(
            "Registered identity to inspect; repeat once per identity. "
            "Defaults to scout, implementer and tester."
        ),
    )
    parser.add_argument(
        "--check-local-router",
        action="store_true",
        help="GET the loopback router model list; no inference request is made.",
    )
    parser.add_argument(
        "--receipt",
        action="append",
        dest="receipts",
        metavar="PATH",
        help=(
            "Passive runtime receipt (runtime_receipt/1) to correlate with the "
            "inspected roles; repeatable. Requires no probe or inference."
        ),
    )
    parser.add_argument(
        "--session-id",
        help="Current session identity; required whenever --receipt is supplied.",
    )
    parser.add_argument(
        "--receipt-max-age-seconds",
        type=int,
        default=DEFAULT_RECEIPT_MAX_AGE_SECONDS,
        metavar="SECONDS",
        help=(
            "Maximum age of current-session receipt evidence; older receipts are "
            "history only (default: 86400)."
        ),
    )
    args = parser.parse_args()
    if args.roles:
        for role_id in args.roles:
            if not ROLE_ID_PATTERN.fullmatch(role_id):
                parser.error("role identities must match [A-Za-z0-9._-]+")
    return args


def main() -> int:
    args = parse_args()
    codex_home = Path(
        args.codex_home or os.environ.get("CODEX_HOME") or (Path.home() / ".codex")
    ).expanduser()
    roles = tuple(args.roles) if args.roles else DEFAULT_ROLES
    receipts = [Path(item) for item in args.receipts] if args.receipts else None
    try:
        report, exit_code = inspect_report(
            codex_home,
            roles,
            args.profile,
            args.check_local_router,
            receipts,
            args.session_id,
            args.receipt_max_age_seconds,
        )
    except KeyboardInterrupt:
        report = envelope(
            "unknown",
            None,
            make_provenance(roles, [], []),
            [],
            {"code": "interrupted", "message": "Preflight was interrupted."},
        )
        exit_code = 130
    except Exception as exc:  # redacted internal failure report
        report = envelope(
            "unknown",
            None,
            make_provenance(roles, [], []),
            [unavailable_role_record(role_id, ["internal_error"]) for role_id in roles],
            {
                "code": "internal_error",
                "message": f"Preflight failed unexpectedly ({type(exc).__name__}).",
            },
        )
        exit_code = 1
    sys.stdout.write(json.dumps(report, indent=2) + "\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
