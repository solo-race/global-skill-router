#!/usr/bin/env python3
"""Skill registry validator for development/skill/manifest.yaml.

Checks the registry against the P4 manifest/control contract. The current
manifest schema is v3: read-only design sources, deployable skills, and
framework-owned adapters have separate registry sections. Planned entries may
be forward-registered before their directory exists; active entries must pass
their complete activation gates.

Additionally enforces the P1 Profile Contract gate (plan 020): every active/planned
entry whose skill directory contains a profiles/ subdirectory must have every
profile YAML file pass profile_errors() (schema version, closed field set, closed
top-level ABI, unique dimensions, binding triples, extension placement, etc.).
External entries and entries without profiles/ are unaffected.

Third-party dependency: PyYAML (yaml.safe_load for manifest and frontmatter
parsing); declared in AGENTS.md Core Rule 5.

Output contract: one JSON report document on stdout; one stderr line per
violation, "CODE skill: message". Exit codes: 0 all green, 1 violations,
130 on KeyboardInterrupt.
"""

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPO_ROOT / "development" / "skill" / "manifest.yaml"
REQUIRED_FIELDS = ("name", "path", "status", "version", "description")
LIST_FIELDS = ("scenarios", "deps", "composed_of")
VALID_STATUSES = frozenset({"planned", "active"})
VALID_DEPLOYMENT_ROLES = frozenset({"router", "module"})
VALID_SOURCE_KINDS = frozenset({"upstream-snapshot", "local-reference"})
VALID_SCENARIOS = frozenset({"win-access-vba", "win-android", "wsl-python"})
VALID_VERIFICATION_KINDS = frozenset({"linear", "partial_order", "independent_checks"})
VALID_MUTATION_SUPPORT = frozenset({"none", "bounded", "high-impact"})
KEBAB_CASE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
RECOVERY_HEADING = re.compile(
    r"^(##+)\s+(?:\d+\.\s*)?recovery(?:\s+model)?\b.*$",
    re.I,
)
HEADING = re.compile(r"^(#+)\s+\S.*$")
# Closed top-level field set of the research-investigation Profile Contract (profile-contract.md).
# Any other top-level key is a contract violation, never tolerated prose.
PROFILE_KNOWN_FIELDS = frozenset({
    "profile_schema_version", "domain", "subject_type", "investigation_dimensions",
    "concept_groups", "query_examples", "vocabulary_authority", "relevance",
    "packet_extensions", "pipeline_binding", "project_bindings", "profile_guidance",
    "display",
})
PROFILE_EXTENSION_PREFIX = "profile_extensions."
PROFILE_ASSESSABLE_STATUSES = frozenset({"active", "planned"})


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Validate the skill registry manifest."
    )
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST),
        help="path to manifest.yaml (default: %(default)s)",
    )
    return parser.parse_args(argv)


def _err(code, skill, message):
    return {"code": code, "skill": skill, "message": message}


def _report(
    ok,
    manifest,
    skills_checked,
    errors,
    sources_checked=0,
    adapters_checked=0,
    routes=None,
):
    return {
        "ok": ok,
        "manifest": manifest,
        "skills_checked": skills_checked,
        "sources_checked": sources_checked,
        "adapters_checked": adapters_checked,
        "routes": routes or {},
        "errors": errors,
    }


def _load_manifest(manifest_path, errors):
    """E1/E2: manifest must exist and parse to {schema_version: 1, skills: [...]}."""
    if not manifest_path.is_file():
        errors.append(
            _err("MANIFEST_NOT_FOUND", "(manifest)", f"manifest not found: {manifest_path}")
        )
        return None
    try:
        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        errors.append(_err("MANIFEST_PARSE_ERROR", "(manifest)", str(exc)))
        return None
    if not isinstance(data, dict):
        errors.append(
            _err(
                "MANIFEST_PARSE_ERROR",
                "(manifest)",
                "manifest must be a mapping",
            )
        )
        return None
    if data.get("schema_version") != 3:
        errors.append(
            _err(
                "SCHEMA_VERSION_UNSUPPORTED",
                "(manifest)",
                f"schema_version must be 3, got {data.get('schema_version')!r}",
            )
        )
        return None
    for section in ("sources", "skills", "adapters"):
        if not isinstance(data.get(section), list):
            errors.append(
                _err(
                    "MANIFEST_SECTION_TYPE",
                    "(manifest)",
                    f"manifest section '{section}' must be a list",
                )
            )
            data[section] = []
    return data


def _frontmatter_errors(skill_dir, entry_name, dir_basename):
    """F1-F3 against <skill_dir>/SKILL.md; caller guarantees the file exists."""
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    close = None
    if lines and lines[0].strip() == "---":
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                close = index
                break
    if close is None:
        return [
            _err(
                "FRONTMATTER_MISSING",
                entry_name,
                "SKILL.md has no '---' fenced frontmatter block",
            )
        ]
    try:
        frontmatter = yaml.safe_load("\n".join(lines[1:close]))
    except yaml.YAMLError:
        frontmatter = None
    if not isinstance(frontmatter, dict):
        frontmatter = {}
    errors = []
    fm_name = frontmatter.get("name")
    if fm_name != entry_name or dir_basename != entry_name:
        errors.append(
            _err(
                "NAME_MISMATCH",
                entry_name,
                (
                    f"frontmatter name {fm_name!r}, directory basename "
                    f"{dir_basename!r} and entry name {entry_name!r} must be equal"
                ),
            )
        )
    description = frontmatter.get("description")
    if not isinstance(description, str) or "Use when" not in description:
        errors.append(
            _err(
                "DESCRIPTION_NO_TRIGGER",
                entry_name,
                "frontmatter description must contain a 'Use when' trigger phrase",
            )
        )
    return errors


def profile_errors(profile_path, label=None):
    """Validate one profile YAML file against the Profile Contract (profile-contract.md v1).

    Returns a list of error dicts; an empty list means the profile passes the mechanical
    gate. This is a structural ABI check only: externally referenced binding objects
    (consuming-project schemas, configs, stores) are never existence-checked here.
    """
    profile_path = Path(profile_path)
    if label is None:
        label = profile_path.name
    try:
        text = profile_path.read_text(encoding="utf-8")
    except OSError as exc:
        return [_err("PROFILE_PARSE_ERROR", label, f"cannot read profile: {exc}")]
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return [_err("PROFILE_PARSE_ERROR", label, str(exc))]
    if not isinstance(data, dict):
        return [_err("PROFILE_PARSE_ERROR", label, "profile must be a mapping")]
    if data.get("profile_schema_version") != 1:
        return [
            _err(
                "PROFILE_SCHEMA_VERSION_UNSUPPORTED",
                label,
                (
                    "profile_schema_version must be 1, got "
                    f"{data.get('profile_schema_version')!r}"
                ),
            )
        ]
    errors = []
    slug = profile_path.stem
    domain = data.get("domain")
    if not isinstance(domain, str) or not domain.strip():
        errors.append(
            _err(
                "PROFILE_DOMAIN_FORMAT",
                label,
                "domain must be a non-empty kebab-case string",
            )
        )
    elif not KEBAB_CASE.match(domain):
        errors.append(
            _err(
                "PROFILE_DOMAIN_FORMAT",
                label,
                f"domain {domain!r} is not kebab-case",
            )
        )
    elif domain != slug:
        errors.append(
            _err(
                "PROFILE_DOMAIN_MISMATCH",
                label,
                f"domain {domain!r} must equal the profile file slug {slug!r}",
            )
        )
    subject_type = data.get("subject_type")
    if not isinstance(subject_type, str) or not subject_type.strip():
        errors.append(
            _err(
                "PROFILE_SUBJECT_TYPE_INVALID",
                label,
                "subject_type must be a non-empty string",
            )
        )
    dimensions = data.get("investigation_dimensions")
    if not isinstance(dimensions, list) or not dimensions:
        errors.append(
            _err(
                "PROFILE_DIMENSIONS_INVALID",
                label,
                "investigation_dimensions must be a non-empty list",
            )
        )
    else:
        ids = []
        for index, entry in enumerate(dimensions):
            if not isinstance(entry, dict):
                errors.append(
                    _err(
                        "PROFILE_DIMENSION_INCOMPLETE",
                        label,
                        f"dimension at index {index} must be a mapping with id and purpose",
                    )
                )
                continue
            dim_id = entry.get("id")
            if not isinstance(dim_id, str) or not dim_id.strip():
                errors.append(
                    _err(
                        "PROFILE_DIMENSION_INCOMPLETE",
                        label,
                        f"dimension at index {index} is missing a non-empty id",
                    )
                )
            elif not KEBAB_CASE.match(dim_id):
                errors.append(
                    _err(
                        "PROFILE_DIMENSION_ID_FORMAT",
                        label,
                        f"dimension id {dim_id!r} is not kebab-case",
                    )
                )
            else:
                ids.append(dim_id)
            purpose = entry.get("purpose")
            if not isinstance(purpose, str) or not purpose.strip():
                errors.append(
                    _err(
                        "PROFILE_DIMENSION_INCOMPLETE",
                        label,
                        f"dimension {dim_id!r} is missing a non-empty purpose",
                    )
                )
        duplicates = sorted({value for value in ids if ids.count(value) > 1})
        if duplicates:
            errors.append(
                _err(
                    "PROFILE_DIMENSION_DUPLICATE_ID",
                    label,
                    f"duplicate dimension ids: {duplicates}",
                )
            )
    if not isinstance(data.get("concept_groups"), dict):
        errors.append(
            _err(
                "PROFILE_CONCEPT_GROUPS_TYPE",
                label,
                "concept_groups must be a mapping",
            )
        )
    if not isinstance(data.get("query_examples"), list):
        errors.append(
            _err(
                "PROFILE_QUERY_EXAMPLES_TYPE",
                label,
                "query_examples must be a list",
            )
        )
    bindings = data.get("project_bindings")
    if bindings is None:
        bindings = {}
    if not isinstance(bindings, dict):
        errors.append(
            _err(
                "PROFILE_PROJECT_BINDINGS_TYPE",
                label,
                "project_bindings must be a mapping",
            )
        )
        bindings = {}
    for key, entry in bindings.items():
        if not isinstance(entry, dict):
            errors.append(
                _err(
                    "PROFILE_BINDING_INCOMPLETE",
                    label,
                    f"binding {key!r} must be a mapping declaring owner, required, when_unavailable",
                )
            )
            continue
        for field in ("owner", "when_unavailable"):
            value = entry.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(
                    _err(
                        "PROFILE_BINDING_INCOMPLETE",
                        label,
                        f"binding {key!r} is missing a non-empty {field}",
                    )
                )
        if "required" not in entry:
            errors.append(
                _err(
                    "PROFILE_BINDING_INCOMPLETE",
                    label,
                    f"binding {key!r} is missing required",
                )
            )
        elif not isinstance(entry.get("required"), bool):
            errors.append(
                _err(
                    "PROFILE_BINDING_REQUIRED_TYPE",
                    label,
                    f"binding {key!r}: required must be a boolean",
                )
            )
    authority = data.get("vocabulary_authority")
    if authority is not None:
        if not isinstance(authority, str) or not authority.strip():
            errors.append(
                _err(
                    "PROFILE_VOCAB_AUTHORITY_UNRESOLVED",
                    label,
                    "vocabulary_authority must be null or a project_bindings key",
                )
            )
        elif authority not in bindings:
            errors.append(
                _err(
                    "PROFILE_VOCAB_AUTHORITY_UNRESOLVED",
                    label,
                    (
                        "vocabulary_authority "
                        f"{authority!r} does not resolve to a project_bindings entry"
                    ),
                )
            )
    extensions = data.get("packet_extensions")
    if extensions is None:
        extensions = {}
    if not isinstance(extensions, dict):
        errors.append(
            _err(
                "PROFILE_EXTENSIONS_TYPE",
                label,
                "packet_extensions must be a mapping",
            )
        )
    else:
        for key, entry in extensions.items():
            placement = entry.get("placed_at") if isinstance(entry, dict) else None
            expected = f"{PROFILE_EXTENSION_PREFIX}{key}"
            if placement != expected:
                errors.append(
                    _err(
                        "PROFILE_EXTENSION_PLACEMENT",
                        label,
                        (
                            f"extension {key!r}: placed_at must equal "
                            f"{expected!r}, got {placement!r}"
                        ),
                    )
                )
    pipeline = data.get("pipeline_binding")
    if pipeline is not None:
        if not isinstance(pipeline, dict):
            errors.append(
                _err(
                    "PROFILE_PIPELINE_BINDING_INVALID",
                    label,
                    "pipeline_binding must be null or a mapping",
                )
            )
        else:
            mode = pipeline.get("mode")
            if not isinstance(mode, str) or not mode.strip():
                errors.append(
                    _err(
                        "PROFILE_PIPELINE_BINDING_INVALID",
                        label,
                        "pipeline_binding must declare a non-empty mode",
                    )
                )
            for field in ("reference_stages", "consumes", "produces", "never_promotes_to"):
                value = pipeline.get(field)
                if not isinstance(value, list) or not value or any(
                    not isinstance(item, str) or not item.strip() for item in value
                ):
                    errors.append(
                        _err(
                            "PROFILE_PIPELINE_BINDING_INVALID",
                            label,
                            f"pipeline_binding.{field} must be a non-empty list of strings",
                        )
                    )
    guidance = data.get("profile_guidance")
    if guidance is not None and not isinstance(guidance, dict):
        errors.append(
            _err(
                "PROFILE_GUIDANCE_TYPE",
                label,
                "profile_guidance must be a mapping",
            )
        )
    display = data.get("display")
    if display is not None and not isinstance(display, dict):
        errors.append(
            _err(
                "PROFILE_DISPLAY_TYPE",
                label,
                "display must be a mapping",
            )
        )
    for key in sorted(set(data) - PROFILE_KNOWN_FIELDS):
        errors.append(
            _err(
                "PROFILE_UNKNOWN_FIELD",
                label,
                (
                    f"unknown top-level field {key!r}; load-bearing profile-local semantics "
                    "belong under profile_guidance"
                ),
            )
        )
    return errors


def _read_frontmatter_document(path):
    """Return (frontmatter, body, error_message) for a fenced document."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        return None, "", str(exc)
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text, "missing '---' fenced frontmatter block"
    close = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            close = index
            break
    if close is None:
        return None, text, "missing closing frontmatter fence"
    try:
        frontmatter = yaml.safe_load("\n".join(lines[1:close]))
    except yaml.YAMLError as exc:
        return None, "\n".join(lines[close + 1 :]), str(exc)
    if not isinstance(frontmatter, dict):
        return None, "\n".join(lines[close + 1 :]), "frontmatter must be a mapping"
    return frontmatter, "\n".join(lines[close + 1 :]), None


def _has_nonempty_recovery_section(body):
    """Return whether the Recovery heading owns non-empty section content."""
    lines = body.splitlines()
    for index, line in enumerate(lines):
        match = RECOVERY_HEADING.match(line.strip())
        if match is None:
            continue
        level = len(match.group(1))
        end = len(lines)
        for next_index in range(index + 1, len(lines)):
            heading = HEADING.match(lines[next_index].strip())
            if heading and len(heading.group(1)) <= level:
                end = next_index
                break
        return any(line.strip() for line in lines[index + 1 : end])
    return False


def _safe_repo_path(root, value):
    """Resolve a repo-relative path, returning None for absolute/escaping paths."""
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.replace("\\", "/")
    if PurePosixPath(normalized).is_absolute() or re.match(r"^[A-Za-z]:", normalized):
        return None
    candidate = (Path(root) / Path(normalized)).resolve()
    try:
        candidate.relative_to(Path(root).resolve())
    except ValueError:
        return None
    return candidate


def _source_errors(entry, index, root):
    if not isinstance(entry, dict):
        return [_err("MANIFEST_SECTION_TYPE", f"<source {index}>", "source entry must be a mapping")]
    label = entry.get("id") if isinstance(entry.get("id"), str) else f"<source {index}>"
    errors = []
    for field in ("id", "path", "kind", "version", "description"):
        if not isinstance(entry.get(field), str) or not entry[field].strip():
            errors.append(_err("SOURCE_FIELD_INVALID", label, f"source field '{field}' must be a non-empty string"))
    if entry.get("kind") not in VALID_SOURCE_KINDS:
        errors.append(_err("SOURCE_FIELD_INVALID", label, f"source kind must be one of {sorted(VALID_SOURCE_KINDS)}"))
    if not isinstance(entry.get("required"), bool):
        errors.append(_err("SOURCE_FIELD_INVALID", label, "source required must be a boolean"))
    path = _safe_repo_path(root, entry.get("path"))
    if path is None:
        errors.append(_err("SOURCE_PATH_INVALID", label, f"source path must stay within repository: {entry.get('path')!r}"))
    elif not path.exists():
        if entry.get("required") is True:
            errors.append(_err("SOURCE_PATH_MISSING", label, f"required source path does not exist: {entry.get('path')}"))
    elif not path.is_dir():
        errors.append(_err("SOURCE_NOT_DIRECTORY", label, f"source path is not a directory: {entry.get('path')}"))
    return errors


def _metadata_errors(metadata_path, skill_name):
    try:
        data = yaml.safe_load(Path(metadata_path).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return [_err("ENTRYPOINT_METADATA_INVALID", skill_name, f"cannot parse metadata: {exc}")]
    if not isinstance(data, dict) or not isinstance(data.get("interface"), dict):
        return [_err("ENTRYPOINT_METADATA_INVALID", skill_name, "metadata must contain an interface mapping")]
    interface = data["interface"]
    errors = []
    for field in ("display_name", "short_description", "default_prompt"):
        value = interface.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(_err("ENTRYPOINT_METADATA_INVALID", skill_name, f"interface.{field} must be a non-empty string"))
    prompt = interface.get("default_prompt")
    if isinstance(prompt, str) and f"${skill_name}" not in prompt:
        errors.append(_err("ENTRYPOINT_PROMPT_NO_TRIGGER", skill_name, f"default_prompt must contain ${skill_name}"))
    return errors


def _entrypoint_errors(skill_dir, skill_name, status, entrypoint):
    if not isinstance(entrypoint, bool):
        return [_err("ENTRYPOINT_FLAG_INVALID", skill_name, "entrypoint must be a boolean")]
    if skill_dir is None or not skill_dir.is_dir():
        if status == "active" and entrypoint:
            return [_err("ENTRYPOINT_METADATA_MISSING", skill_name, "active entrypoint skill directory is missing")]
        return []
    metadata_path = skill_dir / "agents" / "openai.yaml"
    if not metadata_path.is_file():
        if status == "active" and entrypoint:
            return [_err("ENTRYPOINT_METADATA_MISSING", skill_name, f"missing metadata: {metadata_path}")]
        return []
    return _metadata_errors(metadata_path, skill_name)


def _adapter_contract_errors(adapter_path, manifest_entry):
    label = manifest_entry.get("name", "<adapter>")
    frontmatter, body, parse_error = _read_frontmatter_document(adapter_path)
    if parse_error:
        return [_err("ADAPTER_FRONTMATTER_MISSING", label, parse_error)]
    errors = []
    if frontmatter.get("adapter_schema_version") != 1:
        errors.append(_err("ADAPTER_SCHEMA_VERSION_UNSUPPORTED", label, "adapter_schema_version must be 1"))
    stem = PurePosixPath(str(manifest_entry.get("path", ""))).stem
    if frontmatter.get("adapter") != label or stem != label:
        errors.append(_err("ADAPTER_ID_MISMATCH", label, f"frontmatter adapter, manifest name, and file stem must equal {label!r}"))

    manifest_envs = manifest_entry.get("environments")
    if not isinstance(manifest_envs, list) or not manifest_envs or any(not isinstance(value, str) for value in manifest_envs):
        manifest_envs = []
    fm_envs = frontmatter.get("environments")
    if (
        not isinstance(fm_envs, list)
        or not fm_envs
        or any(not isinstance(value, str) or value not in VALID_SCENARIOS for value in fm_envs)
        or len(fm_envs) != len(set(fm_envs))
    ):
        errors.append(_err("ADAPTER_ENVIRONMENTS_INVALID", label, "frontmatter environments must be a non-empty list of valid scenarios"))
        fm_envs = []
    if manifest_envs and sorted(manifest_envs) != sorted(fm_envs):
        errors.append(_err("ADAPTER_ENVIRONMENT_MISMATCH", label, "manifest and adapter frontmatter environments must match"))

    capabilities = frontmatter.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities or any(not isinstance(value, str) or not value.strip() for value in capabilities):
        errors.append(_err("ADAPTER_CAPABILITIES_INVALID", label, "capabilities must be a non-empty list of strings"))
    elif len(capabilities) != len(set(capabilities)):
        errors.append(_err("ADAPTER_CAPABILITY_DUPLICATE", label, "capabilities must not contain duplicates"))

    task_modes = frontmatter.get("task_modes")
    if not isinstance(task_modes, dict):
        errors.append(_err("ADAPTER_TASK_MODES_INVALID", label, "task_modes must be a mapping"))
    else:
        if "closed" not in task_modes or not isinstance(task_modes.get("closed"), bool):
            errors.append(_err("ADAPTER_TASK_MODES_INVALID", label, "task_modes.closed must be an explicit boolean"))
        modes = task_modes.get("modes")
        if not isinstance(modes, list) or not modes or any(not isinstance(value, str) or not value.strip() for value in modes):
            errors.append(_err("ADAPTER_TASK_MODES_INVALID", label, "task_modes.modes must be a list of strings"))
        elif len(modes) != len(set(modes)):
            errors.append(_err("ADAPTER_TASK_MODES_INVALID", label, "task_modes.modes must not contain duplicates"))

    verification = frontmatter.get("verification_model_kind")
    if verification not in VALID_VERIFICATION_KINDS:
        errors.append(_err("ADAPTER_VERIFICATION_KIND_INVALID", label, f"verification_model_kind must be one of {sorted(VALID_VERIFICATION_KINDS)}"))
    mutation = frontmatter.get("mutation_support")
    if mutation not in VALID_MUTATION_SUPPORT:
        errors.append(_err("ADAPTER_MUTATION_SUPPORT_INVALID", label, f"mutation_support must be one of {sorted(VALID_MUTATION_SUPPORT)}"))
    elif mutation != "none" and not _has_nonempty_recovery_section(body):
        errors.append(_err("ADAPTER_RECOVERY_SECTION_MISSING", label, "mutating adapters must declare a non-empty Recovery model section"))
    return errors


def _adapter_errors(entry, index, root, skill_statuses):
    if not isinstance(entry, dict):
        return [_err("MANIFEST_SECTION_TYPE", f"<adapter {index}>", "adapter entry must be a mapping")]
    label = entry.get("name") if isinstance(entry.get("name"), str) else f"<adapter {index}>"
    errors = []
    for field in ("name", "path", "status", "owner_skill", "version", "description"):
        if not isinstance(entry.get(field), str) or not entry[field].strip():
            errors.append(_err("ADAPTER_FIELD_INVALID", label, f"adapter field '{field}' must be a non-empty string"))
    status = entry.get("status")
    if status not in VALID_STATUSES:
        errors.append(_err("INVALID_STATUS", label, f"adapter status must be one of {sorted(VALID_STATUSES)}"))
    owner = entry.get("owner_skill")
    if owner not in skill_statuses:
        errors.append(_err("ADAPTER_OWNER_UNKNOWN", label, f"owner skill {owner!r} is not registered"))
    elif status == "active" and skill_statuses[owner] != "active":
        errors.append(_err("ADAPTER_OWNER_NOT_ACTIVE", label, f"active adapter owner {owner!r} is not active"))
    envs = entry.get("environments")
    if not isinstance(envs, list) or not envs or any(not isinstance(value, str) or value not in VALID_SCENARIOS for value in envs) or len(envs) != len(set(envs)):
        errors.append(_err("ADAPTER_ENVIRONMENTS_INVALID", label, "manifest environments must be a non-empty list of unique valid scenarios"))
    rel_path = entry.get("path")
    adapter_path = _safe_repo_path(root, rel_path)
    if adapter_path is not None and isinstance(owner, str) and owner:
        expected_dir = (Path(root) / "development" / "skill" / owner / "adapters").resolve()
        expected_path = expected_dir / f"{label}.md"
        try:
            adapter_path.relative_to(expected_dir)
        except ValueError:
            errors.append(
                _err(
                    "ADAPTER_PATH_INVALID",
                    label,
                    f"adapter path must stay under owner adapters directory: {rel_path!r}",
                )
            )
        if adapter_path != expected_path:
            errors.append(
                _err(
                    "ADAPTER_PATH_INVALID",
                    label,
                    f"adapter path must equal {expected_path.relative_to(root).as_posix()!r}",
                )
            )
    elif adapter_path is None:
        errors.append(
            _err(
                "ADAPTER_PATH_INVALID",
                label,
                f"adapter path must stay within repository: {rel_path!r}",
            )
        )
    if status == "active" and (adapter_path is None or not adapter_path.is_file()):
        errors.append(_err("ACTIVE_ADAPTER_PATH_MISSING", label, f"active adapter file is missing: {rel_path}"))
    if adapter_path is not None and adapter_path.is_file():
        errors.extend(_adapter_contract_errors(adapter_path, entry))
    return errors


def _check_skill_entry_v2(entry, index, root, errors):
    if not isinstance(entry, dict):
        errors.append(_err("MANIFEST_SECTION_TYPE", f"<skill {index}>", "skill entry must be a mapping"))
        return
    name = entry.get("name") if isinstance(entry.get("name"), str) and entry.get("name") else f"<skill {index}>"
    for field in REQUIRED_FIELDS:
        value = entry.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(_err("MISSING_FIELD", name, f"required field '{field}' must be a non-empty string"))
    status = entry.get("status")
    if status not in VALID_STATUSES:
        errors.append(_err("INVALID_STATUS", name, f"status must be one of {sorted(VALID_STATUSES)}, got {status!r}"))
    deployment_role = entry.get("deployment_role")
    if deployment_role not in VALID_DEPLOYMENT_ROLES:
        errors.append(
            _err(
                "DEPLOYMENT_ROLE_INVALID",
                name,
                f"deployment_role must be one of {sorted(VALID_DEPLOYMENT_ROLES)}, got {deployment_role!r}",
            )
        )
    lists = {}
    for field in LIST_FIELDS:
        value = entry.get(field)
        if value is None:
            value = []
        if not isinstance(value, list):
            errors.append(_err("MISSING_FIELD", name, f"'{field}' must be a list"))
            value = []
        lists[field] = value
    for scenario in lists["scenarios"]:
        if scenario not in VALID_SCENARIOS:
            errors.append(_err("INVALID_SCENARIO", name, f"scenario '{scenario}' not in {sorted(VALID_SCENARIOS)}"))
    if not isinstance(entry.get("entrypoint"), bool):
        errors.append(_err("ENTRYPOINT_FLAG_INVALID", name, "entrypoint must be a boolean"))

    rel_path = entry.get("path")
    skill_dir = _safe_repo_path(root, rel_path)
    if skill_dir is None:
        errors.append(
            _err(
                "SKILL_PATH_INVALID",
                name,
                f"skill path must stay within repository: {rel_path!r}",
            )
        )
    elif isinstance(name, str) and not name.startswith("<"):
        expected = (Path(root) / "development" / "skill" / name).resolve()
        if skill_dir != expected:
            errors.append(
                _err(
                    "SKILL_PATH_INVALID",
                    name,
                    f"skill path must equal {expected.relative_to(root).as_posix()!r}",
                )
            )
    if status == "planned":
        if skill_dir is not None and (skill_dir / "SKILL.md").is_file():
            errors.extend(_frontmatter_errors(skill_dir, name, PurePosixPath(rel_path).name))
    elif status == "active":
        if skill_dir is None or not skill_dir.exists():
            errors.append(_err("ACTIVE_PATH_MISSING", name, f"path does not exist: {rel_path}"))
        elif not (skill_dir / "SKILL.md").is_file():
            errors.append(_err("ACTIVE_SKILL_MD_MISSING", name, f"missing SKILL.md under: {rel_path}"))
        else:
            errors.extend(_frontmatter_errors(skill_dir, name, PurePosixPath(rel_path).name))
        if not lists["scenarios"]:
            errors.append(_err("ACTIVE_EMPTY_SCENARIOS", name, "active entries must declare at least one scenario"))

    if isinstance(entry.get("entrypoint"), bool):
        errors.extend(_entrypoint_errors(skill_dir, name, status, entry.get("entrypoint")))

    if (
        name == "research-investigation"
        and status in PROFILE_ASSESSABLE_STATUSES
        and skill_dir is not None
        and skill_dir.is_dir()
    ):
        profiles_dir = skill_dir / "profiles"
        if profiles_dir.is_dir():
            profiles = sorted(list(profiles_dir.glob("*.yaml")) + list(profiles_dir.glob("*.yml")))
            for profile_path in profiles:
                relative = profile_path.relative_to(skill_dir).as_posix()
                for error in profile_errors(profile_path, name):
                    error["message"] = f"{relative}: {error['message']}"
                    errors.append(error)


def _validate_edges(entries, errors):
    statuses = {
        entry.get("name"): entry.get("status")
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("name"), str)
    }
    graphs = {"deps": {}, "composed_of": {}}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            continue
        name = entry["name"]
        for field, unknown_code, inactive_code, cycle_code in (
            ("deps", "DEP_UNKNOWN_REF", "DEP_NOT_ACTIVE", "DEP_CYCLE"),
            ("composed_of", "COMPOSED_OF_UNKNOWN_REF", "COMPOSED_OF_NOT_ACTIVE", "COMPOSED_OF_CYCLE"),
        ):
            refs = entry.get(field)
            if not isinstance(refs, list):
                continue
            graph = graphs[field].setdefault(name, [])
            for ref in refs:
                if not isinstance(ref, str) or ref not in statuses:
                    errors.append(_err(unknown_code, name, f"{field} reference {ref!r} does not resolve to a skill"))
                    continue
                graph.append(ref)
                if ref == name:
                    errors.append(_err(cycle_code, name, f"{field} self-reference is not allowed"))
                elif entry.get("status") == "active" and statuses.get(ref) != "active":
                    errors.append(_err(inactive_code, name, f"active skill target {ref!r} is not active"))

    for field, graph in graphs.items():
        if not graph:
            continue
        code = "DEP_CYCLE" if field == "deps" else "COMPOSED_OF_CYCLE"
        state = {}
        stack = []
        reported = set()

        def visit(node):
            state[node] = 1
            stack.append(node)
            for target in graph.get(node, []):
                if state.get(target) == 1:
                    start = stack.index(target)
                    cycle = tuple(sorted(set(stack[start:] + [target])))
                    if cycle not in reported:
                        reported.add(cycle)
                        errors.append(_err(code, cycle[0], f"{field} cycle detected: {' -> '.join(cycle)}"))
                elif state.get(target) != 2:
                    visit(target)
            stack.pop()
            state[node] = 2

        for node in sorted(graph):
            if state.get(node) is None:
                visit(node)


def _deployment_errors(entries, errors):
    """Validate the physical catalog contract introduced by P4."""
    valid_entries = [
        entry
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("name"), str)
    ]
    routers = [
        entry for entry in valid_entries
        if entry.get("deployment_role") == "router"
    ]
    active_routers = [entry for entry in routers if entry.get("status") == "active"]
    if len(active_routers) != 1:
        errors.append(
            _err(
                "ROUTER_CARDINALITY_INVALID",
                "(manifest)",
                f"manifest must contain exactly one active router, found {len(active_routers)}",
            )
        )
        return

    router = active_routers[0]
    router_name = router.get("name")
    if router_name != "global-skill-router":
        errors.append(
            _err(
                "ROUTER_ID_INVALID",
                router_name,
                "the active router must be named global-skill-router",
            )
        )
    if router.get("entrypoint") is not True or not isinstance(router.get("scenarios"), list) or not router.get("scenarios"):
        errors.append(
            _err(
                "ROUTER_ACTIVATION_INVALID",
                router_name,
                "active router must be entrypoint=true and declare at least one scenario",
            )
        )

    direct = router.get("composed_of") if isinstance(router.get("composed_of"), list) else []
    direct_names = {value for value in direct if isinstance(value, str)}
    active_modules = [
        entry for entry in valid_entries
        if entry.get("status") == "active" and entry.get("deployment_role") == "module"
    ]
    for entry in active_modules:
        name = entry.get("name")
        if entry.get("entrypoint") is True and name not in direct_names:
            errors.append(
                _err(
                    "ROUTER_MODULE_UNCOVERED",
                    name,
                    "active entrypoint module must appear in router composed_of",
                )
            )

    graph = {
        entry.get("name"): [
            ref for ref in (entry.get("composed_of") or [])
            if isinstance(ref, str)
        ]
        for entry in valid_entries
    }
    reachable = set()
    pending = list(direct_names)
    while pending:
        current = pending.pop()
        if current in reachable:
            continue
        reachable.add(current)
        pending.extend(graph.get(current, []))
    for entry in active_modules:
        if entry.get("entrypoint") is False and entry.get("name") not in reachable:
            errors.append(
                _err(
                    "MODULE_UNREACHABLE",
                    entry.get("name"),
                    "active non-entrypoint module is not reachable from router composed_of",
                )
            )


def _build_routes(skills, adapters):
    routes = {
        scenario: {"skills": [], "adapters": []}
        for scenario in sorted(VALID_SCENARIOS)
    }
    for entry in skills:
        if not isinstance(entry, dict):
            continue
        for scenario in entry.get("scenarios", []) if isinstance(entry.get("scenarios"), list) else []:
            if scenario in routes:
                routes[scenario]["skills"].append({"name": entry.get("name"), "status": entry.get("status")})
    for entry in adapters:
        if not isinstance(entry, dict):
            continue
        for scenario in entry.get("environments", []) if isinstance(entry.get("environments"), list) else []:
            if scenario in routes:
                routes[scenario]["adapters"].append(
                    {
                        "name": entry.get("name"),
                        "status": entry.get("status"),
                        "owner_skill": entry.get("owner_skill"),
                    }
                )
    for route in routes.values():
        route["skills"] = sorted(route["skills"], key=lambda item: (item.get("name") or "", item.get("status") or ""))
        route["adapters"] = sorted(route["adapters"], key=lambda item: (item.get("name") or "", item.get("status") or ""))
    return routes


def _route_errors(routes):
    errors = []
    for scenario, route in routes.items():
        if not route["skills"] and not route["adapters"]:
            errors.append(_err("SCENARIO_UNROUTED", scenario, f"scenario has no registered skill or adapter: {scenario}"))
    return errors


def validate(manifest_path):
    """Run the full schema-v3 control-plane check and return its report."""
    manifest_path = Path(manifest_path)
    errors = []
    loaded = _load_manifest(manifest_path, errors)
    if loaded is None:
        return _report(False, str(manifest_path), 0, errors)
    root = manifest_path.resolve().parents[2]
    sources = loaded.get("sources", [])
    entries = loaded.get("skills", [])
    adapters = loaded.get("adapters", [])

    source_ids = []
    for index, source in enumerate(sources):
        errors.extend(_source_errors(source, index, root))
        if isinstance(source, dict) and isinstance(source.get("id"), str):
            source_ids.append(source["id"])
    for source_id in sorted({value for value in source_ids if source_ids.count(value) > 1}):
        errors.append(_err("DUPLICATE_SOURCE_ID", source_id, "duplicate source id in manifest"))

    all_names = [
        entry.get("name")
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("name"), str)
    ]
    seen = set()
    duplicates = set()
    for entry_name in all_names:
        if entry_name in seen:
            duplicates.add(entry_name)
        seen.add(entry_name)
    for index, entry in enumerate(entries):
        _check_skill_entry_v2(entry, index, root, errors)
    for duplicate in sorted(duplicates):
        errors.append(_err("DUPLICATE_NAME", duplicate, "duplicate skill name in manifest"))
    _validate_edges(entries, errors)
    _deployment_errors(entries, errors)

    skill_statuses = {
        entry.get("name"): entry.get("status")
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("name"), str)
    }
    adapter_names = [
        entry.get("name")
        for entry in adapters
        if isinstance(entry, dict) and isinstance(entry.get("name"), str)
    ]
    for duplicate in sorted({value for value in adapter_names if adapter_names.count(value) > 1}):
        errors.append(_err("DUPLICATE_ADAPTER_NAME", duplicate, "duplicate adapter name in manifest"))
    for index, adapter in enumerate(adapters):
        errors.extend(_adapter_errors(adapter, index, root, skill_statuses))

    routes = _build_routes(entries, adapters)
    errors.extend(_route_errors(routes))

    scan_dir = manifest_path.parent
    if scan_dir.is_dir():
        registered = {entry.get("path") for entry in entries if isinstance(entry, dict)}
        for child in sorted(scan_dir.iterdir()):
            if child.is_dir():
                relative = child.relative_to(root).as_posix()
                if relative not in registered:
                    errors.append(
                        _err(
                            "UNREGISTERED_SKILL",
                            child.name,
                            f"directory under development/skill/ has no manifest entry: {relative}",
                        )
                    )
    return _report(
        not errors,
        str(manifest_path),
        len(entries),
        errors,
        sources_checked=len(sources),
        adapters_checked=len(adapters),
        routes=routes,
    )


def main(argv=None):
    args = parse_args(argv)
    report = validate(args.manifest)
    for error in report["errors"]:
        print(f"{error['code']} {error['skill']}: {error['message']}", file=sys.stderr)
    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
