from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).with_name("router_preflight.py")
SPEC = importlib.util.spec_from_file_location("router_preflight", SCRIPT)
router_preflight = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(router_preflight)


def make_codex_home(tmp_path: Path, version: str = "v2") -> Path:
    codex_home = tmp_path / ".codex"
    agents_dir = codex_home / "agents"
    agents_dir.mkdir(parents=True)
    catalog = {
        "models": [
            {
                "slug": router_preflight.ROUTE,
                "multi_agent_version": version,
                "supported_reasoning_levels": ["low", "high"],
            }
        ]
    }
    (codex_home / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
    config_lines = [
        'model_provider = "codex_router"',
        'model_catalog_json = "catalog.json"',
        "",
        "[model_providers.codex_router]",
        'base_url = "http://127.0.0.1:43123/v1"',
    ]
    for agent_id in router_preflight.AGENT_IDS:
        config_lines.extend(
            [
                "",
                f"[agents.{agent_id}]",
                f'description = "{agent_id}"',
                f'config_file = "./agents/{agent_id}.toml"',
            ]
        )
        effort = "high" if agent_id == "implementer-deepseek" else "low"
        agent_profile = (
            f'name = "{agent_id}"\n'
            f'model = "{router_preflight.ROUTE}"\n'
            f'model_reasoning_effort = "{effort}"\n'
        )
        (agents_dir / f"{agent_id}.toml").write_text(agent_profile, encoding="utf-8")
    (codex_home / "config.toml").write_text("\n".join(config_lines) + "\n", encoding="utf-8")
    return codex_home


def test_v2_router_route_is_ready_for_runtime_probe_only(tmp_path: Path) -> None:
    codex_home = make_codex_home(tmp_path)

    report = router_preflight.inspect(codex_home)

    assert report["status"] == "ready_for_runtime_probe"
    assert report["available_agents"] == list(router_preflight.AGENT_IDS)
    assert report["runtime_verified"] is False
    assert report["inference_request_made"] is False


def test_v1_route_blocks_every_deepseek_agent(tmp_path: Path) -> None:
    codex_home = make_codex_home(tmp_path, version="v1")

    report = router_preflight.inspect(codex_home)

    assert report["status"] == "unavailable"
    assert report["available_agents"] == []
    assert all(not item["available"] for item in report["agents"].values())
    assert any("multi_agent_version = v2" in reason for reason in report["reasons"])


def test_vendor_model_id_and_direct_provider_are_rejected_for_role(tmp_path: Path) -> None:
    codex_home = make_codex_home(tmp_path)
    profile = codex_home / "agents" / "scout-deepseek.toml"
    profile.write_text(
        'name = "scout-deepseek"\nmodel = "deepseek-flash"\nmodel_provider = "deepseek"\n',
        encoding="utf-8",
    )

    report = router_preflight.inspect(codex_home)

    assert report["agents"]["scout-deepseek"]["available"] is False
    assert any("route slug" in reason for reason in report["agents"]["scout-deepseek"]["reasons"])
    assert any("overrides model_provider" in reason for reason in report["agents"]["scout-deepseek"]["reasons"])
    assert "scout-deepseek" not in report["available_agents"]


def test_direct_provider_endpoint_is_not_a_router(tmp_path: Path) -> None:
    codex_home = make_codex_home(tmp_path)
    config_path = codex_home / "config.toml"
    config = config_path.read_text(encoding="utf-8").replace(
        "http://127.0.0.1:43123/v1", "https://api.deepseek.com"
    )
    config_path.write_text(config, encoding="utf-8")

    report = router_preflight.inspect(codex_home)

    assert report["status"] == "unavailable"
    assert report["router_provider_configured"] is False
    assert report["available_agents"] == []


def test_router_url_requires_loopback_and_accepts_default_port() -> None:
    assert router_preflight.is_router_url("http://localhost/v1")
    assert router_preflight.is_router_url("http://127.0.0.1:43123/v1")
    assert not router_preflight.is_router_url("https://api.deepseek.com/v1")


def test_local_catalog_check_reads_route_without_auth_or_proxy(monkeypatch) -> None:
    calls = []

    class Response:
        def read(self, limit):
            assert limit == router_preflight.MAX_LIVE_CATALOG_BYTES + 1
            return json.dumps([{"id": router_preflight.ROUTE}]).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class Opener:
        def open(self, request, timeout):
            calls.append((request.full_url, request.get_header("Authorization"), timeout))
            return Response()

    monkeypatch.setattr(router_preflight.urllib.request, "build_opener", lambda *handlers: Opener())

    router_preflight.check_local_catalog("http://127.0.0.1:43123/v1")

    assert calls == [("http://127.0.0.1:43123/v1/models", None, 5)]
