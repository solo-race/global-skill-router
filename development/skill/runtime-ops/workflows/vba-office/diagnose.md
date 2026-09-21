# VBA Diagnose Workflow

Use for a reported defect, unexpected behavior, or uncertain runtime state.
Apply the loaded module contract (source `SKILL.md`, deployed payload `MODULE.md`)
and `adapters/vba-office.md`; their operation, ownership,
recovery, and operator-handoff contracts remain authoritative. Paths below
resolve from the `runtime-ops` root.

## Sequence

1. Identify the host, owning object/module, entry point, and reported versus
   expected behavior. Classify the hypothesis as source-based,
   runtime-dependent, or both.
2. Load only affected host knowledge: Access event paths use
   `references/vba-office/access/form-lifecycle.md`; focus/value questions use
   `references/vba-office/access/controls.md`; record/state questions use
   `references/vba-office/access/record-navigation.md` and/or
   `references/vba-office/access/form-state.md`. Excel ownership questions use
   `references/vba-office/excel/workbook-worksheet-model.md`; event questions
   use `references/vba-office/excel/worksheet-events.md`; UserForm questions
   use `references/vba-office/excel/userform-model.md`. Load shared error or
   encoding knowledge only when that issue is involved.
3. Retrieve the complete relevant module and related callbacks. Inspect the
   surrounding event/state path, not only the reported line. Run host-correct
   static inspection according to the adapter.
4. Form a targeted test for each runtime-dependent hypothesis. For Access,
   observe relevant Dirty/NewRecord/filter/current-record/focus state through
   the adapter's no-argument Public Function/Eval path. For Excel, observe
   the intended workbook/sheet and event re-entry state rather than inferring
   active objects from source. Use `workflows/vba-office/test.md` for execution.
5. Separate confirmed findings, documented host behavior, evidence-based
   inferences, runtime assumptions/observations, and project-specific
   recommendations. Propose the smallest behavior-preserving correction;
   use `workflows/vba-office/modify.md` only when modification is authorized.

## Stop and output

If the hypothesis requires an unavailable observation or operator-only step,
use the adapter handoff and stop dependent diagnosis. Resume after the stated
prerequisite is satisfied and fresh structured state checks are complete.
Report which hypotheses remain unresolved and each independent verification
check; runtime smoke does not establish compilation.
