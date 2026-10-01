from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

SCRIPT = Path(__file__).with_name("router_preflight.py")
SPEC = importlib.util.spec_from_file_location("router_preflight", SCRIPT)
router_preflight = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(router_preflight)

ROUTER_URL = "http://127.0.0.1:10101/v1"
DEEPSEEK_SLUG = "deepseek/deepseek-flash"
OLD_ROUTE = "deepseek/deepseek-v4.1-flash"
RECEIPT_NOW = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)

CATALOG_ROWS = [
    {
        "slug": "gpt-6.1-sol",
        "multi_agent_version": "v1",
        "opencodex_multi_agent_version_origin": "v2",
        "opencodex_capability_provenance": None,
    },
    {
        "slug": "gpt-6-astra",
        "multi_agent_version": "v1",
        "opencodex_multi_agent_version_origin": "v2",
        "opencodex_capability_provenance": None,
    },
    {
        "slug": "deepseek/deepseek-v4-flash",
        "multi_agent_version": "v1",
        "opencodex_capability_provenance": {
            "provider": "deepseek",
            "model_id": "deepseek-v4-flash",
        },
    },
    {
        "slug": DEEPSEEK_SLUG,
        "multi_agent_version": "v1",
        "opencodex_multi_agent_version_origin": "v2",
        "opencodex_capability_provenance": {
            "provider": "deepseek",
            "model_id": "deepseek-flash",
            "context_window": 1_000_000,
            "input_modalities": ["text"],
        },
    },
]

FIXTURE_ROLES = {
    "scout": {"model": "gpt-6.1-sol"},
    "implementer": {"model": "gpt-6-astra"},
    "scout-deepseek": {"model": DEEPSEEK_SLUG, "provider": "deepseek"},
    "codebase-memory-scout": {"model": DEEPSEEK_SLUG},
}


def write_home(
    tmp_path,
    *,
    rows=None,
    roles=None,
    multi_agent=True,
    multi_agent_v2=False,
    catalog_name="catalog.json",
    write_catalog=True,
    extra_config="",
):
    """Build a Codex home shaped like the inspected OpenCodex configuration."""
    codex_home = tmp_path / ".codex"
    agents_dir = codex_home / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    roles = FIXTURE_ROLES if roles is None else roles
    if write_catalog:
        payload = {"models": CATALOG_ROWS if rows is None else rows}
        (codex_home / catalog_name).write_text(json.dumps(payload), encoding="utf-8")
    lines = [
        'model = "deepseek/deepseek-flash"',
        'model_reasoning_effort = "high"',
        'openai_base_url = "' + ROUTER_URL + '"',
    ]
    if catalog_name:
        lines.append('model_catalog_json = "' + catalog_name + '"')
    lines += [
        "",
        "[features]",
        "multi_agent = " + ("true" if multi_agent else "false"),
        "",
        "[features.multi_agent_v2]",
        "enabled = " + ("true" if multi_agent_v2 else "false"),
        "",
        "[model_providers.deepseek]",
        'name = "DeepSeek"',
        'base_url = "https://api.deepseek.com"',
        "",
    ]
    for role_id in roles:
        lines += [
            "[agents." + role_id + "]",
            'description = "' + role_id + '"',
            'config_file = "./agents/' + role_id + '.toml"',
            "",
        ]
    if extra_config:
        lines.append(extra_config)
    (codex_home / "config.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for role_id, spec in roles.items():
        if spec.get("raw") is not None:
            body = [spec["raw"]]
        else:
            body = ['name = "' + role_id + '"']
            if spec.get("model"):
                body.append('model = "' + spec["model"] + '"')
            if spec.get("provider"):
                body.append('model_provider = "' + spec["provider"] + '"')
            if spec.get("effort"):
                body.append('model_reasoning_effort = "' + spec["effort"] + '"')
        (agents_dir / (role_id + ".toml")).write_text("\n".join(body) + "\n", encoding="utf-8")
    return codex_home


def records_of(report):
    return {record["role_id"]: record for record in report["roles"]}


def write_receipt(
    tmp_path,
    codex_home,
    *,
    role_id="scout",
    slug=None,
    upstream=None,
    upstream_provider="deepseek",
    route_decision="router",
    session_id="session-1",
    observed_at="2026-10-01T00:00:00Z",
    schema="runtime_receipt/1",
    name="receipt.json",
    bindings=None,
):
    """Write a sanitized passive receipt bound to the current fixture bytes."""

    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    default_slug = FIXTURE_ROLES[role_id]["model"]
    requested_slug = default_slug if slug is None else slug
    default_upstream = "deepseek-flash" if requested_slug == DEEPSEEK_SLUG else requested_slug
    bound = {
        "config_sha256": digest(codex_home / "config.toml"),
        "catalog_sha256": digest(codex_home / "catalog.json"),
        "profile_sha256": digest(codex_home / "agents" / (role_id + ".toml")),
    }
    bound.update(bindings or {})
    document = {
        "schema_version": schema,
        "role_id": role_id,
        "session_id": session_id,
        "request_id": "request-1",
        "requested_slug": requested_slug,
        "route_decision": route_decision,
        "upstream_provider": upstream_provider,
        "upstream_model": default_upstream if upstream is None else upstream,
        "observed_at": observed_at,
        "bindings": bound,
        "source": "sanitized fixture",
    }
    path = tmp_path / name
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_receipt_verifies_a_role_whose_bindings_match(tmp_path):
    roles = {"scout": {"model": DEEPSEEK_SLUG}}
    codex_home = write_home(tmp_path, roles=roles)
    receipt = write_receipt(
        tmp_path,
        codex_home,
        slug=DEEPSEEK_SLUG,
        upstream="deepseek-flash",
        observed_at="2026-10-01T11:00:00Z",
    )

    report, exit_code = router_preflight.inspect_report(
        codex_home,
        ("scout",),
        receipts=[receipt],
        session_id="session-1",
        now=RECEIPT_NOW,
    )

    assert exit_code == 0
    assert report["error"] is None
    assert report["provenance"]["requirements"] == ["static", "runtime"]
    assert "receipt.json" in report["provenance"]["inputs"]
    record = records_of(report)["scout"]
    assert record["evidence"]["runtime_route"] == "verified"
    assert record["reason_codes"] == []
    assert record["available"] is True
    attribution = record["delegation_evidence"]["passive_child_evidence"]
    assert attribution == {
        "session_id": "session-1",
        "request_id": "request-1",
        "observed_at": "2026-10-01T11:00:00Z",
        "requested_slug": DEEPSEEK_SLUG,
        "route_decision": "router",
        "upstream_provider": "deepseek",
        "upstream_model": "deepseek-flash",
        "attribution": "routing_evidence_only",
    }


def test_receipt_is_stale_after_the_profile_or_config_changes(tmp_path):
    roles = {"scout": {"model": DEEPSEEK_SLUG}}
    codex_home = write_home(tmp_path, roles=roles)
    receipt = write_receipt(tmp_path, codex_home, slug=DEEPSEEK_SLUG)
    report, _ = router_preflight.inspect_report(
        codex_home,
        ("scout",),
        receipts=[receipt],
        session_id="session-1",
        now=RECEIPT_NOW,
    )
    assert records_of(report)["scout"]["evidence"]["runtime_route"] == "verified"

    profile = codex_home / "agents" / "scout.toml"
    profile.write_text(profile.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    report, _ = router_preflight.inspect_report(
        codex_home,
        ("scout",),
        receipts=[receipt],
        session_id="session-1",
        now=RECEIPT_NOW,
    )
    record = records_of(report)["scout"]
    assert record["evidence"]["runtime_route"] == "unverified"
    assert "receipt_stale" in record["reason_codes"]
    assert record["available"] is False

    config = codex_home / "config.toml"
    fresh = write_receipt(tmp_path, codex_home, slug=DEEPSEEK_SLUG, name="fresh.json")
    config.write_text(config.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    report, _ = router_preflight.inspect_report(
        codex_home,
        ("scout",),
        receipts=[fresh],
        session_id="session-1",
        now=RECEIPT_NOW,
    )
    assert "receipt_stale" in records_of(report)["scout"]["reason_codes"]


def test_receipt_for_another_role_is_ignored(tmp_path):
    roles = {
        "scout": {"model": DEEPSEEK_SLUG},
        "implementer": {"model": DEEPSEEK_SLUG},
    }
    codex_home = write_home(tmp_path, roles=roles)
    receipt = write_receipt(
        tmp_path,
        codex_home,
        role_id="implementer",
        slug=DEEPSEEK_SLUG,
    )

    report, _ = router_preflight.inspect_report(
        codex_home,
        ("scout",),
        receipts=[receipt],
        session_id="session-1",
        now=RECEIPT_NOW,
    )

    record = records_of(report)["scout"]
    assert record["evidence"]["runtime_route"] == "unverified"
    assert record["reason_codes"] == []
    assert record["delegation_evidence"]["passive_child_evidence"] is None
    assert record["available"] is False


def test_receipt_slug_and_upstream_mismatches_are_reported(tmp_path):
    roles = {"scout": {"model": DEEPSEEK_SLUG}}
    codex_home = write_home(tmp_path, roles=roles)
    wrong_slug = write_receipt(tmp_path, codex_home, slug="gpt-6-astra", name="slug.json")

    report, _ = router_preflight.inspect_report(
        codex_home,
        ("scout",),
        receipts=[wrong_slug],
        session_id="session-1",
        now=RECEIPT_NOW,
    )
    record = records_of(report)["scout"]
    assert record["evidence"]["runtime_route"] == "unverified"
    assert "receipt_mismatch" in record["reason_codes"]

    wrong_upstream = write_receipt(
        tmp_path,
        codex_home,
        slug=DEEPSEEK_SLUG,
        upstream=DEEPSEEK_SLUG,
        name="upstream.json",
    )
    report, _ = router_preflight.inspect_report(
        codex_home,
        ("scout",),
        receipts=[wrong_upstream],
        session_id="session-1",
        now=RECEIPT_NOW,
    )
    record = records_of(report)["scout"]
    assert record["evidence"]["runtime_route"] == "mismatch"
    assert "receipt_mismatch" in record["reason_codes"]
    assert record["available"] is False

    wrong_provider = write_receipt(
        tmp_path,
        codex_home,
        slug=DEEPSEEK_SLUG,
        upstream_provider="other-provider",
        name="provider.json",
    )
    report, _ = router_preflight.inspect_report(
        codex_home,
        ("scout",),
        receipts=[wrong_provider],
        session_id="session-1",
        now=RECEIPT_NOW,
    )
    record = records_of(report)["scout"]
    assert record["evidence"]["runtime_route"] == "mismatch"
    assert "receipt_mismatch" in record["reason_codes"]


def test_route_decision_must_match_the_resolved_route_class(tmp_path):
    codex_home = write_home(tmp_path)
    receipt = write_receipt(
        tmp_path,
        codex_home,
        role_id="scout-deepseek",
        route_decision="router",
        upstream=DEEPSEEK_SLUG,
    )

    report, _ = router_preflight.inspect_report(
        codex_home,
        ("scout-deepseek",),
        receipts=[receipt],
        session_id="session-1",
        now=RECEIPT_NOW,
    )

    record = records_of(report)["scout-deepseek"]
    assert record["endpoint_classification"] == "remote"
    assert record["evidence"]["runtime_route"] == "unverified"
    assert "receipt_mismatch" in record["reason_codes"]
    assert record["delegation_evidence"]["passive_child_evidence"] is None

    direct_receipt = write_receipt(
        tmp_path,
        codex_home,
        role_id="scout-deepseek",
        route_decision="direct",
        upstream=DEEPSEEK_SLUG,
        name="direct.json",
    )
    report, _ = router_preflight.inspect_report(
        codex_home,
        ("scout-deepseek",),
        receipts=[direct_receipt],
        session_id="session-1",
        now=RECEIPT_NOW,
    )
    assert records_of(report)["scout-deepseek"]["evidence"]["runtime_route"] == "verified"


def test_absent_router_provenance_never_guesses_an_upstream_mapping(tmp_path):
    codex_home = write_home(tmp_path)
    receipt = write_receipt(tmp_path, codex_home, upstream="gpt-6.1-sol")

    report, _ = router_preflight.inspect_report(
        codex_home,
        ("scout",),
        receipts=[receipt],
        session_id="session-1",
        now=RECEIPT_NOW,
    )

    record = records_of(report)["scout"]
    assert record["evidence"]["runtime_route"] == "unverified"
    assert "router_mapping_unknown" in record["reason_codes"]
    assert "receipt_mismatch" not in record["reason_codes"]
    assert record["delegation_evidence"]["passive_child_evidence"] is None


def test_newest_verified_receipt_wins_and_mismatch_outranks_it(tmp_path):
    roles = {"scout": {"model": DEEPSEEK_SLUG}}
    codex_home = write_home(tmp_path, roles=roles)
    stale = write_receipt(
        tmp_path,
        codex_home,
        slug=DEEPSEEK_SLUG,
        observed_at="2026-10-01T00:00:00Z",
        bindings={"profile_sha256": "0" * 64},
        name="stale.json",
    )
    fresh = write_receipt(
        tmp_path,
        codex_home,
        slug=DEEPSEEK_SLUG,
        observed_at="2026-10-01T01:00:00Z",
        name="fresh.json",
    )

    report, _ = router_preflight.inspect_report(
        codex_home,
        ("scout",),
        receipts=[stale, fresh],
        session_id="session-1",
        now=RECEIPT_NOW,
    )
    record = records_of(report)["scout"]
    assert record["evidence"]["runtime_route"] == "verified"
    assert (
        record["delegation_evidence"]["passive_child_evidence"]["observed_at"]
        == "2026-10-01T01:00:00Z"
    )

    mismatch = write_receipt(
        tmp_path,
        codex_home,
        slug=DEEPSEEK_SLUG,
        observed_at="2026-10-01T02:00:00Z",
        upstream="nope",
        name="m.json",
    )
    report, _ = router_preflight.inspect_report(
        codex_home,
        ("scout",),
        receipts=[mismatch, fresh],
        session_id="session-1",
        now=RECEIPT_NOW,
    )
    assert records_of(report)["scout"]["evidence"]["runtime_route"] == "mismatch"
    assert records_of(report)["scout"]["available"] is False


def test_other_session_receipt_is_history_only(tmp_path):
    roles = {"scout": {"model": DEEPSEEK_SLUG}}
    codex_home = write_home(tmp_path, roles=roles)
    receipt = write_receipt(
        tmp_path,
        codex_home,
        slug=DEEPSEEK_SLUG,
        session_id="session-2",
    )

    report, _ = router_preflight.inspect_report(
        codex_home,
        ("scout",),
        receipts=[receipt],
        session_id="session-1",
        now=RECEIPT_NOW,
    )

    record = records_of(report)["scout"]
    assert record["evidence"]["runtime_route"] == "unverified"
    assert "receipt_other_session" in record["reason_codes"]
    assert record["delegation_evidence"]["passive_child_evidence"] is None
    assert record["available"] is False


def test_expired_receipt_is_history_only_and_window_is_configurable(tmp_path):
    roles = {"scout": {"model": DEEPSEEK_SLUG}}
    codex_home = write_home(tmp_path, roles=roles)
    receipt = write_receipt(
        tmp_path,
        codex_home,
        slug=DEEPSEEK_SLUG,
        observed_at="2026-10-01T10:00:00Z",
    )

    report, _ = router_preflight.inspect_report(
        codex_home,
        ("scout",),
        receipts=[receipt],
        session_id="session-1",
        receipt_max_age_seconds=3_600,
        now=RECEIPT_NOW,
    )
    expired = records_of(report)["scout"]
    assert expired["evidence"]["runtime_route"] == "unverified"
    assert "receipt_expired" in expired["reason_codes"]
    assert expired["delegation_evidence"]["passive_child_evidence"] is None

    report, _ = router_preflight.inspect_report(
        codex_home,
        ("scout",),
        receipts=[receipt],
        session_id="session-1",
        receipt_max_age_seconds=10_800,
        now=RECEIPT_NOW,
    )
    current = records_of(report)["scout"]
    assert current["evidence"]["runtime_route"] == "verified"
    assert "receipt_expired" not in current["reason_codes"]


def test_invalid_receipt_is_an_input_error(tmp_path):
    codex_home = write_home(tmp_path)
    unparseable = tmp_path / "unparseable.json"
    unparseable.write_text("{not json", encoding="utf-8")

    report, exit_code = router_preflight.inspect_report(
        codex_home, ("scout",), receipts=[unparseable], session_id="session-1"
    )

    assert exit_code == 1
    assert report["error"]["code"] == "receipt_invalid"
    assert [record["role_id"] for record in report["roles"]] == ["scout"]
    assert records_of(report)["scout"]["evidence"]["runtime_route"] == "unverified"
    assert str(unparseable) not in json.dumps(report)

    wrong_schema = write_receipt(tmp_path, codex_home, schema="runtime_receipt/2", name="v2.json")
    report, exit_code = router_preflight.inspect_report(
        codex_home, ("scout",), receipts=[wrong_schema], session_id="session-1"
    )
    assert exit_code == 1
    assert report["error"]["code"] == "receipt_invalid"

    bad_timestamp = write_receipt(
        tmp_path,
        codex_home,
        observed_at="not-a-timestamp",
        name="bad-timestamp.json",
    )
    report, exit_code = router_preflight.inspect_report(
        codex_home, ("scout",), receipts=[bad_timestamp], session_id="session-1"
    )
    assert exit_code == 1
    assert report["error"]["code"] == "receipt_invalid"

    bad_route = write_receipt(
        tmp_path,
        codex_home,
        route_decision="router:loopback",
        name="bad-route.json",
    )
    report, exit_code = router_preflight.inspect_report(
        codex_home, ("scout",), receipts=[bad_route], session_id="session-1"
    )
    assert exit_code == 1
    assert report["error"]["code"] == "receipt_invalid"


def test_receipt_without_session_id_is_an_input_error(tmp_path, monkeypatch, capsys):
    codex_home = write_home(tmp_path)
    receipt = write_receipt(tmp_path, codex_home)
    monkeypatch.setattr(
        router_preflight.sys,
        "argv",
        [
            "router_preflight.py",
            "--codex-home",
            str(codex_home),
            "--role",
            "scout",
            "--receipt",
            str(receipt),
        ],
    )

    assert router_preflight.main() == 1
    report = json.loads(capsys.readouterr().out)
    assert report["error"]["code"] == "receipt_invalid"
    assert records_of(report)["scout"]["evidence"]["runtime_route"] == "unverified"


def test_without_a_receipt_behaviour_is_unchanged(tmp_path):
    codex_home = write_home(tmp_path)

    report, exit_code = router_preflight.inspect_report(codex_home, ("scout",), receipts=None)

    record = records_of(report)["scout"]
    assert exit_code == 0
    assert report["provenance"]["requirements"] == ["static"]
    assert record["evidence"]["runtime_route"] == "unverified"
    assert record["delegation_evidence"]["passive_child_evidence"] is None
    assert [code for code in record["reason_codes"] if code.startswith("receipt_")] == []
    assert record["available"] is True
    wrapper = router_preflight.inspect(codex_home, ("scout",))
    wrapper.pop("provenance")
    assert wrapper == {key: value for key, value in report.items() if key != "provenance"}


def test_cli_receipt_flag_is_repeatable(monkeypatch):
    monkeypatch.setattr(
        router_preflight.sys,
        "argv",
        [
            "router_preflight.py",
            "--receipt",
            "a.json",
            "--receipt",
            "b.json",
            "--session-id",
            "session-1",
            "--receipt-max-age-seconds",
            "3600",
        ],
    )

    args = router_preflight.parse_args()

    assert args.receipts == ["a.json", "b.json"]
    assert args.session_id == "session-1"
    assert args.receipt_max_age_seconds == 3_600
    assert args.roles is None


def test_inspected_opencodex_fixture_is_eligible_per_role(tmp_path):
    codex_home = write_home(tmp_path)

    report, exit_code = router_preflight.inspect_report(
        codex_home, ("scout", "scout-deepseek", "codebase-memory-scout")
    )

    assert exit_code == 0
    assert report["schema_version"] == "preflight_report/1"
    assert report["bootstrap"] == "ready"
    assert report["bootstrap_failure"] is None
    assert report["error"] is None
    assert report["provenance"]["requirements"] == ["static"]
    records = records_of(report)
    assert set(records) == {"scout", "scout-deepseek", "codebase-memory-scout"}
    for record in records.values():
        assert record["evidence"] == {
            "bootstrap": "ready",
            "configuration": "consistent",
            "catalog": "present",
            "delegation": "supported",
            "endpoint": "unchecked",
            "runtime_route": "unverified",
        }
        assert record["available"] is True
        assert record["delegation_evidence"]["host_interface"] == "v1"
        assert record["delegation_evidence"]["catalog_declared_version"] == "v1"
        assert record["reason_codes"] == []
    assert records["scout"]["endpoint_classification"] == "loopback"
    assert records["scout"]["profile_path"] == "agents/scout.toml"
    assert records["codebase-memory-scout"]["effective_values"] == {
        "model": DEEPSEEK_SLUG,
        "model_provider": "openai",
    }


def test_v1_advertisement_and_a_non_legacy_slug_are_not_rejections(tmp_path):
    rows = [{"slug": "deepseek/deepseek-v4-flash", "multi_agent_version": "v1"}]
    roles = {"scout-deepseek": {"model": "deepseek/deepseek-v4-flash", "provider": "deepseek"}}
    codex_home = write_home(tmp_path, rows=rows, roles=roles)

    report, exit_code = router_preflight.inspect_report(codex_home, ("scout-deepseek",))

    assert exit_code == 0
    record = records_of(report)["scout-deepseek"]
    assert record["available"] is True
    assert record["evidence"]["delegation"] == "supported"
    assert "delegation_interface_mismatch" not in record["reason_codes"]
    assert not any("v2" in code for code in record["reason_codes"])
    assert OLD_ROUTE not in json.dumps(report)


def test_explicit_provider_override_is_evaluated_not_banned(tmp_path):
    codex_home = write_home(tmp_path)

    report, _ = router_preflight.inspect_report(codex_home, ("scout", "scout-deepseek"))
    records = records_of(report)

    override = records["scout-deepseek"]
    assert override["declared_model_slug"] == DEEPSEEK_SLUG
    assert override["declared_overrides"] == {"model": DEEPSEEK_SLUG, "model_provider": "deepseek"}
    assert override["effective_values"] == {"model": DEEPSEEK_SLUG, "model_provider": "deepseek"}
    assert override["codex_provider_identity"] == {"key": "deepseek", "label": "DeepSeek"}
    assert override["endpoint_classification"] == "remote"
    assert override["evidence"]["configuration"] == "consistent"
    assert override["reason_codes"] == []
    assert records["scout"]["declared_overrides"] == {"model": "gpt-6.1-sol", "model_provider": None}


def test_missing_exact_slug_is_not_normalized_to_a_vendor_prefixed_entry(tmp_path):
    roles = {"scout-deepseek": {"model": "deepseek-flash", "provider": "deepseek"}}
    codex_home = write_home(tmp_path, roles=roles)

    report, exit_code = router_preflight.inspect_report(codex_home, ("scout-deepseek",))

    assert exit_code == 0
    record = records_of(report)["scout-deepseek"]
    assert record["declared_model_slug"] == "deepseek-flash"
    assert record["effective_values"]["model"] == "deepseek-flash"
    assert record["evidence"]["catalog"] == "missing"
    assert "catalog_entry_missing" in record["reason_codes"]
    assert record["evidence"]["delegation"] == "unknown"
    assert record["available"] is False


def test_ambiguous_exact_slug_is_reported(tmp_path):
    rows = CATALOG_ROWS + [{"slug": DEEPSEEK_SLUG, "multi_agent_version": "v1"}]
    roles = {"scout-deepseek": {"model": DEEPSEEK_SLUG}}
    codex_home = write_home(tmp_path, rows=rows, roles=roles)

    report, _ = router_preflight.inspect_report(codex_home, ("scout-deepseek",))
    record = records_of(report)["scout-deepseek"]

    assert record["evidence"]["catalog"] == "ambiguous"
    assert "catalog_entry_ambiguous" in record["reason_codes"]
    assert record["available"] is False


def test_unregistered_identity_is_reported_without_crashing(tmp_path):
    codex_home = write_home(tmp_path)

    report, exit_code = router_preflight.inspect_report(codex_home, ("ghost",))

    assert exit_code == 0
    record = records_of(report)["ghost"]
    assert record["reason_codes"] == ["role_not_registered"]
    assert record["profile_path"] is None
    assert record["profile_hash"] is None
    assert record["declared_overrides"] is None
    assert record["evidence"]["configuration"] == "conflict"
    assert record["available"] is False


def test_unreadable_profile_and_inherited_model(tmp_path):
    roles = {
        "scout": {"raw": 'name = "scout"'},
        "ghost": {"model": "gpt-6.1-sol"},
    }
    codex_home = write_home(tmp_path, roles=roles)
    (codex_home / "agents" / "ghost.toml").unlink()

    report, _ = router_preflight.inspect_report(codex_home, ("scout", "ghost"))
    records = records_of(report)

    inherited = records["scout"]
    assert inherited["declared_overrides"] == {"model": None, "model_provider": None}
    assert inherited["effective_values"] == {"model": "deepseek/deepseek-flash", "model_provider": "openai"}
    assert inherited["evidence"]["catalog"] == "present"
    assert inherited["available"] is True

    missing = records["ghost"]
    assert "profile_missing" in missing["reason_codes"]
    assert missing["profile_path"] is None
    assert missing["declared_overrides"] is None
    assert missing["evidence"]["configuration"] == "unknown"
    assert missing["available"] is False


def test_version_mismatch_is_unknown_not_blocked(tmp_path):
    rows = [{"slug": DEEPSEEK_SLUG, "multi_agent_version": "v2"}]
    roles = {"codebase-memory-scout": {"model": DEEPSEEK_SLUG}}
    codex_home = write_home(tmp_path, rows=rows, roles=roles)

    report, _ = router_preflight.inspect_report(codex_home, ("codebase-memory-scout",))
    record = records_of(report)["codebase-memory-scout"]

    assert record["evidence"]["delegation"] == "unknown"
    assert "delegation_interface_mismatch" in record["reason_codes"]
    assert record["available"] is False


def test_disabled_subagents_block_delegation_for_every_role(tmp_path):
    codex_home = write_home(tmp_path, multi_agent=False)

    report, exit_code = router_preflight.inspect_report(codex_home, ("scout", "scout-deepseek"))

    assert exit_code == 0
    for record in records_of(report).values():
        assert record["evidence"]["delegation"] == "unsupported"
        assert "delegation_disabled" in record["reason_codes"]
        assert record["available"] is False


def test_bootstrap_blocked_when_tomllib_is_unavailable(tmp_path, monkeypatch):
    codex_home = write_home(tmp_path)
    monkeypatch.setattr(router_preflight, "tomllib", None)

    report, exit_code = router_preflight.inspect_report(codex_home, ("scout",))

    assert exit_code == 1
    assert report["bootstrap"] == "blocked"
    assert report["bootstrap_failure"] == "dependency_unavailable"
    assert report["roles"] == []
    assert report["error"]["code"] == "bootstrap_blocked"


def test_check_local_router_records_endpoint_evidence(tmp_path, monkeypatch):
    codex_home = write_home(tmp_path)
    calls = []

    class Response:
        def read(self, limit):
            assert limit == router_preflight.MAX_LIVE_CATALOG_BYTES + 1
            return json.dumps([{"slug": "gpt-6.1-sol"}, {"slug": DEEPSEEK_SLUG}]).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class Opener:
        def open(self, request, timeout):
            calls.append((request.full_url, request.get_header("Authorization"), timeout))
            return Response()

    monkeypatch.setattr(router_preflight.urllib.request, "build_opener", lambda *handlers: Opener())

    report, exit_code = router_preflight.inspect_report(
        codex_home, ("scout", "scout-deepseek"), check_live=True
    )

    assert exit_code == 0
    assert report["provenance"]["requirements"] == ["static", "endpoint"]
    records = records_of(report)
    router_role = records["scout"]
    assert router_role["evidence"]["endpoint"] == "reachable"
    assert router_role["router_evidence"] == {
        "classification": "loopback",
        "product_identity": "unverified",
        "live_catalog_checked": True,
        "live_route_visible": True,
    }
    assert router_role["available"] is True
    direct_role = records["scout-deepseek"]
    assert direct_role["evidence"]["endpoint"] == "unchecked"
    assert direct_role["router_evidence"]["live_catalog_checked"] is False
    assert calls == [(ROUTER_URL + "/models", None, 5)]


def test_check_local_router_failure_marks_the_endpoint_unreachable(tmp_path, monkeypatch):
    codex_home = write_home(tmp_path)

    class Opener:
        def open(self, request, timeout):
            raise router_preflight.urllib.error.URLError("refused")

    monkeypatch.setattr(router_preflight.urllib.request, "build_opener", lambda *handlers: Opener())

    report, _ = router_preflight.inspect_report(codex_home, ("scout",), check_live=True)
    record = records_of(report)["scout"]

    assert record["evidence"]["endpoint"] == "unreachable"
    assert "endpoint_unreachable" in record["reason_codes"]
    assert record["available"] is False


def test_static_preflight_makes_no_request_and_redacts_host_details(tmp_path, monkeypatch):
    codex_home = write_home(tmp_path)

    def explode(*args, **kwargs):
        raise AssertionError("static preflight must not open a network connection")

    monkeypatch.setattr(router_preflight.urllib.request, "build_opener", explode)

    report, _ = router_preflight.inspect_report(codex_home, ("scout", "scout-deepseek"))
    text = json.dumps(report)

    assert "C:\\" not in text
    assert str(codex_home) not in text
    assert "api.deepseek.com" not in text
    assert ROUTER_URL not in text
    assert "http://" not in text and "https://" not in text
    for record in report["roles"]:
        assert len(record["profile_hash"]) == 64
        assert record["profile_path"] in {"agents/scout.toml", "agents/scout-deepseek.toml"}
        assert record["registration_source"] == "config.toml:[agents." + record["role_id"] + "]"


def test_default_roles_and_provenance_inputs(tmp_path):
    codex_home = write_home(tmp_path)

    report, _ = router_preflight.inspect_report(codex_home, ())

    assert report["provenance"]["roles"] == ["scout", "implementer", "tester"]
    assert [record["role_id"] for record in report["roles"]] == ["scout", "implementer", "tester"]
    assert report["provenance"]["inputs"] == [
        "config.toml",
        "catalog.json",
        "agents/scout.toml",
        "agents/implementer.toml",
    ]
    assert report["provenance"]["operation"] == "preflight"
    assert report["provenance"]["interpreter"].count(".") >= 1


def test_cli_role_flag_is_repeatable_and_validated(monkeypatch):
    monkeypatch.setattr(
        router_preflight.sys, "argv", ["router_preflight.py", "--role", "scout", "--role", "scout-deepseek"]
    )
    args = router_preflight.parse_args()
    assert args.roles == ["scout", "scout-deepseek"]
    assert args.check_local_router is False

    monkeypatch.setattr(router_preflight.sys, "argv", ["router_preflight.py", "--role", "bad id"])
    with pytest.raises(SystemExit) as error:
        router_preflight.parse_args()
    assert error.value.code == 2


def test_interrupt_and_internal_failure_exit_codes(tmp_path, monkeypatch, capsys):
    codex_home = write_home(tmp_path)
    monkeypatch.setattr(
        router_preflight.sys, "argv", ["router_preflight.py", "--codex-home", str(codex_home)]
    )

    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(router_preflight, "inspect_report", interrupted)
    assert router_preflight.main() == 130
    interrupted_report = json.loads(capsys.readouterr().out)
    assert interrupted_report["error"]["code"] == "interrupted"
    assert interrupted_report["roles"] == []

    def boom(*args, **kwargs):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(router_preflight, "inspect_report", boom)
    assert router_preflight.main() == 1
    failed_report = json.loads(capsys.readouterr().out)
    assert failed_report["error"]["code"] == "internal_error"
    assert "kaboom" not in json.dumps(failed_report)
    assert [record["reason_codes"] for record in failed_report["roles"]] == [
        ["internal_error"],
        ["internal_error"],
        ["internal_error"],
    ]
