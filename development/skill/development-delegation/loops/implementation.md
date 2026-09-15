# Implementation Loop

Use only when the current phase already has a usable detailed phase plan.

## Unit execution

1. Load the active phase plan and persisted status.
2. Select one ready implementation unit whose dependencies are satisfied.
3. Delegate only the repository/document/code questions needed for that unit; parallelize independent scout work.
4. Build a bounded implementation brief from direct evidence.
5. Delegate the code change to the implementer.
6. Delegate build/test/runtime/manual validation to the test executor.
7. On failure, return decisive evidence to the implementer. Re-scout only when evidence is stale or incomplete.
8. Accept the unit only when every criterion has direct validation evidence. Persist status before selecting another unit.
9. If work reveals a missing architecture decision, invalid phase assumption, or required scope expansion, return `ESCALATE_PLAN` and route to the planning loop.

## Phase close

When all units are mechanically accepted, verify phase exit criteria and build a review package.

If `human_supervisor=true`, do not automatically spawn an independent reviewer. Mark the phase `PHASE_ACCEPTED` when its mechanical exit criteria are evidenced, report completion to the human supervisor, then advance according to the project plan.

If `human_supervisor=false`, mark the phase `READY_FOR_REVIEW` and invoke `modules/review.md`:

- `PASS` -> persist `PHASE_ACCEPTED`, then advance.
- `REVISE` -> translate each actionable finding into bounded repair work, implement and revalidate it, rebuild the review package, then review again.
- `BLOCK` -> stop with the blocking decision/evidence.

Repeat unattended review until `PASS`, `BLOCK`, or a deployment-defined review budget is exhausted. Never convert reviewer uncertainty into approval.

## Retry discipline

Reuse the implementation brief across retries unless the contract or evidence changed. Keep reviewer findings distinct from implementer rationale. Do not solve validation failures in the test-executor role. Do not broaden a unit merely to make tests pass.
