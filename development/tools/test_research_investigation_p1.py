"""Behavioral/decision regression tests for the P1 research-investigation contract.

These pin the decisions fixed by plan 020 and its P1 fix batch (BUG-P1-1..5):
activation gate reality, vocabulary_authority selection, the closed profile ABI,
the unique output position of ``unknown``, and Core domain neutrality. They run
against the real skill tree in this repository.
"""

import importlib.util
import re
from pathlib import Path

import yaml

_SPEC = importlib.util.spec_from_file_location(
    "validate_skills_under_test",
    Path(__file__).with_name("validate_skills.py"),
)
validate_skills = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(validate_skills)

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = REPO_ROOT / "development" / "skill" / "research-investigation"
PROFILE_PATH = SKILL_DIR / "profiles" / "recycling-company.yaml"
CORE_PATHS = list(SKILL_DIR.glob("references/*.md")) + [SKILL_DIR / "SKILL.md"]

# Domain vocabulary and consuming-project identifiers that must never leak into
# the Core (plan 020 §6 item 2). They are allowed only inside profiles/.
BANNED_CORE_TOKENS = (
    "recycling",
    "weee",
    "elv",
    "plastic",
    "polymer",
    "customer_screening",
    "config/search_terms.yaml",
    "company_result.schema.json",
    "sourcerecord",
    "evidencelink",
)

_WHEN_UNAVAILABLE_STATES = frozenset({"review_packet_only", "use_profile_vocabulary_only"})


def _read(path):
    return path.read_text(encoding="utf-8")


def test_recycling_profile_passes_activation_gate():
    errors = validate_skills.profile_errors(PROFILE_PATH)
    assert errors == []


def test_vocabulary_authority_selects_its_binding():
    profile = yaml.safe_load(_read(PROFILE_PATH))
    authority = profile["vocabulary_authority"]
    assert isinstance(authority, str)
    binding = profile["project_bindings"][authority]
    assert binding["owner"] == "consuming_project"
    assert binding["required"] is False
    assert binding["when_unavailable"] == "use_profile_vocabulary_only"
    assert "config/search_terms.yaml" in binding["reference"]


def test_all_bindings_degrade_legally_for_standalone_run():
    profile = yaml.safe_load(_read(PROFILE_PATH))
    assert profile["project_bindings"]
    for key, binding in profile["project_bindings"].items():
        assert binding.get("required") is False, f"binding {key} must stay optional"
        assert binding["when_unavailable"] in _WHEN_UNAVAILABLE_STATES, (
            f"binding {key} has unknown degradation {binding['when_unavailable']!r}"
        )
    # Standalone review packet must always be a legal terminal output.
    pipeline = profile["pipeline_binding"]
    assert pipeline["mode"] == "canonical_candidates_when_supplied"
    assert "Fact-candidate" in pipeline["produces"]
    assert "Score" in pipeline["never_promotes_to"]


def test_packet_extensions_confined_to_profile_extensions():
    profile = yaml.safe_load(_read(PROFILE_PATH))
    for key, extension in profile["packet_extensions"].items():
        placed_at = extension["placed_at"]
        assert placed_at.startswith("profile_extensions."), key
        assert len(placed_at) > len("profile_extensions."), key


def test_load_bearing_guidance_lives_in_profile_guidance_namespace():
    profile = yaml.safe_load(_read(PROFILE_PATH))
    guidance = profile["profile_guidance"]
    for block in ("language_policy", "domain_model", "terminology_map"):
        assert block in guidance, f"missing guidance block {block}"
        assert isinstance(guidance[block], dict)
    # The old free-floating top-level sections must be gone.
    for block in ("language_policy", "domain_model", "terminology_map"):
        assert block not in profile, f"top-level {block} must not exist outside the namespace"


def test_display_remains_presentation_only():
    profile = yaml.safe_load(_read(PROFILE_PATH))
    assert set(profile["display"]) == {"display_name", "short_description"}


def test_unknown_routing_consistent_skil_and_references():
    skill = _read(SKILL_DIR / "SKILL.md").lower()
    rules = _read(SKILL_DIR / "references" / "evidence-rules.md").lower()
    schema = _read(SKILL_DIR / "references" / "output-schema.md").lower()
    # findings admit exactly three states; unknown never becomes a finding.
    assert "one of `confirmed`, `inferred`, or `conflicting`" in schema
    assert "never becomes a finding" in schema
    assert "`unknown` never becomes a finding" in rules
    assert "never a finding" in skill
    # evidence_gaps is the single home of unknown.
    assert "state` (always `unknown`)" in schema
    # failed/partial retrieval may explain gaps but never resolve them.
    assert re.search(r"failed or partial retrieval\s+explains a gap; it never resolves one", schema)
    # unknown is epistemic, not negative.
    assert 'never means "no"' in rules
    assert "a negative derived from missing or failed retrieval" in schema
    assert "never write definitive negatives solely because a search failed" in rules
    # forbidden wording that would let unknown leak into findings.
    assert "finding is unknown" not in rules
    assert "finding is unknown" not in schema
    assert "one of the four states;one of" not in schema


def test_core_is_domain_neutral():
    offenders = []
    for path in CORE_PATHS:
        text = _read(path).lower()
        for token in BANNED_CORE_TOKENS:
            if token in text:
                offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")
    assert offenders == []


def test_synthetic_software_project_profile_needs_no_core_change(tmp_path):
    """Orthogonality probe (plan 020 §6 item 5): a heterogeneous profile with no
    recycling vocabulary, no company operations, no input->operation->output, no
    Acquisition->...->Score pipeline and no customer_screening bindings must pass
    the contract gate without any Core modification."""
    profile = {
        "profile_schema_version": 1,
        "domain": "software-project",
        "subject_type": "software-project",
        "investigation_dimensions": [
            {
                "id": "identity",
                "purpose": "Establish canonical identity, namespace ownership, and naming history.",
            },
            {
                "id": "ownership",
                "purpose": "Determine the owning organization and maintainer model.",
            },
            {
                "id": "release-status",
                "purpose": "Establish released versions, channels, and deprecation or archival signals.",
            },
            {
                "id": "dependency-relationship",
                "purpose": "Map declared dependencies and reverse dependents that change adoption risk.",
            },
        ],
        "concept_groups": {
            "identity": ["repository", "package", "changelog"],
            "ownership": ["author", "organization", "maintainers"],
            "release-status": ["release", "version", "deprecated", "archived"],
            "dependency-relationship": ["dependency", "dependents", "license"],
        },
        "query_examples": [
            '"Project" repository changelog',
            '"Project" maintainers organization',
            '"Project" release deprecation',
        ],
        "vocabulary_authority": None,
        "packet_extensions": {
            "adoption_notes": {
                "placed_at": "profile_extensions.adoption_notes",
                "fields": {},
            }
        },
        "pipeline_binding": None,
        "project_bindings": {},
        "display": {
            "display_name": "Software Project Investigation",
            "short_description": "Evidence-first open-source project research",
        },
    }
    probe = tmp_path / "software-project.yaml"
    probe.write_text(yaml.safe_dump(profile, sort_keys=False), encoding="utf-8")
    errors = validate_skills.profile_errors(probe)
    assert errors == []


def test_malformed_profile_cannot_pass_activation_gate(tmp_path):
    """An unknown load-bearing top-level field must fail the manifest-level gate."""
    skill_dir = tmp_path / "development" / "skill" / "research-investigation"
    (skill_dir / "profiles").mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: research-investigation\n"
        "description: Profile probe. Use when probing.\n---\n\nBody.\n",
        encoding="utf-8",
    )
    (skill_dir / "profiles" / "alpha-domain.yaml").write_text(
        yaml.safe_dump(
            {
                "profile_schema_version": 1,
                "domain": "alpha-domain",
                "subject_type": "company",
                "investigation_dimensions": [
                    {"id": "identity", "purpose": "Establish identity."}
                ],
                "concept_groups": {},
                "query_examples": [],
                "scoring_policy": {"weight": 1},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / "development" / "skill" / "manifest.yaml"
    router_dir = tmp_path / "development" / "skill" / "global-skill-router"
    router_dir.mkdir(parents=True, exist_ok=True)
    (router_dir / "SKILL.md").write_text(
        "---\nname: global-skill-router\n"
        "description: Probe router. Use when selecting a module.\n"
        "---\n\nRouter body.\n",
        encoding="utf-8",
    )
    (router_dir / "agents").mkdir(parents=True, exist_ok=True)
    (router_dir / "agents" / "openai.yaml").write_text(
        "interface:\n"
        "  display_name: Router\n"
        "  short_description: Probe router\n"
        "  default_prompt: Load $global-skill-router.\n",
        encoding="utf-8",
    )
    manifest.write_text(
        yaml.safe_dump(
                {
                    "schema_version": 4,
                    "sources": [],
                    "skills": [
                        {
                            "name": "research-investigation",
                            "path": "development/skill/research-investigation",
                            "status": "active",
                            "deployment_role": "module",
                            "deployment_role": "module",
                            "routing_priority": 0,
                            "routing_outcome": "terminal",
                            "scenarios": ["win-access-vba", "win-android", "wsl-python"],
                            "deps": [],
                            "composed_of": [],
                            "entrypoint": False,
                            "version": "0.1.0",
                            "description": "Probe skill.",
                        },
                        {
                            "name": "global-skill-router",
                            "path": "development/skill/global-skill-router",
                            "status": "active",
                            "deployment_role": "router",
                            "scenarios": ["win-access-vba", "win-android", "wsl-python"],
                            "deps": [],
                            "composed_of": ["research-investigation"],
                            "entrypoint": True,
                            "version": "0.1.0",
                            "description": "Probe router.",
                        },
                    ],
                    "adapters": [],
                },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    report = validate_skills.validate(manifest)
    assert report["ok"] is False
    assert any(
        error["code"] == "PROFILE_UNKNOWN_FIELD" for error in report["errors"]
    )


def test_repo_activation_gate_is_live():
    """The real manifest stays green only because the real profile passed the gate."""
    report = validate_skills.validate(validate_skills.DEFAULT_MANIFEST)
    assert report["ok"] is True
    assert report["errors"] == []
