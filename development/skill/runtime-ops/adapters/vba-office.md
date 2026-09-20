---
adapter_schema_version: 1
adapter: vba-office
environments: [win-access-vba]
capabilities: [source.read, source.write, source.static-analyze, project.compile, runtime.execute, ui.dialog-control]
task_modes:
  closed: false
  modes: [diagnose, review, modify, test]
verification_model_kind: independent_checks
mutation_support: high-impact
---

# vba-office Adapter

Contract for operating Microsoft Access and Excel VBA projects through the registered `vba-doctor` (Office COM automation MCP server; 21 registered tools; every tool returns a string, usually JSON; failures are Japanese `エラー: ...` strings) and `vba-lint` (static-analysis MCP server; four registered tools) servers. Self-sufficient: every fact needed to form correct calls, judge results, claim verification states, and recover mutations lives in this file.

## 1. Identity and source of truth

Providers: the deployed vba-doctor and vba-lint servers. Version: record the engine/submodule version returned with lint results; vba-doctor exposes no version query — note the deployment instead. Source of truth is the servers' registered tool implementations; this contract mirrors registration as observed, never an assumed API.

## 2. Capabilities

| Capability | Registered tools |
|---|---|
| source.read | open_workbook, open_database, list_vba_modules, get_vba_code, get_ribbon_xml, sync_to_src |
| source.write | set_vba_code, add_vba_module, remove_vba_module, set_ribbon_xml |
| source.static-analyze | vba_parse, vba_inspect, vba_inspect_workspace, vba_list_inspections |
| project.compile | compile_vba_project — Excel host only; dispatch-only/unverified |
| runtime.execute | run_macro, get_macro_result |
| ui.dialog-control | check_dialog, dismiss_dialog; screenshot as optional visual aid |

## 3. Operations

### Host and file identity

`app_type` accepts only `"excel"` (default) or `"access"`. Excel sessions are identified by workbook name as returned by `open_workbook` (e.g., `Book1.xlsm`). Access databases run in separate `Access.Application` instances identified by normalized absolute database path plus managed application HWND/PID. With multiple instances, never guess macro binding: establish the exact instance owning the target. Ambiguous ownership or a path/HWND/PID mismatch fails closed before execution. Asynchronous Access execution revalidates the HWND/PID and current database path after reacquiring the application.

### Session and module tools

| Tool | Signature | Contract |
|---|---|---|
| open_workbook | file_path: str, safe_inspection=False | Opens `.xlsm`/`.xlsb`/`.xlsx`; returns workbook name/path/status. Safe inspection behavior is defined below. |
| open_database | file_path: str | Opens `.accdb`/`.mdb`; returns path/status. |
| close_file | file_name: str, app_type="excel", save=True | Excel expects workbook name; Access expects database path. Choose `save` deliberately. |
| list_open_files | — | Returns `{excel: [...], access: [...]}`. |
| list_vba_modules | file_name: str, app_type="excel" | Module metadata including module type. |
| get_vba_code | file_name: str, module_name: str, app_type="excel" | Complete module source; empty module returns `(コードなし)`. |
| set_vba_code | file_name: str, module_name: str, code: str, app_type="excel" | **Whole-module replacement**: deletes every existing line before inserting `code`; returns module + line count. |
| add_vba_module | file_name: str, module_name: str, module_type="Standard", code="", app_type="excel" | Only names `Standard` and `ClassModule` are addable (never numeric IDs). Types: 1 Standard, 2 ClassModule, 3 Form, 100 Document. |
| remove_vba_module | file_name: str, module_name: str, app_type="excel" | Refuses type-100 document modules (`ThisWorkbook`, worksheet/document modules). |

`open_workbook(..., safe_inspection=True)` force-disables automatic macros (`AutomationSecurity=3`), suppresses link updates (`AskToUpdateLinks=False`, `UpdateLinks=0`), and opens a newly opened workbook read-only (`ReadOnly=True`). Prior application security/link settings are restored after the attempt, including failure. The default `False` preserves editable opening behavior. An already-open workbook is reused as-is: its security/read-only state is unchanged and the call does not newly grant managed-close ownership. Safe inspection cannot retroactively make that session safe; do not close it as cleanup unless it was already doctor-managed.

### XML and export tools

| Tool | Signature | Contract |
|---|---|---|
| get_ribbon_xml | file_path: str | Reads `customUI/customUI.xml` or `customUI14/customUI14.xml` without opening the workbook; CP932 decode; absent → `no_custom_ui`. |
| set_ribbon_xml | file_path: str, xml: str, close_if_open=False | Rewrites the custom UI ZIP entry as CP932. Workbook open: default `False` returns an error; `True` saves and closes first. Never creates a missing custom UI part. A successful write does not prove Excel loaded the Ribbon. |
| sync_to_src | file_path: str, dest_dir: str, close_after=True | Exports `.bas`, `.cls`, `.frm`+`.frx`, `.dcm`; reports orphaned VBA files without deleting them. |

### Compile, execution, dialogs

- `compile_vba_project(file_name)` — **Excel only**; no `app_type` parameter. Verifies the requested workbook/VBProject is the VBE active project, dispatches the VBE CommandBars compile command, and returns `status: "unverified"`. The provider has no reliable compiler-result channel; dispatch never establishes Compile Verified.
- `run_macro(file_name, macro_name, args=None, app_type="excel", timeout=10.0)` — runs in a worker; the implementation signature is authoritative even though a docstring says "default 3 seconds". Excel: `Application.Run` on `'WorkbookName'!MacroName`. Access: without args uses `Application.Eval("MacroName()")`; with args uses `Application.Run(macro_name, *args)`. The validated Access smoke harness is a **no-argument `Public Function` invoked through Eval** — do not substitute a parameterized macro or an ordinary `Public Sub`.
- Timeout returns `{status: "running", request_id}`. Resolution sequence: `check_dialog(app_type="excel"` or `app_type="access", file_name=<database path>`)` → `dismiss_dialog(dialog_hwnd, button_text=<exact text>, input_text optional, entered before clicking)` (`button_text` required in practice) → `get_macro_result(request_id, app_type)` → report returned status/result/error. Structured dialog results only; `screenshot(save_path)` (Excel only) is optional visual evidence for layout/Ribbon appearance, never a substitute.
- `check_dialog` authorizes only visible `#32770` dialogs owned by the selected Office window and process, recording owner HWND/PID and dialog identity. `dismiss_dialog` accepts only a discovered HWND and revalidates owner, process, class, contents, and child controls before every input/button mutation. Stale or mismatched provenance fails closed; stop for operator intervention instead of using foreground-window actions or generic desktop automation.
- GitHub-token registry tools exist (get/set/list). Out of scope unless the task explicitly concerns GitHub token configuration; never place a returned token in logs or source files.

## 4. Preconditions and failures

- For an in-scope task, source open/list/read and lint parse/inspect/workspace/catalog calls may proceed automatically. Use Excel safe inspection for read-only inspection and respect existing-session ownership; opening a file does not authorize source changes or business execution.
- The VBA project-object-model trust setting must be enabled in both hosts. Otherwise module operations return trust-setting guidance, and compile attempts fail with COM error `-2146827284`. Report affected checks as unverified; Static still requires its own evidence. Preserve the guidance verbatim and never relabel it compile/runtime evidence.
- Missing file → file-not-found error; missing module → value error. Preserve actual messages.
- `set_ribbon_xml` against an open workbook with default `close_if_open=False` errors by design — an explicit choice is required.

## 5. Mutation model

State-changing operations: `set_vba_code` (whole-module replacement), `add_vba_module`, `remove_vba_module`, `set_ribbon_xml` (whole-part replacement), `close_file(save=True)`. Granularity is whole artifact — no line-level patching exists. Blast radius: an entire module or the entire custom UI part.

Hard guards:

- Write only for an explicit user-requested VBA modification against an identified exact development/test target. This adapter never authorizes production/authoritative targets; stop if target status or identity is uncertain. Apply the same target boundary to runtime calls with mutation effects.
- Read the complete current module/artifact before replacement or removal. Preserve unrelated behavior, make only the smallest necessary complete replacement, and never delete or replace existing business modules unnecessarily. Confirm a recoverable path before mutation; whole replacements follow §7.
- After a change, reread the affected source, run host-correct static analysis, and perform narrow runtime verification on the development/test target; report unavailable evidence as unverified under §6.
- Structured dialog discovery/control failure is operator-only. Stop and hand off the exact target, operation, failure, and available evidence; never fall back to foreground-window actions or generic desktop automation.

## 6. Verification model (independent_checks)

| State | Required evidence | Does not prove |
|---|---|---|
| Static | Changed module reread via `get_vba_code` matches the intended patch AND `vba_parse`/`vba_inspect` accept it; inspection uses the host's explicit `hostLibraries` and `severity: "warning"`. | Compilation, event binding, focus, form/workbook state, active-object targets, runtime outcome. |
| Compile | Access compile is unsupported: no registered operation. Excel compile is a registered dispatch operation returning `status: "unverified"` without a reliable compiler-result channel. Report `compile: unverified via vba-doctor`; record Excel separately as `compile dispatch: unverified`. | Dispatch does not prove compiler success; runtime smoke does not supply compile evidence. |
| Runtime | Targeted `run_macro` completes; expected result/state observed; any dialog resolved through owned structured tools. | Static or Compile checks; anything beyond the exercised path. |
| Operator-observed | Explicit operator observation tied to the identified target and exercised action. | Static, Compile, or Runtime checks; authorization alone proves none of them. |

`relations: []`. `unsupported`: [Access compile] — no registered Access operation. Excel compile dispatch is supported but its result remains unverified. Report every check individually as achieved or unverified, naming unsupported checks; no check implies another. Lint findings are advisory; a successful source write, clean lint, compile dispatch, or operator authorization alone is never compile/runtime evidence.

## 7. Recovery model (repo-local text backup)

For every whole-replacement write (`set_vba_code`, `set_ribbon_xml`):

1. Read the complete current content (`get_vba_code` / `get_ribbon_xml`) before relying on any partial section.
2. Store it as text under a repo-local `backups/` directory excluded by `.gitignore`, at `backups/<host>/<file-stem>/<artifact>.<yyyyMMdd-HHmmss>.<ext>` (modules → `.txt`; Ribbon → `.xml`).
3. Confirm the backup file exists on disk before mutating; the tool creates no backup itself.
4. Make the smallest complete write; reread via the matching getter; compare against intended patch and backup.
5. On failed write or failed required verification: restore the stored text through the SAME tool (`set_vba_code` / `set_ribbon_xml`), reread to confirm restoration, and report the original failure verbatim.

Stop conditions: fixture missing; backup unconfirmed; failure whose recovery cannot restore prior content.

## 8. Environment and configuration

Windows plus desktop Office hosts; trust setting enabled. Access instances are keyed by normalized database path; Excel sessions by workbook name. Configuration injection: profiles are agent guidance only — neither server reads skill or profile files automatically, so pass values explicitly on every call:

- Access inspection calls pass `hostLibraries: ["access"]`, `severity: "warning"`.
- Excel inspection calls pass `hostLibraries: ["Excel"]`, `severity: "warning"`.

Casing: `vba_inspect` / `vba_inspect_workspace` match host libraries case-insensitively; only `vba_list_inspections` filters its catalog case-sensitively. Pass the same host value explicitly for catalog calls; they have no severity parameter. Inspection providers have no `warning` default: the agent must supply that policy value. `vba_parse` accepts neither host libraries nor severity. Pass `app_type` explicitly per host call likewise.

vba-lint notes: `vba_parse(code, depth=3, range 1-10)` → AST serialization; structure/syntax understanding only. `vba_inspect(code, hostLibraries=["excel"] default, severity error/warning/suggestion/hint, categories)` → `results`, `errors`, `skippedInspections`, `parseErrors`, engine version. `vba_inspect_workspace(path, hostLibraries=["excel"], severity?, categories?, limit=100, detailed=false)` → scans `.bas`/`.cls`/`.frm` sources; aborts above 500 candidate files — narrow the path or extend `.vbalintignore`. `vba_list_inspections(hostLibraries?, category?, tier "A"|"B")` → tier A parse-tree inspections, tier B symbol-aware. Treat the live catalog response as authoritative; never hardcode inspection counts. Lint is static evidence only: it cannot prove compilation, event binding, focus, form state, active-object targets, or runtime outcomes. Interpret findings through the selected host's semantics; never delete host-called event procedures because lint reports them unused. Scan exported/retrieved source only — binary fixtures are not parser inputs.

## 9. Task routing

Preferred modes: **diagnose** (reported defect, unexpected behavior, uncertain runtime state), **review** (two-layer audit: generic VBA correctness, then selected-host semantics), **modify** (existing-code change; read the complete target module first; smallest behavior-preserving patch; no unrelated cleanup), **test** (behavioral verification via deterministic entry points with structured evidence capture).

`closed: false`. Intents such as build-new, refactor, or migration belong to none of these modes; route them through the Core operation lifecycle rather than forcing them into a mode. Mode workflows may specialize lifecycle steps but never weaken Core safety invariants.

### Lazy-load index

Resolve all paths below from the `runtime-ops` skill root. Load only the selected workflow and references needed for the identified host and question; never scan or preload the whole `references/vba-office` tree. Load the other host's references only for an explicit cross-host question.

| Task | Load |
|---|---|
| diagnose | `workflows/vba-office/diagnose.md` + references for the suspected host behavior |
| review | `workflows/vba-office/review.md` + `references/vba-office/shared/sources.md` + references for the reviewed host behavior |
| modify | `workflows/vba-office/modify.md` + references for the affected host behavior |
| test | `workflows/vba-office/test.md`; add host references only when the test depends on their semantics |
| Access SaveAsText review | `references/vba-office/access/saveastext-source.md` + `scripts/vba-office/extract_access_saveastext.py`; classify/extract the source before parsing a mixed dump |

Select references by the actual question:

- Shared: evidence/source priority → `references/vba-office/shared/sources.md`; error cleanup/state restoration → `references/vba-office/shared/error-handling.md`; source encoding → `references/vba-office/shared/vba-encoding.md`.
- Access: event callbacks/lifecycle → `references/vba-office/access/form-lifecycle.md`; focus/control access → `references/vba-office/access/controls.md`; record movement → `references/vba-office/access/record-navigation.md`; Dirty/NewRecord state → `references/vba-office/access/form-state.md`; DAO → `references/vba-office/access/dao.md`.
- Excel: workbook/worksheet/range ownership → `references/vba-office/excel/workbook-worksheet-model.md`; events/re-entry → `references/vba-office/excel/worksheet-events.md`; UserForm → `references/vba-office/excel/userform-model.md`; Ribbon → `references/vba-office/excel/ribbon-xml.md`; add-ins → `references/vba-office/excel/addin-xlam.md`.

## 10. Fixture policy

Controlled synthetic fixtures (`.accdb` / `.xlsm`) are local-only assets excluded by `.gitignore`; they are never committed, and a fresh clone must provision them before any fixture-backed verification. Before opening either kind, confirm existence at the recorded path; if absent, STOP fixture-backed verification, report the missing fixture as the blocker, and ask the operator how to proceed — never silently substitute production files. Never alter a fixture permanently for a one-off test: temporary smoke functions are added, run, reread, then removed. Do not modify a fixture to manufacture a passing result (e.g., an Excel compile failure caused by fixture references is recorded, not fixed).

## 11. Source priority instance

For source-priority or conflict questions, load `references/vba-office/shared/sources.md` from the `runtime-ops` skill root. It owns the source policy; follow its claim-ownership and controlled-experiment rules.

## 12. Provenance

Design references (development-time, read-only, NOT runtime dependencies): `references/access-vba-dev/skill/tool-contracts/vba-doctor.md`, `references/access-vba-dev/skill/tool-contracts/vba-lint.md`, `references/access-vba-dev/skill/workflows/` (diagnose/review/modify/test), `references/access-vba-dev/skill/references/shared/sources.md`, `references/access-vba-dev/docs/testing.md`. Deployed use of this adapter requires nothing outside the `runtime-ops` skill directory.
