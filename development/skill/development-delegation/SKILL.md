---
name: development-delegation
description: Use when a repository already has a phase plan or acceptance contract and implementation should be delegated across a supervisor, read-only scouts, a bounded implementer, external validation, and an upstream final reviewer.
---

# Development Delegation Loop

Load this skill once in the main supervisor. Give workers only the relevant contract fragment and role-specific return format.

## Purpose

Execute an existing phase contract with minimal duplicated context. Planning and final cross-phase review remain upstream. If no usable contract exists, escalate instead of inventing one.

Repository observations should come from current HEAD and direct evidence, not stale summaries or prior conversation.

## Roles

- **Upstream planner / final reviewer**: owns phase decomposition, acceptance contracts, architecture decisions, and final audit.
- **Main supervisor**: selects work, delegates inspection/implementation/validation, compares evidence with acceptance criteria, persists state, and routes failures.
- **Scout**: read-only inspection. Returns observed facts with exact sources and keeps inference separate.
- **Implementer**: makes only the bounded change in the implementation brief. If the brief requires wider scope, return `BLOCKED`.
- **Test executor**: runs requested checks and returns reproducible evidence without editing code.

## Loop

1. Load the active phase contract and project status.
2. Select one acceptance unit with satisfied dependencies.
3. Delegate only the repository/document/code questions needed for that unit; parallelize independent questions.
4. Build the bounded implementation brief from scout evidence.
5. Send code changes to the implementer.
6. Delegate build/test/runtime/manual validation.
7. On failure, return evidence to the implementer; re-scout only when evidence became stale or incomplete.
8. Accept only when every criterion has direct evidence. Persist state, then advance or stop in a defined state.
9. When the phase closes, prepare the final review package and report `READY_FOR_FINAL_REVIEW`.

## Boundaries

- Keep work inside the active contract and allowed scope; unrelated refactors or architecture changes require escalation.
- The supervisor coordinates and accepts; it is not the fallback implementer after worker failure.
- Scouts and test executors do not modify repository files.
- Evidence should name paths, symbols, diffs, commands, test names, exit codes, or artifacts where applicable.
- A material repository-state change invalidates affected evidence.
- Reuse a stable implementation brief across retries unless the contract or evidence changed.
- Record only work actually performed and validation actually observed.

## Escalate when

- the contract is missing, stale, contradictory, or materially ambiguous;
- required implementation crosses the permitted scope or needs an architecture decision;
- targeted verification cannot resolve conflicting evidence;
- required validation cannot run;
- repeated attempts fail for the same underlying reason;
- the unit introduces an uncovered irreversible, migration, permission, or data-loss decision;
- completing the unit would invalidate a later phase contract.

## States

Each acceptance unit ends as one of:

- `ACCEPTED` — all criteria have evidence.
- `RETRY_IMPLEMENTATION` — code failed but contract/evidence remain valid.
- `REVERIFY` — evidence is stale, incomplete, or conflicting.
- `BLOCKED` — mechanical execution cannot continue.
- `ESCALATE_PLAN` — upstream planning or architecture is required.

A completed phase remains `READY_FOR_FINAL_REVIEW` until upstream review.

## Prompt delta

After this skill and the active repository contract are loaded, ordinary task prompts should state only what differs from the defaults:

```text
<mode>: <objective>
scope=<optional narrower scope>
exceptions=<optional task-specific constraint>
```

## References

- [Implementation brief](references/implementation-brief.md)
- [Evidence report](references/evidence-report.md)
- [Final review package](references/final-review-package.md)
