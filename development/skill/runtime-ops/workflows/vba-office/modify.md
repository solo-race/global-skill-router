# VBA Modify Workflow

Use for an authorized change to existing VBA or Ribbon XML. Apply the loaded
module contract (source `SKILL.md`, deployed payload `MODULE.md`) and
`adapters/vba-office.md` for target permission, ownership, whole-artifact
writes, backup/recovery, and operator handoff. All paths resolve from the
`runtime-ops` root.

## Sequence

1. Read the current complete target module/XML before planning a replacement;
   a partial excerpt is sufficient for local reasoning only when the complete
   current content is already available.
2. Map affected callbacks and load only their references. Access uses
   `references/vba-office/access/form-lifecycle.md`,
   `references/vba-office/access/controls.md`,
   `references/vba-office/access/record-navigation.md`,
   `references/vba-office/access/form-state.md`, or
   `references/vba-office/access/dao.md`,
   according to the change. Excel uses the corresponding files under
   `references/vba-office/excel/` for ownership, worksheet events, UserForms,
   Ribbon XML, or add-ins. Load shared error-handling/encoding references
   only when relevant.
3. Define expected inputs, outputs, state transitions, error/cancel paths, and
   the narrow runtime acceptance check. Inspect the original source with the
   host policy in the adapter.
4. Prepare the minimum patch. Preserve unrelated code and host event
   signatures/parameters; do not delete or replace existing business modules
   unnecessarily. Whole-module transport does not authorize wholesale
   behavioral rewriting.
5. Complete the adapter's backup preconditions, then write the intended
   complete replacement. Use a new standard/class module only when the design
   actually requires one. Keep document-module edits direct; do not import
   `.dcm` exports as ordinary modules. Apply the separate Ribbon write policy
   when XML changes.
6. Reread the artifact and compare it with the intended patch and saved
   original. Run host-correct lint on the changed source, then the narrow
   verification sequence in `workflows/vba-office/test.md`.
7. If a required write or verification fails, follow the adapter's recovery
   sequence: restore the saved original through the matching tool and reread
   it to confirm restoration. Preserve the original failure in the report.

## Host interpretation and stop/resume

For Access, preserve form/control event binding and distinguish data-state
changes from navigation. For Excel, qualify workbook/worksheet/range targets
and restore captured application flags on both success and error; load
`references/vba-office/shared/error-handling.md` when those paths change.

An operator-only prerequisite or acceptance action stops this sequence before
that step and all dependent writes/checks. Use the adapter's handoff/resume
contract; do not treat confirmation as machine-observed behavior.

Report changed artifacts, the minimum behavioral change, backup/recovery
outcome, and Static/Compile/Runtime/Operator-observed results separately.
