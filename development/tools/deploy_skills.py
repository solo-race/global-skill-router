#!/usr/bin/env python3
"""Build and deploy the routed global skill payload.

The source tree remains the development representation.  This tool assembles a
single ``global-skill-router`` directory with active modules under ``library/``
and a small, deterministic route index.  The default command is a read-only
plan; ``--apply`` is required to change a target skill root.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
import uuid
from pathlib import Path, PurePosixPath

import yaml

try:
    import validate_skills
except ModuleNotFoundError:  # pragma: no cover - exercised when imported by path
    import importlib.util

    _VALIDATOR_PATH = Path(__file__).with_name("validate_skills.py")
    _SPEC = importlib.util.spec_from_file_location("validate_skills", _VALIDATOR_PATH)
    validate_skills = importlib.util.module_from_spec(_SPEC)
    assert _SPEC.loader is not None
    _SPEC.loader.exec_module(validate_skills)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPO_ROOT / "development" / "skill" / "manifest.yaml"
ROUTER_NAME = "global-skill-router"
DEPLOYMENT_SCHEMA_VERSION = 1
SCENARIOS = ("win-access-vba", "win-android", "wsl-python")
SCENARIO_SELECTORS = {
    "win-access-vba": "windows host/tool mutation",
    "win-android": "windows android build/runtime",
    "wsl-python": "wsl python evidence/investigation",
}
ROUTE_INDEX_SCHEMA_VERSION = 4
LEGACY_ROUTE_INDEX_SCHEMA_VERSION = 1
LEGACY_ROUTE_INDEX_SCHEMA_V2 = 2
LEGACY_ROUTE_INDEX_SCHEMA_V3 = 3


class DeploymentError(RuntimeError):
    """A controlled deployment refusal or failed recovery."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_file_hashes(root: Path) -> dict[str, str]:
    files = sorted(path for path in root.rglob("*") if path.is_file())
    return {
        path.relative_to(root).as_posix(): _sha256(path)
        for path in files
        if path.name != "deployment-state.json"
    }


def _read_yaml(path: Path, label: str) -> object:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise DeploymentError(f"cannot read {label}: {exc}") from exc


def _write_yaml(path: Path, payload: object) -> None:
    path.write_text(
        yaml.safe_dump(
            payload,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        ),
        encoding="utf-8",
    )


def _route_path(value: object, label: str) -> PurePosixPath:
    """Validate a router-relative POSIX route path and return its parts."""

    if not isinstance(value, str) or not value.strip():
        raise DeploymentError(f"{label} must be a non-empty POSIX path")
    if "\\" in value or value.startswith("/") or len(value) >= 2 and value[1] == ":":
        raise DeploymentError(f"{label} must be router-relative POSIX path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise DeploymentError(f"{label} must not be absolute or contain dot segments: {value!r}")
    try:
        path.relative_to(PurePosixPath("_platform/routes"))
    except ValueError as exc:
        raise DeploymentError(f"{label} must stay under _platform/routes: {value!r}") from exc
    return path


def _library_skill_path(value: object, label: str) -> PurePosixPath:
    """Validate a router-relative direct library MODULE.md path."""

    if not isinstance(value, str) or not value.strip():
        raise DeploymentError(f"{label} must be a non-empty POSIX path")
    if "\\" in value or value.startswith("/") or len(value) >= 2 and value[1] == ":":
        raise DeploymentError(f"{label} must be router-relative POSIX path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise DeploymentError(f"{label} must not be absolute or contain dot segments: {value!r}")
    if len(path.parts) != 3 or path.parts[0] != "library" or path.parts[2] != "MODULE.md":
        raise DeploymentError(f"{label} must equal library/<module>/MODULE.md: {value!r}")
    return path


def _library_adapter_path(value: object, label: str, owner: str, name: str) -> PurePosixPath:
    """Validate a v3 router-relative adapter path for one module owner."""

    if not isinstance(value, str) or not value.strip():
        raise DeploymentError(f"{label} must be a non-empty POSIX path")
    if "\\" in value or value.startswith("/") or len(value) >= 2 and value[1] == ":":
        raise DeploymentError(f"{label} must be router-relative POSIX path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise DeploymentError(f"{label} must not be absolute or contain dot segments: {value!r}")
    expected = f"library/{owner}/adapters/{name}.md"
    if path.as_posix() != expected:
        raise DeploymentError(f"{label} must be {expected!r}")
    return path


def _validate_adapter_environment(adapter_path: Path, adapter_name: str, scenario: str) -> None:
    """Require a deployed adapter contract to declare the shard scenario."""

    frontmatter, _, parse_error = validate_skills._read_frontmatter_document(adapter_path)
    if parse_error or not isinstance(frontmatter, dict):
        detail = parse_error or "frontmatter must be a mapping"
        raise DeploymentError(
            f"route adapter frontmatter is invalid for {adapter_name}: {detail}"
        )
    environments = frontmatter.get("environments")
    if not isinstance(environments, list) or scenario not in environments:
        raise DeploymentError(
            f"route adapter {adapter_name} frontmatter environments do not include scenario {scenario!r}"
        )


def _validate_routing_fields(route: dict) -> None:
    if type(route.get("routing_priority")) is not int:
        raise DeploymentError("route routing_priority must be an integer")
    if route.get("routing_outcome") not in ("continue", "terminal"):
        raise DeploymentError("route routing_outcome must be continue or terminal")


def _validate_route_index(index: object, router_root: Path) -> set[str]:
    """Validate route-index v4, accepting v1/v2/v3 for installed-payload recovery."""

    if not isinstance(index, dict):
        raise DeploymentError("route index must be a mapping")
    schema_version = index.get("schema_version")
    if schema_version == LEGACY_ROUTE_INDEX_SCHEMA_VERSION:
        if set(index) != {"schema_version", "scenarios"}:
            raise DeploymentError("legacy route index must contain only schema_version and scenarios")
        global_routes = []
    elif schema_version in (
        LEGACY_ROUTE_INDEX_SCHEMA_V2, LEGACY_ROUTE_INDEX_SCHEMA_V3, ROUTE_INDEX_SCHEMA_VERSION
    ):
        if set(index) != {"schema_version", "global_routes", "scenarios"}:
            raise DeploymentError("route index must contain only schema_version, global_routes, and scenarios")
        global_routes = index.get("global_routes")
        if not isinstance(global_routes, list):
            raise DeploymentError("route index global_routes must be a list")
    else:
        raise DeploymentError("route index schema_version is invalid")

    routing_fields = {"routing_priority", "routing_outcome"} if schema_version == ROUTE_INDEX_SCHEMA_VERSION else set()
    global_names: set[str] = set()
    for item in global_routes:
        if not isinstance(item, dict) or set(item) != {"name", "selector", "skill_path"} | routing_fields:
            raise DeploymentError("global route fields are invalid")
        if routing_fields:
            _validate_routing_fields(item)
        name = item.get("name")
        if not isinstance(name, str) or not name.strip() or name in global_names:
            raise DeploymentError(f"route index has invalid or duplicate global route: {name!r}")
        selector = item.get("selector")
        if not isinstance(selector, str) or not selector.strip() or len(selector) > 180:
            raise DeploymentError(f"global route selector must be short and non-empty: {name!r}")
        skill_path = _library_skill_path(item.get("skill_path"), f"global route skill path for {name}")
        expected = f"library/{name}/MODULE.md"
        if skill_path.as_posix() != expected:
            raise DeploymentError(f"global route skill path for {name} must be {expected!r}")
        if not router_root.joinpath(*skill_path.parts).is_file():
            raise DeploymentError(f"global route skill path is missing: {skill_path.as_posix()}")
        global_names.add(name)

    scenarios = index.get("scenarios")
    if not isinstance(scenarios, list) or len(scenarios) != len(SCENARIOS):
        raise DeploymentError("route index scenarios must contain the fixed scenario vocabulary")

    seen_names: set[str] = set()
    declared_paths: set[str] = set()
    routes_dir = router_root / "_platform" / "routes"
    for item in scenarios:
        if not isinstance(item, dict) or set(item) != {"name", "shard", "selector"}:
            raise DeploymentError("route index scenario entries must contain name, shard, selector")
        name = item.get("name")
        if name not in SCENARIOS or name in seen_names:
            raise DeploymentError(f"route index has invalid or duplicate scenario: {name!r}")
        seen_names.add(name)
        selector = item.get("selector")
        if not isinstance(selector, str) or not selector.strip() or len(selector) > 96:
            raise DeploymentError(f"route index selector must be short and non-empty: {name!r}")
        path = _route_path(item.get("shard"), f"route index shard for {name}")
        expected = f"_platform/routes/{name}.yaml"
        if path.as_posix() != expected:
            raise DeploymentError(f"route index shard for {name} must be {expected!r}")
        declared_paths.add(path.as_posix())
        shard_path = router_root.joinpath(*path.parts)
        if not shard_path.is_file():
            raise DeploymentError(f"route index shard is missing: {path.as_posix()}")
        shard = _read_yaml(shard_path, path.as_posix())
        if not isinstance(shard, dict) or shard.get("scenario") != name or not isinstance(shard.get("skills"), list):
            raise DeploymentError(f"route shard structure is invalid: {path.as_posix()}")
        if schema_version in (LEGACY_ROUTE_INDEX_SCHEMA_V3, ROUTE_INDEX_SCHEMA_VERSION) and set(shard) != {"scenario", "skills"}:
            raise DeploymentError(f"route shard fields are invalid: {path.as_posix()}")
        candidate_names: set[str] = set()
        for candidate in shard["skills"]:
            if not isinstance(candidate, dict):
                raise DeploymentError(f"route candidate is invalid: {path.as_posix()}")
            candidate_name = candidate.get("name")
            if not isinstance(candidate_name, str) or not candidate_name.strip() or candidate_name in candidate_names:
                raise DeploymentError(f"route candidate has invalid or duplicate name: {candidate_name!r}")
            candidate_names.add(candidate_name)
            if candidate_name in global_names:
                raise DeploymentError(f"global route duplicated in scenario shard: {candidate_name!r}")
            skill_path = _library_skill_path(
                candidate.get("skill_path"),
                f"route skill path for {candidate_name}",
            )
            if not router_root.joinpath(*skill_path.parts).is_file():
                raise DeploymentError(f"route skill path is missing: {skill_path.as_posix()}")
            if candidate.get("status") != "active":
                raise DeploymentError(f"planned route candidate is executable: {candidate_name}")
            if schema_version in (LEGACY_ROUTE_INDEX_SCHEMA_VERSION, LEGACY_ROUTE_INDEX_SCHEMA_V2):
                continue
            if set(candidate) != {"name", "description", "skill_path", "status", "adapters"} | routing_fields:
                raise DeploymentError(
                    f"route candidate fields are invalid: {candidate_name!r}"
                )
            if routing_fields:
                _validate_routing_fields(candidate)
            expected_skill_path = f"library/{candidate_name}/MODULE.md"
            if skill_path.as_posix() != expected_skill_path:
                raise DeploymentError(
                    f"route skill path for {candidate_name} must be {expected_skill_path!r}"
                )
            description = candidate.get("description")
            if not isinstance(description, str) or not description.strip():
                raise DeploymentError(f"route candidate description is invalid: {candidate_name!r}")
            adapters = candidate.get("adapters")
            if not isinstance(adapters, list):
                raise DeploymentError(f"route candidate adapters must be a list: {candidate_name!r}")
            adapter_names: set[str] = set()
            for adapter in adapters:
                if not isinstance(adapter, dict) or set(adapter) != {
                    "name",
                    "description",
                    "adapter_path",
                    "status",
                }:
                    raise DeploymentError(
                        f"route adapter fields are invalid: {candidate_name!r}"
                    )
                adapter_name = adapter.get("name")
                if (
                    not isinstance(adapter_name, str)
                    or not adapter_name.strip()
                    or adapter_name in adapter_names
                ):
                    raise DeploymentError(
                        f"route adapter has invalid or duplicate name: {adapter_name!r}"
                    )
                adapter_names.add(adapter_name)
                adapter_description = adapter.get("description")
                if not isinstance(adapter_description, str) or not adapter_description.strip():
                    raise DeploymentError(
                        f"route adapter description is invalid: {adapter_name!r}"
                    )
                if adapter.get("status") != "active":
                    raise DeploymentError(
                        f"planned route adapter is executable: {adapter_name}"
                    )
                adapter_path = _library_adapter_path(
                    adapter.get("adapter_path"),
                    f"route adapter path for {adapter_name}",
                    candidate_name,
                    adapter_name,
                )
                if not router_root.joinpath(*adapter_path.parts).is_file():
                    raise DeploymentError(
                        f"route adapter path is missing: {adapter_path.as_posix()}"
                    )
                _validate_adapter_environment(
                    router_root.joinpath(*adapter_path.parts),
                    adapter_name,
                    name,
                )

    if seen_names != set(SCENARIOS):
        raise DeploymentError("route index scenarios do not match the fixed vocabulary")
    if not routes_dir.is_dir():
        raise DeploymentError("route index routes directory is missing")
    actual_paths = {
        child.relative_to(router_root).as_posix()
        for child in routes_dir.iterdir()
        if child.is_file() and child.name != "index.yaml"
    }
    unexpected_entries = [
        child.relative_to(router_root).as_posix()
        for child in routes_dir.iterdir()
        if child.name != "index.yaml" and not child.is_file()
    ]
    if unexpected_entries:
        raise DeploymentError(f"route directory contains non-file entries: {sorted(unexpected_entries)}")
    if actual_paths != declared_paths:
        missing = sorted(declared_paths - actual_paths)
        extra = sorted(actual_paths - declared_paths)
        raise DeploymentError(f"route index shard set mismatch: missing={missing}, extra={extra}")
    return declared_paths


def _load_source(manifest_path: Path) -> tuple[dict, dict, Path]:
    manifest_path = Path(manifest_path).resolve()
    report = validate_skills.validate(manifest_path)
    if not report["ok"]:
        codes = ", ".join(
            f"{item['code']}:{item['skill']}" for item in report["errors"]
        )
        raise DeploymentError(f"manifest/control validation failed: {codes}")
    data = _read_yaml(manifest_path, "manifest")
    if not isinstance(data, dict):
        raise DeploymentError("validated manifest is not a mapping")
    root = manifest_path.parents[2]
    return data, report, root


def _entry_path(root: Path, entry: dict) -> Path:
    path = (root / str(entry["path"])).resolve()
    if not path.is_dir():
        raise DeploymentError(f"active skill directory missing: {entry.get('name')}")
    return path


def _short_description(skill_root: Path, entry: dict) -> str:
    metadata_path = skill_root / "agents" / "openai.yaml"
    if metadata_path.is_file():
        metadata = _read_yaml(metadata_path, f"metadata for {entry['name']}")
        if isinstance(metadata, dict):
            interface = metadata.get("interface")
            if isinstance(interface, dict):
                value = interface.get("short_description")
                if isinstance(value, str) and value.strip():
                    return value.strip()
    return str(entry.get("description", ""))


def _active_modules(data: dict) -> list[dict]:
    return sorted(
        [
            entry
            for entry in data.get("skills", [])
            if isinstance(entry, dict)
            and entry.get("status") == "active"
            and entry.get("deployment_role") == "module"
        ],
        key=lambda entry: str(entry.get("name", "")),
    )


def _router_entry(data: dict) -> dict:
    routers = [
        entry
        for entry in data.get("skills", [])
        if isinstance(entry, dict)
        and entry.get("status") == "active"
        and entry.get("deployment_role") == "router"
    ]
    if len(routers) != 1 or routers[0].get("name") != ROUTER_NAME:
        raise DeploymentError("validated manifest does not contain the expected router")
    return routers[0]


def _planned_adapter_files(data: dict) -> dict[str, set[str]]:
    """Return manifest-authoritative planned adapter filenames by owner."""

    planned: dict[str, set[str]] = {}
    for entry in data.get("adapters", []):
        if not isinstance(entry, dict) or entry.get("status") != "planned":
            continue
        owner = entry.get("owner_skill")
        path = entry.get("path")
        if isinstance(owner, str) and isinstance(path, str):
            planned.setdefault(owner, set()).add(PurePosixPath(path).name)
    return planned


def _active_adapters(data: dict, owner: str, scenario: str) -> list[dict]:
    """Return active adapters closed over one module owner and scenario."""

    adapters = []
    for entry in data.get("adapters", []):
        if not isinstance(entry, dict):
            continue
        if entry.get("status") != "active" or entry.get("owner_skill") != owner:
            continue
        environments = entry.get("environments")
        if not isinstance(environments, list) or scenario not in environments:
            continue
        name = entry.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        adapters.append(entry)
    return sorted(adapters, key=lambda entry: str(entry.get("name", "")))


def _copy_module_source(source: Path, destination: Path, planned_files: set[str]) -> None:
    """Copy a private module without discovery metadata or planned adapters."""

    def ignore(directory: str, names: list[str]) -> list[str]:
        relative = Path(directory).resolve().relative_to(source.resolve()).as_posix()
        if relative == "adapters":
            return sorted(planned_files.intersection(names))
        if relative == "agents":
            return [name for name in names if name == "openai.yaml"]
        return []

    shutil.copytree(source, destination, ignore=ignore)
    (destination / "SKILL.md").rename(destination / "MODULE.md")


def _discovery_boundary_errors(router_root: Path) -> list[str]:
    """Keep Codex discovery files at the router entrypoint, outside library."""

    errors = []
    if not (router_root / "SKILL.md").is_file():
        errors.append("router discovery entrypoint SKILL.md is missing")
    library = router_root / "library"
    forbidden = sorted(set(library.rglob("SKILL.md")) | set(library.rglob("agents/openai.yaml")))
    for path in forbidden:
        errors.append(
            f"library contains forbidden discovery entrypoint: {path.relative_to(router_root).as_posix()}"
        )
    return errors


def _route_payloads(data: dict, root: Path, router_root: Path) -> tuple[dict, dict[str, str]]:
    modules = _active_modules(data)
    modules = sorted(modules, key=lambda entry: (-entry["routing_priority"], entry["name"]))
    global_routes = []
    for entry in modules:
        name = entry["name"]
        if entry.get("routing_scope", "scenario") != "global":
            continue
        if entry.get("entrypoint") is not True:
            continue
        global_routes.append(
            {
                "name": name,
                "selector": str(entry.get("routing_selector", "")).strip(),
                "routing_priority": entry["routing_priority"],
                "routing_outcome": entry["routing_outcome"],
                "skill_path": f"library/{name}/MODULE.md",
            }
        )
    index = {
        "schema_version": ROUTE_INDEX_SCHEMA_VERSION,
        "global_routes": global_routes,
        "scenarios": [
            {
                "name": scenario,
                "shard": f"_platform/routes/{scenario}.yaml",
                "selector": SCENARIO_SELECTORS[scenario],
            }
            for scenario in SCENARIOS
        ],
    }
    shards: dict[str, str] = {}
    routes_dir = router_root / "_platform" / "routes"
    routes_dir.mkdir(parents=True, exist_ok=True)
    _write_yaml(routes_dir / "index.yaml", index)
    for scenario in SCENARIOS:
        candidates = []
        for entry in modules:
            name = entry["name"]
            if entry.get("routing_scope", "scenario") == "global":
                continue
            if scenario not in (entry.get("scenarios") or []):
                continue
            if entry.get("entrypoint") is not True:
                continue
            module_root = _entry_path(root, entry)
            adapters = [
                {
                    "name": adapter["name"],
                    "description": str(adapter.get("description", "")).strip(),
                    "adapter_path": f"library/{name}/adapters/{adapter['name']}.md",
                    "status": "active",
                }
                for adapter in _active_adapters(data, name, scenario)
            ]
            candidates.append(
                {
                    "name": name,
                    "description": _short_description(module_root, entry),
                    "routing_priority": entry["routing_priority"],
                    "routing_outcome": entry["routing_outcome"],
                    "skill_path": f"library/{name}/MODULE.md",
                    "status": "active",
                    "adapters": adapters,
                }
            )
        payload = {"scenario": scenario, "skills": candidates}
        shard_path = routes_dir / f"{scenario}.yaml"
        _write_yaml(shard_path, payload)
        shards[f"_platform/routes/{scenario}.yaml"] = _sha256(shard_path)
    _validate_route_index(index, router_root)
    return index, shards


def build_payload(manifest_path: Path = DEFAULT_MANIFEST, staging_root: Path | None = None) -> dict:
    """Build a complete router payload in ``staging_root``.

    The returned mapping contains the staging payload path, validated manifest,
    generated state, and route metadata.  The caller owns cleanup of the
    staging directory.
    """

    manifest_path = Path(manifest_path).resolve()
    data, report, root = _load_source(manifest_path)
    router_entry = _router_entry(data)
    if staging_root is None:
        tmp_root = REPO_ROOT / ".tmp"
        tmp_root.mkdir(parents=True, exist_ok=True)
        staging_root = Path(tempfile.mkdtemp(prefix="p4-payload-", dir=str(tmp_root)))
    staging_root = Path(staging_root)
    staging_root.mkdir(parents=True, exist_ok=True)
    payload_root = staging_root / ROUTER_NAME
    if payload_root.exists():
        shutil.rmtree(payload_root)
    router_source = _entry_path(root, router_entry)
    shutil.copytree(router_source, payload_root)

    library_root = payload_root / "library"
    library_root.mkdir(parents=True, exist_ok=True)
    modules = _active_modules(data)
    planned_adapter_files = _planned_adapter_files(data)
    for entry in modules:
        destination = library_root / str(entry["name"])
        _copy_module_source(
            _entry_path(root, entry),
            destination,
            planned_adapter_files.get(str(entry["name"]), set()),
        )

    discovery_errors = _discovery_boundary_errors(payload_root)
    if discovery_errors:
        raise DeploymentError("; ".join(discovery_errors))
    index, shard_hashes = _route_payloads(data, root, payload_root)
    hashes = _relative_file_hashes(payload_root)
    state = {
        "deployment_schema_version": DEPLOYMENT_SCHEMA_VERSION,
        "manifest": {
            "schema_version": data.get("schema_version"),
            "sha256": _sha256(manifest_path),
        },
        "router": {
            "name": ROUTER_NAME,
            "version": router_entry.get("version"),
        },
        "modules": [
            {"name": entry.get("name"), "version": entry.get("version")}
            for entry in modules
        ],
        "routes": {
            "index": "_platform/routes/index.yaml",
            "index_sha256": hashes["_platform/routes/index.yaml"],
            "shards": shard_hashes,
        },
        "payload_files": hashes,
    }
    state_path = payload_root / "_platform" / "deployment-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "payload_root": payload_root,
        "state": state,
        "manifest": data,
        "report": report,
        "index": index,
        "modules": modules,
    }


def backup_root(target_root: Path) -> Path:
    target_root = Path(target_root).expanduser().resolve()
    return target_root.parent / f".{target_root.name}-{ROUTER_NAME}-backup"


def _managed_target(target_root: Path) -> Path:
    return Path(target_root).expanduser().resolve() / ROUTER_NAME


def _load_state(target: Path) -> dict | None:
    state_path = target / "_platform" / "deployment-state.json"
    if not state_path.is_file():
        return None
    try:
        value = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _is_reparse_point(path: Path) -> bool:
    """Return whether a path is a symlink, junction, or Windows reparse point."""

    path = Path(path)
    if path.is_symlink() or os.path.islink(path):
        return True
    is_junction = getattr(path, "is_junction", None)
    if callable(is_junction):
        try:
            if is_junction():
                return True
        except OSError:
            return True
    try:
        attributes = getattr(os.lstat(path), "st_file_attributes", 0)
    except (FileNotFoundError, OSError):
        attributes = 0
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400))


def _assert_no_reparse(path: Path, label: str) -> None:
    """Reject reparse points on an existing path or any existing ancestor."""

    path = Path(path).expanduser()
    current = path
    while True:
        if os.path.lexists(current) and _is_reparse_point(current):
            raise DeploymentError(f"{label} must not contain a symlink/junction/reparse point: {current}")
        if current.parent == current:
            break
        current = current.parent


def _normal_target_root(target_root: Path, *, create: bool) -> Path:
    target_root = Path(target_root).expanduser()
    _assert_no_reparse(target_root, "target root")
    if target_root.exists() and not target_root.is_dir():
        raise DeploymentError(f"target root is not a directory: {target_root}")
    if create:
        target_root.mkdir(parents=True, exist_ok=True)
    resolved = target_root.resolve()
    _assert_no_reparse(resolved, "target root")
    return resolved


def _assert_target_root(target_root: Path) -> Path:
    target_root = _normal_target_root(target_root, create=True)
    managed = target_root / ROUTER_NAME
    _assert_no_reparse(managed, "managed target")
    _assert_no_reparse(backup_root(target_root), "backup root")
    return target_root


def _is_managed_target(target: Path) -> bool:
    state = _load_state(target)
    return bool(
        target.is_dir()
        and state
        and state.get("deployment_schema_version") == DEPLOYMENT_SCHEMA_VERSION
        and state.get("router", {}).get("name") == ROUTER_NAME
    )


def verify_target(target_root: Path, expected_state: dict | None = None) -> dict:
    """Verify a deployed router and report drift without changing files."""

    try:
        target_root = _normal_target_root(target_root, create=False)
    except DeploymentError as exc:
        return {"ok": False, "target": str(Path(target_root)), "errors": [str(exc)]}
    target = target_root / ROUTER_NAME
    errors: list[str] = []
    try:
        _assert_no_reparse(target, "managed target")
    except DeploymentError as exc:
        return {"ok": False, "target": str(target), "errors": [str(exc)]}
    if not target.is_dir():
        return {"ok": False, "target": str(target), "errors": ["managed router is missing"]}
    errors.extend(_discovery_boundary_errors(target))
    state = _load_state(target)
    if state is None:
        return {"ok": False, "target": str(target), "errors": ["deployment state is missing or invalid"]}
    if expected_state is not None and state != expected_state:
        errors.append("deployment state differs from source plan")
    if state.get("router", {}).get("name") != ROUTER_NAME:
        errors.append("deployment state router name is invalid")
    expected_files = state.get("payload_files")
    if not isinstance(expected_files, dict):
        errors.append("deployment state payload_files is invalid")
        expected_files = {}
    for relative, expected_hash in expected_files.items():
        relative_path = PurePosixPath(str(relative))
        if (
            "\\" in str(relative)
            or relative_path.is_absolute()
            or ".." in relative_path.parts
            or "." in relative_path.parts
        ):
            errors.append(f"payload path escapes router: {relative}")
            continue
        path = target.joinpath(*relative_path.parts)
        if not path.is_file():
            errors.append(f"missing managed file: {relative}")
        elif _sha256(path) != expected_hash:
            errors.append(f"hash mismatch: {relative}")
    actual_files = _relative_file_hashes(target)
    actual_files.pop("_platform/deployment-state.json", None)
    for extra in sorted(set(actual_files) - set(expected_files)):
        errors.append(f"extra managed file: {extra}")
    modules = state.get("modules")
    module_names = [item.get("name") for item in modules] if isinstance(modules, list) else []
    library = target / "library"
    if not library.is_dir():
        errors.append("library directory is missing")
    else:
        installed = sorted(path.name for path in library.iterdir() if path.is_dir())
        if installed != sorted(module_names):
            errors.append("library module set differs from deployment state")
    routes = state.get("routes")
    route_paths = routes.get("shards", {}) if isinstance(routes, dict) else {}
    if not isinstance(routes, dict) or routes.get("index") != "_platform/routes/index.yaml":
        errors.append("deployment state route index path is invalid")
    if not isinstance(route_paths, dict):
        errors.append("deployment state routes.shards is invalid")
        route_paths = {}
    declared_paths: set[str] = set()
    index_path = target / "_platform" / "routes" / "index.yaml"
    try:
        index = _read_yaml(index_path, "_platform/routes/index.yaml")
        declared_paths = _validate_route_index(index, target)
    except (DeploymentError, OSError) as exc:
        errors.append(str(exc))
    state_paths = set()
    for relative in route_paths:
        try:
            state_paths.add(_route_path(relative, "deployment state shard").as_posix())
        except DeploymentError as exc:
            errors.append(str(exc))
    if declared_paths and state_paths != declared_paths:
        errors.append("deployment state route shard set differs from route index")
    for relative in sorted(declared_paths):
        path = target.joinpath(*PurePosixPath(relative).parts)
        payload = _read_yaml(path, relative)
        candidates = payload.get("skills", []) if isinstance(payload, dict) else []
        if not isinstance(candidates, list):
            errors.append(f"route shard skills is invalid: {relative}")
            continue
        for candidate in candidates:
            if not isinstance(candidate, dict):
                errors.append(f"route candidate is invalid: {relative}")
                continue
            skill_path = PurePosixPath(str(candidate.get("skill_path", "")))
            if (
                "\\" in str(candidate.get("skill_path", ""))
                or skill_path.is_absolute()
                or ".." in skill_path.parts
                or "." in skill_path.parts
                or not skill_path.as_posix().startswith("library/")
            ):
                errors.append(f"route skill path escapes library: {candidate.get('skill_path')}")
                continue
            if not target.joinpath(*skill_path.parts).is_file():
                errors.append(f"route skill path is missing: {candidate.get('skill_path')}")
            if candidate.get("status") != "active":
                errors.append(f"planned route candidate is executable: {candidate.get('name')}")
    return {"ok": not errors, "target": str(target), "errors": errors, "state": state}


def _snapshot(target: Path, backup: Path) -> bool:
    _assert_no_reparse(target, "managed target")
    _assert_no_reparse(backup, "backup root")
    if not target.exists():
        return False
    if not _is_managed_target(target):
        raise DeploymentError(
            f"refusing to replace unmanaged existing router: {target}"
        )
    previous = backup / "previous"
    _assert_no_reparse(previous, "previous snapshot")
    if backup.exists():
        _remove_tree(backup)
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copytree(target, previous)
    return True


def _remove_tree(path: Path) -> None:
    path = Path(path)
    if not os.path.lexists(path):
        return
    _assert_no_reparse(path, "managed deployment path")
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def _replace_payload(staging: Path, target: Path) -> None:
    _assert_no_reparse(staging, "staging payload")
    _assert_no_reparse(target, "managed target")
    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)
    old = parent / f".{ROUTER_NAME}.old-{uuid.uuid4().hex}"
    _assert_no_reparse(old, "replacement staging path")
    had_target = target.exists()
    try:
        if had_target:
            target.rename(old)
        shutil.copytree(staging, target)
    except Exception:
        _remove_tree(target)
        if old.exists():
            old.rename(target)
        raise
    finally:
        if old.exists():
            _remove_tree(old)


def apply_payload(target_root: Path, payload: dict) -> dict:
    """Apply a built payload and recover the previous managed target on failure."""

    target_root = _assert_target_root(target_root)
    target = target_root / ROUTER_NAME
    state = payload["state"]
    current = _load_state(target)
    if current == state and verify_target(target_root)["ok"]:
        return {"ok": True, "action": "noop", "target": str(target), "state": state}
    backup = backup_root(target_root)
    had_previous = _snapshot(target, backup)
    try:
        _replace_payload(Path(payload["payload_root"]), target)
        verification = verify_target(target_root, expected_state=state)
        if not verification["ok"]:
            raise DeploymentError("post-apply verification failed: " + "; ".join(verification["errors"]))
    except Exception as exc:
        previous = backup / "previous"
        recovery_error = None
        try:
            _assert_no_reparse(previous, "previous snapshot")
            _remove_tree(target)
            if had_previous and previous.is_dir():
                shutil.copytree(previous, target)
                restored = verify_target(target_root)
                if not restored["ok"]:
                    raise DeploymentError(
                        "restored previous payload failed verification: "
                        + "; ".join(restored["errors"])
                    )
            elif target.exists():
                raise DeploymentError("failed deployment target could not be removed")
        except Exception as restore_exc:
            recovery_error = restore_exc
        if recovery_error is not None:
            raise DeploymentError(
                f"deployment failed: {exc}; recovery failed: {recovery_error}; "
                f"manual recovery snapshot: {previous}"
            ) from exc
        if had_previous:
            raise DeploymentError(
                f"deployment failed: {exc}; previous snapshot restored and verified: {previous}"
            ) from exc
        raise DeploymentError(
            f"deployment failed: {exc}; no previous snapshot existed and the new target was removed"
        ) from exc
    return {
        "ok": True,
        "action": "applied",
        "target": str(target),
        "previous_snapshot": had_previous,
        "state": state,
    }


def rollback_payload(target_root: Path) -> dict:
    target_root = _assert_target_root(target_root)
    target = target_root / ROUTER_NAME
    backup = backup_root(target_root)
    previous = backup / "previous"
    _assert_no_reparse(backup, "backup root")
    _assert_no_reparse(previous, "previous snapshot")
    if not previous.is_dir() or not _is_managed_target(previous):
        raise DeploymentError("no valid previous router snapshot is available")
    current_backup = backup / "rollback-current"
    _assert_no_reparse(current_backup, "rollback recovery snapshot")
    if current_backup.exists():
        _remove_tree(current_backup)
    if target.exists():
        _assert_no_reparse(target, "managed target")
        if not _is_managed_target(target):
            raise DeploymentError(f"refusing to rollback over unmanaged router: {target}")
        shutil.copytree(target, current_backup)
    _remove_tree(target)
    try:
        shutil.copytree(previous, target)
        verification = verify_target(target_root)
        if not verification["ok"]:
            raise DeploymentError("rollback verification failed: " + "; ".join(verification["errors"]))
    except Exception as exc:
        _remove_tree(target)
        recovery_error = None
        try:
            if current_backup.is_dir():
                shutil.copytree(current_backup, target)
                restored = verify_target(target_root)
                if not restored["ok"]:
                    raise DeploymentError(
                        "restored current payload failed verification: "
                        + "; ".join(restored["errors"])
                    )
        except Exception as restore_exc:
            recovery_error = restore_exc
        if recovery_error is not None:
            raise DeploymentError(
                f"rollback failed: {exc}; recovery failed: {recovery_error}; "
                f"manual recovery snapshot: {previous}"
            ) from exc
        raise DeploymentError(
            f"rollback failed: {exc}; current payload restored and verified; "
            f"previous snapshot retained at {previous}"
        ) from exc
    _remove_tree(previous)
    _remove_tree(current_backup)
    return {"ok": True, "action": "rollback", "target": str(target)}


def _plan_result(target_root: Path, payload: dict) -> dict:
    target = Path(target_root).expanduser().resolve() / ROUTER_NAME
    current = _load_state(target)
    verification = verify_target(target_root) if target.exists() else {"ok": False, "errors": []}
    same = current == payload["state"] and verification.get("ok") is True
    return {
        "ok": True,
        "action": "noop" if same else "plan",
        "target": str(target),
        "managed_scope": [ROUTER_NAME],
        "unmanaged_paths_untouched": True,
        "modules": [entry.get("name") for entry in payload["modules"]],
        "scenarios": list(SCENARIOS),
        "would_change": not same,
        "state": payload["state"],
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Build/deploy the routed global skill payload.")
    parser.add_argument("--target-root", default=None, help="target skill root")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true", help="plan only (the default)")
    modes.add_argument("--apply", action="store_true", help="apply the assembled payload")
    modes.add_argument("--verify", action="store_true", help="verify an installed payload")
    modes.add_argument("--rollback", action="store_true", help="restore the previous snapshot")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def _default_target_root() -> Path:
    return Path.home() / ".codex" / "skills"


def main(argv=None):
    args = parse_args(argv)
    target_root = Path(args.target_root).expanduser() if args.target_root else _default_target_root()
    try:
        if args.verify:
            deploy_tmp = REPO_ROOT / ".tmp" / "deploy"
            deploy_tmp.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(
                prefix="verify-", dir=str(deploy_tmp)
            ) as run_dir:
                payload = build_payload(Path(args.manifest), Path(run_dir))
                result = verify_target(target_root, expected_state=payload["state"])
        elif args.rollback:
            result = rollback_payload(target_root)
        else:
            deploy_tmp = REPO_ROOT / ".tmp" / "deploy"
            deploy_tmp.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(
                prefix="run-", dir=str(deploy_tmp)
            ) as run_dir:
                payload = build_payload(Path(args.manifest), Path(run_dir))
                if args.apply:
                    result = apply_payload(target_root, payload)
                else:
                    result = _plan_result(target_root, payload)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result.get("ok") else 1
    except (DeploymentError, OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
