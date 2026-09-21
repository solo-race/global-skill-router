# VBA Review Workflow

Use for a code review or audit. Apply the loaded module contract (source
`SKILL.md`, deployed payload `MODULE.md`) and `adapters/vba-office.md` for
operation and evidence contracts. Paths resolve from the `runtime-ops` root.
Review has two interpretation layers: generic VBA, then owning-host
semantics.

## Sequence

1. Identify Access versus Excel, the owning module/object, and host callbacks
   even when no explicit VBA call site exists. Load
   `references/vba-office/shared/sources.md` and only the host references
   needed by the reviewed behavior. Analyze mixed-host repositories with
   separate host-correct inspections.
2. Retrieve complete relevant source or classify supplied artifacts. Native
   `.bas`, `.cls`, `.frm`, and `.dcm` exports differ from mixed Access
   SaveAsText `.txt` dumps. For a mixed dump, load
   `references/vba-office/access/saveastext-source.md` and use its extraction
   gate before any parser/lint call. Only a `ready` extracted VBA tail may be
   analyzed; report `no_vba` or `source extraction unresolved` unchanged and
   stop that parser path. Never pass the raw dump or renamed dump to lint.
3. Use parsing for syntax/structure questions and inspection for findings.
   Use workspace inspection for cross-module questions, requesting detailed
   results when locations/fixes matter. Consult the live catalog when a host
   filter or inspection is uncertain; record host policy and engine version.
4. Prioritize data/state errors, event re-entry, error handling, and cleanup
   over style suggestions. Interpret findings through the selected host:
   - Access: event signatures, Text/Value and focus, Recordset versus
     RecordsetClone/independent DAO, NoMatch, Dirty/NewRecord/filter state,
     Requery re-entry, and DAO cleanup. Load the matching files under
     `references/vba-office/access/` only for the affected topics.
   - Excel: workbook/worksheet/range ownership, ThisWorkbook versus active
     objects, multi-cell event targets, EnableEvents restoration, host-owned
     callbacks, add-in/document-module transfer, and Ribbon assumptions.
     Load the matching files under `references/vba-office/excel/`.
5. Where a claim needs behavior evidence, use
   `workflows/vba-office/test.md` on an authorized controlled target. Keep
   source findings and runtime observations distinct. A review does not
   authorize an unrelated refactor or business-module rewrite.

## Stop and output

For an operator-only observation, follow the adapter handoff and stop
dependent review claims until its resume conditions are satisfied.

For each finding give severity/location, host/owner, evidence type/source,
why the finding applies under host semantics, runtime evidence or explicit
unverified state, and the smallest recommended change. Report independent
checks separately, including operator observations and remaining gaps.
