---
adapter_schema_version: 1
adapter: vba-office
environments: [win-access-vba]
capabilities: [source.read, source.write, source.static-analyze, project.compile, runtime.execute, ui.dialog-control]
task_modes:
  closed: false
  modes: [diagnose, review, modify, test]
verification_model_kind: linear
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
| project.compile | compile_vba_project — Excel host only |
| runtime.execute | run_macro, get_macro_result |
| ui.dialog-control | check_dialog, dismiss_dialog; screenshot as optional visual aid |

## 3. Operations

### Host and file identity

`app_type` accepts only `"excel"` (default) or `"access"`. Excel sessions are identified by workbook name as returned by `open_workbook` (e.g., `Book1.xlsm`). Access databases run in separate `Access.Application` instances identified by normalized database path.

### Session and module tools

| Tool | Signature | Contract |
|---|---|---|
| open_workbook | file_path: str | Opens `.xlsm`/`.xlsb`/`.xlsx`; returns workbook name/path/status. |
| open_database | file_path: str | Opens `.accdb`/`.mdb`; returns path/status. |
| close_file | file_name: str, app_type="excel", save=True | Excel expects workbook name; Access expects database path. Choose `save` deliberately. |
| list_open_files | — | Returns `{excel: [...], access: [...]}`. |
| list_vba_modules | file_name: str, app_type="excel" | Module metadata including module type. |
| get_vba_code | file_name: str, module_name: str, app_type="excel" | Complete module source; empty module returns `(コードなし)`. |
| set_vba_code | file_name: str, module_name: str, code: str, app_type="excel" | **Whole-module replacement**: deletes every existing line before inserting `code`; returns module + line count. |
| add_vba_module | file_name: str, module_name: str, module_type="Standard", code="", app_type="excel" | Only names `Standard` and `ClassModule` are addable (never numeric IDs). Types: 1 Standard, 2 ClassModule, 3 Form, 100 Document. |
| remove_vba_module | file_name: str, module_name: str, app_type="excel" | Refuses type-100 document modules (`ThisWorkbook`, worksheet/document modules). |

### XML and export tools

| Tool | Signature | Contract |
|---|---|---|
| get_ribbon_xml | file_path: str | Reads `customUI/customUI.xml` or `customUI14/customUI14.xml` without opening the workbook; CP932 decode; absent → `no_custom_ui`. |
| set_ribbon_xml | file_path: str, xml: str, close_if_open=False | Rewrites the custom UI ZIP entry as CP932. Workbook open: default `False` returns an error; `True` saves and closes first. Never creates a missing custom UI part. A successful write does not prove Excel loaded the Ribbon. |
| sync_to_src | file_path: str, dest_dir: str, close_after=True | Exports `.bas`, `.cls`, `.frm`+`.frx`, `.dcm`; reports orphaned VBA files without deleting them. |

### Compile, execution, dialogs

- `compile_vba_project(file_name)` — **Excel only**; no `app_type` parameter. Opens VBE and runs Debug → Compile; returns `{status: ok/error, ...}`.
- `run_macro(file_name, macro_name, args=None, app_type="excel", timeout=10.0)` — runs in a worker; the implementation signature is authoritative even though a docstring says "default 3 seconds". Excel: `Application.Run` on `'WorkbookName'!MacroName`. Access: without args uses `Application.Eval("MacroName()")`; with args uses `Application.Run(macro_name, *args)`. The validated Access smoke harness is a **no-argument `Public Function` invoked through Eval** — do not substitute a parameterized macro or an ordinary `Public Sub`.
- Timeout returns `{status: "running", request_id}`. Resolution sequence: `check_dialog(app_type="excel"` or `app_type="access", file_name=<database path>`)` → `dismiss_dialog(dialog_hwnd, button_text=<exact text>, input_text optional, entered before clicking)` (`button_text` required in practice) → `get_macro_result(request_id, app_type)` → report returned status/result/error. Structured dialog results only; `screenshot(save_path)` (Excel only) is optional visual evidence for layout/Ribbon appearance, never a substitute.
- GitHub-token registry tools exist (get/set/list). Out of scope unless the task explicitly concerns GitHub token configuration; never place a returned token in logs or source files.

## 4. Preconditions and failures

- The VBA project-object-model trust setting must be enabled in both hosts. Otherwise module operations return trust-setting guidance, and compile attempts fail with COM error `-2146827284`. Such permission failures downgrade achievable verification to Static; preserve the guidance verbatim and never relabel it compile/runtime evidence.
- Missing file → file-not-found error; missing module → value error. Preserve actual messages.
- `set_ribbon_xml` against an open workbook with default `close_if_open=False` errors by design — an explicit choice is required.

## 5. Mutation model

State-changing operations: `set_vba_code` (whole-module replacement), `add_vba_module`, `remove_vba_module`, `set_ribbon_xml` (whole-part replacement), `close_file(save=True)`. Granularity is whole artifact — no line-level patching exists. Blast radius: an entire module or the entire custom UI part. Never touch production files when a development/test fixture is intended.

## 6. Verification model (linear: Static → Compile → Runtime)

| State | Required evidence | Does not prove |
|---|---|---|
| Static | Changed module reread via `get_vba_code` matches the intended patch AND `vba_parse`/`vba_inspect` accept it with the host's `hostLibraries` value. | Compilation, event binding, focus, form/workbook state, active-object targets, runtime outcome. |
| Compile | `compile_vba_project` returns `status: ok` for the actually open workbook — **Excel only**. For Access this state is **unsupported through the registered vba-doctor API**: always report `compile: unverified via vba-doctor`, even when the Eval-based smoke succeeds. | Behavioral correctness; Ribbon actually loaded. |
| Runtime | Targeted `run_macro` completes; expected result/state observed; any dialog resolved through structured tools. | Anything beyond the exercised path. |

`unsupported`: [Access compile] — reason: no registered operation provides that evidence. A successful source write or clean lint result alone is never compile/runtime evidence. Only the highest achieved level may be reported (linear model).

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

- Access lint calls pass `hostLibraries: ["access"]`.
- Excel lint calls pass `hostLibraries: ["Excel"]`.

Casing: `vba_inspect` / `vba_inspect_workspace` match host libraries case-insensitively; only `vba_list_inspections` filters its catalog case-sensitively. The values above are correct everywhere. Pass `app_type` explicitly per call likewise.

vba-lint notes: `vba_parse(code, depth=3, range 1-10)` → AST serialization; structure/syntax understanding only. `vba_inspect(code, hostLibraries=["excel"] default, severity error/warning/suggestion/hint, categories)` → `results`, `errors`, `skippedInspections`, `parseErrors`, engine version. `vba_inspect_workspace(path, hostLibraries=["excel"], severity?, categories?, limit=100, detailed=false)` → scans `.bas`/`.cls`/`.frm` sources; aborts above 500 candidate files — narrow the path or extend `.vbalintignore`. `vba_list_inspections(hostLibraries?, category?, tier "A"|"B")` → tier A parse-tree inspections, tier B symbol-aware. Treat the live catalog response as authoritative; never hardcode inspection counts. Lint is static evidence only: it cannot prove compilation, event binding, focus, form state, active-object targets, or runtime outcomes. Interpret findings through the selected host's semantics; never delete host-called event procedures because lint reports them unused. Scan exported/retrieved source only — binary fixtures are not parser inputs.

## 9. Task routing

Preferred modes: **diagnose** (reported defect, unexpected behavior, uncertain runtime state), **review** (two-layer audit: generic VBA correctness, then selected-host semantics), **modify** (existing-code change; read the complete target module first; smallest behavior-preserving patch; no unrelated cleanup), **test** (behavioral verification via deterministic entry points with structured evidence capture).

`closed: false`. Intents such as build-new, refactor, or migration belong to none of these modes; route them through the Core operation lifecycle rather than forcing them into a mode. Mode workflows may specialize lifecycle steps but never weaken Core safety invariants.

## 10. Fixture policy

Controlled synthetic fixtures (`.accdb` / `.xlsm`) are local-only assets excluded by `.gitignore`; they are never committed, and a fresh clone must provision them before any fixture-backed verification. Before opening either kind, confirm existence at the recorded path; if absent, STOP fixture-backed verification, report the missing fixture as the blocker, and ask the operator how to proceed — never silently substitute production files. Never alter a fixture permanently for a one-off test: temporary smoke functions are added, run, reread, then removed. Do not modify a fixture to manufacture a passing result (e.g., an Excel compile failure caused by fixture references is recorded, not fixed).

## 11. Source priority instance

1. Microsoft object-model reference for the selected host (Access claims vs. Excel claims use their own reference); 2. the other host's object-model reference, only for cross-host claims; 3. Microsoft DAO Reference; 4. Microsoft VBA Language Reference; 5. controlled experiments via fixtures through vba-doctor tools; 6. vba-lint generic static analysis (generic VBA only, never runtime state); 7. community sources, discovery only. A lower-priority source never overrides a higher-priority one for the same claim.

## 12. Provenance

Design references (development-time, read-only, NOT runtime dependencies): `references/access-vba-dev/skill/tool-contracts/vba-doctor.md`, `references/access-vba-dev/skill/tool-contracts/vba-lint.md`, `references/access-vba-dev/skill/workflows/` (diagnose/review/modify/test), `references/access-vba-dev/skill/references/shared/sources.md`, `references/access-vba-dev/docs/testing.md`. Deployed use of this adapter requires nothing outside the `runtime-ops` skill directory.
