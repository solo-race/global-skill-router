# Independent Review Module

This module is mandatory at unattended phase-close boundaries and may also gate unattended planning. It is not part of the implementer role.

## Independence

The reviewer receives a fresh, bounded package. Do not pass the implementer's private reasoning history or ask the reviewer to continue implementation. Provide only the active contract/plan, changed files or diff, validation evidence, repository state, prior review findings when applicable, and material risks.

The reviewer is read-only and must not edit code, repair failures, or redesign the project unless the review question is explicitly a plan review.

## Review targets

### Implementation review

Check:
- every phase/unit criterion has direct evidence;
- changes remain inside approved scope;
- validation is sufficient and reproducible;
- failures, skipped checks, generated artifacts, and dirty state are accounted for;
- later-phase assumptions are not invalidated;
- no uncovered migration, compatibility, permission, irreversible, or data-loss issue was introduced.

### Planning review

Check:
- the plan is grounded in cited project/repository evidence;
- the current phase is executable rather than merely descriptive;
- units have clear boundaries, dependencies, acceptance criteria, and validation;
- the plan is consistent with the master plan and existing architecture/contracts;
- material risks and authority decisions are explicit.

## Return contract

Return exactly one disposition:

- `PASS` — no material finding blocks acceptance/sealing.
- `REVISE` — one or more actionable findings can be corrected within the active plan/contract.
- `BLOCK` — approval requires a new architecture/plan/authority decision or evidence that the loop cannot obtain mechanically.

For `REVISE` or `BLOCK`, report findings as:

```text
finding_id:
severity: material | blocking
criterion_or_source:
evidence:
required_change:
```

Do not approve based on plausibility. Do not require stylistic changes that are outside acceptance criteria unless they reveal a concrete correctness, maintainability, safety, or scope defect.
