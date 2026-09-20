"""P6 M5 static parity contracts; these tests provide no Office runtime evidence."""

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = REPO_ROOT / "development" / "skill"
RUNTIME_ROOT = SKILL_ROOT / "runtime-ops"


def _read(relative):
    return (RUNTIME_ROOT / relative).read_text(encoding="utf-8")


def _section(text, heading):
    assert heading in text, f"Missing contract section: {heading}"
    return text.split(heading, 1)[1].split("\n## ", 1)[0]


def _requires(text, *clauses):
    # Ignore Markdown wrapping without snapshotting entire knowledge documents.
    normalized = " ".join(text.split())
    for clause in clauses:
        assert clause in normalized, f"Missing decision contract: {clause}"


@pytest.fixture(scope="module")
def adapter():
    return _read("adapters/vba-office.md")


def test_mutation_requires_exact_dev_target_and_complete_evidence(adapter):
    mutation = _section(adapter, "## 5. Mutation model")
    _requires(
        mutation,
        "explicit user-requested VBA modification",
        "identified exact development/test target",
        "never authorizes production/authoritative targets",
        "stop if target status or identity is uncertain",
        "same target boundary to runtime calls with mutation effects",
        "Read the complete current module/artifact before replacement or removal",
        "smallest necessary complete replacement",
        "Confirm a recoverable path before mutation",
        "reread the affected source",
        "run host-correct static analysis",
        "perform narrow runtime verification on the development/test target",
        "report unavailable evidence as unverified",
    )


def test_whole_replacement_requires_confirmed_backup_and_verified_recovery(adapter):
    recovery = _section(adapter, "## 7. Recovery model")
    _requires(
        recovery,
        "Read the complete current content",
        "Store it as text under a repo-local `backups/` directory",
        "Confirm the backup file exists on disk before mutating",
        "reread via the matching getter",
        "On failed write or failed required verification",
        "restore the stored text through the SAME tool",
        "reread to confirm restoration",
        "report the original failure verbatim",
        "Stop conditions: fixture missing; backup unconfirmed",
    )


def test_structured_dialog_failure_requires_operator_handoff(adapter):
    mutation = _section(adapter, "## 5. Mutation model")
    _requires(
        mutation,
        "Structured dialog discovery/control failure is operator-only",
        "Stop and hand off the exact target, operation, failure, and available evidence",
        "never fall back to foreground-window actions or generic desktop automation",
    )


def test_access_focus_and_record_navigation_keep_runtime_semantics():
    _requires(
        _read("references/vba-office/access/controls.md"),
        "`.Text` / `.Value` semantics",
        "requires the control to have the focus; otherwise a runtime error occurs",
        "Move focus with `SetFocus` first, or use `.Value`",
        "Never mechanically replace one with the other",
        "it cannot be determined from source code alone",
    )
    _requires(
        _read("references/vba-office/access/record-navigation.md"),
        "`RecordsetClone` search that intends to move the form must end in the Bookmark assignment",
        "Always check NoMatch after FindFirst",
        "Locate records by key via `FindFirst`, never by `GoToRecord` offsets computed from IDs",
    )


def test_access_dirty_newrecord_and_dao_preserve_state_boundaries():
    _requires(
        _read("references/vba-office/access/form-state.md"),
        "`Dirty` — unsaved edits exist on the current record",
        "`NewRecord` — the current record is a new, not-yet-saved row",
        "each is a runtime fact, not a source-code fact",
        "Requery, Refresh, Repaint are distinct operations",
        "an identified synthetic/dev `.accdb` fixture",
    )
    _requires(
        _read("references/vba-office/access/dao.md"),
        "Keep the data-access path (`CurrentDb.OpenRecordset`) distinct from the form-bound objects",
        "Empty Recordsets require BOF/EOF handling",
        "Branch on `NoMatch` immediately after any `Find` method",
        "A write is not complete until `Update` succeeds",
        "Use a cleanup path that runs on both success and error",
        "Identify the workspace boundary before claiming a transaction protects only one database",
    )


def test_excel_ownership_and_event_reentry_keep_host_specific_guidance():
    _requires(
        _read("references/vba-office/excel/workbook-worksheet-model.md"),
        "`ThisWorkbook` is the add-in and `ActiveWorkbook` is the caller",
        "Use an explicitly identified workbook for a caller's data",
        "Qualify the Workbook -> Worksheet -> Range chain",
        "Treat any unqualified range access as a review finding until its intended owner is established",
    )
    _requires(
        _read("references/vba-office/excel/worksheet-events.md"),
        "Event handlers can re-enter after writing cells",
        "Capture the prior `EnableEvents` value before changing it",
        "restore that captured value on success and error rather than unconditionally writing `True`",
        "Do not remove an apparently unused event parameter",
    )


def test_ribbon_and_xlam_artifacts_do_not_substitute_for_runtime_evidence():
    _requires(
        _read("references/vba-office/excel/ribbon-xml.md"),
        "Review Ribbon XML separately from VBA source",
        "Look up each callback's member-specific signature",
        "verify Ribbon loading and callback behavior independently",
        "Report XML verification and VBA runtime verification as separate evidence",
    )
    _requires(
        _read("references/vba-office/excel/addin-xlam.md"),
        "Before file-level import/overwrite of an `.xlam`, confirm Excel is not holding the file open",
        "Never import a document-module export as if it were a standard `.bas` module",
        "A successful source write does not prove Excel can load the add-in or execute its callback",
        "registered compile operation reports `unverified` after dispatch",
    )


def test_saveastext_classification_gates_parser_and_workspace_inputs():
    _requires(
        _read("references/vba-office/access/saveastext-source.md"),
        "mixed object dump, not a native VBA export",
        "Only that extracted text may be passed as `code` to `vba_parse` or `vba_inspect`",
        "has no VBA section and do not call parser/lint",
        "`source extraction unresolved`. Stop the parser/lint path",
        "`ready`, `no_vba`, and `unresolved` states are intentionally distinct",
        "Do not rename or copy the original `.txt` into a vba-lint workspace",
        "Regression cases are synthetic strings and temporary files",
    )


def test_documented_fixtures_are_synthetic_local_only_and_missing_is_a_stop(adapter):
    # Read-only migration provenance; deployed workflows use the adapter policy.
    provenance_root = REPO_ROOT / "references" / "access-vba-dev"
    testing = (provenance_root / "docs" / "testing.md").read_text(encoding="utf-8")
    controlled = _section(testing, "## Controlled Fixtures")
    _requires(
        controlled,
        "The repository references two synthetic targets",
        "test-fixtures/access/ArmostQuote_Test.accdb",
        "test-fixtures/excel/Armost_Quote_Test.xlsm",
        "Both binaries are local-only assets excluded by `.gitignore`",
        "a fresh clone must provision them locally before running any fixture-backed verification",
    )
    ignored = (provenance_root / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "test-fixtures/access/*.accdb" in ignored
    assert "test-fixtures/excel/*.xlsm" in ignored
    _requires(
        _section(adapter, "## 10. Fixture policy"),
        "Controlled synthetic fixtures (`.accdb` / `.xlsm`) are local-only assets",
        "confirm existence at the recorded path",
        "if absent, STOP fixture-backed verification",
        "never silently substitute production files",
        "temporary smoke functions are added, run, reread, then removed",
        "Do not modify a fixture to manufacture a passing result",
    )
    _requires(
        _read("workflows/vba-office/test.md"),
        "do not substitute a production or authoritative file",
        "Report Static, Compile, Runtime, and Operator-observed independently",
        "achieved or unverified with reasons",
    )


def test_non_office_and_unrelated_host_tasks_do_not_preload_vba_knowledge(adapter):
    router = (SKILL_ROOT / "global-skill-router" / "SKILL.md").read_text(encoding="utf-8")
    _requires(
        router,
        "read zero scenario shards, and stop routing",
        "Read only that scenario's registered shard",
        "report `ROUTE_NO_MATCH` and continue without loading a managed module",
        "Never scan `library/`, glob module paths, or pre-read unselected modules",
    )
    _requires(
        _read("SKILL.md"),
        "Load only the adapter matching the current host and toolchain",
    )
    _requires(
        _section(adapter, "### Lazy-load index"),
        "Load only the selected workflow and references needed for the identified host and question",
        "never scan or preload the whole `references/vba-office` tree",
        "Load the other host's references only for an explicit cross-host question",
    )
