# VBA Test Workflow

Use for behavioral verification through a deterministic entry point. Apply
`SKILL.md` and `adapters/vba-office.md` for fixture choice, ownership, tool
calls, dialog handling, recovery, and independent verification checks. Paths
resolve from the `runtime-ops` root. Load host references only when the test
depends on their semantics; this workflow does not require a reference scan.

## Sequence

1. Identify the controlled target and the exact result/state to observe.
   Confirm that the fixture exists and that its state supports the test. A
   missing fixture stops fixture-backed verification under the adapter
   policy; do not substitute a production or authoritative file.
2. Open or attach through the adapter, record ownership, and reread the
   relevant source. For a changed module, compare with the intended patch and
   run host-correct parse/inspection. Static results stand on their own.
3. Record Compile independently. Access has no registered compile operation.
   Excel's target-checked compile command returns dispatch-only evidence;
   record `compile dispatch: unverified`, never Compile Verified from that
   response. Runtime execution does not supply the missing compile result.
4. Run the narrow entry point:
   - Access: the candidate baseline is a no-argument `Public Function` through
     Eval. Current deployment evidence may remain unverified; return relevant
     form/record/control state, including
     Dirty/NewRecord/filter/current-record/focus when the claim needs it.
   - Excel: use a targeted macro against the identified workbook and observe
     the intended result/state. For Ribbon/layout work, XML or screenshot
     evidence is supplementary artifact/appearance evidence, not proof that
     the callback executed.
5. Resolve a running request and any owned dialog through the adapter's
   structured sequence; retain the request ID, returned status/result/error,
   and dialog actions. If an operator-only prerequisite appears, stop before
   that step and dependent work, using the adapter handoff/resume contract.
6. Remove any temporary smoke function after its run and result reread;
   confirm cleanup. Close only targets the workflow manages and choose save
   deliberately. A pre-existing workbook reused as already-open is not
   newly owned cleanup work.

## Failure and report

Preserve exact errors and trust-setting guidance. Do not change fixture
references or configuration merely to manufacture a passing result. Required
write/verification failures use the adapter recovery contract; unresolved
operator prerequisites remain stopped until the required state can be checked.

Record host/version, fixture path, entry point, exact tool inputs and returned
evidence, expected versus observed state, and cleanup/recovery outcome.
Report Static, Compile, Runtime, and Operator-observed independently as
achieved or unverified with reasons. There is no highest achieved level and
no check implies another; authorization alone proves none of them.
