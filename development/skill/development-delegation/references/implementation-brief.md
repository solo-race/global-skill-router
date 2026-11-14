# Implementation Brief

Use for handoffs or coordinated units, not as a prerequisite for same-context Direct
work. Pass only the information needed for this acceptance unit. Stable rules live in
the loaded module contract (source `SKILL.md`, deployed payload `MODULE.md`).

```text
IMPLEMENTATION_BRIEF

unit:
mode: direct | planned | exploratory_experiment
role_module: <skill-root-relative role file>
role_mode: <only when applicable; tester defaults to test_executor>
binding: <authorized host identity; explicit model/provider constraints or host-owned>
capabilities: <required and actually granted; no implied grant>
authority: <approval/source; quota permission when required>
budgets: <finite limits and remaining counters>
supervision: interactive | unattended
review_policy: on_demand | risk_based | always
risk: <triggers; mandatory review cannot be waived>
baseline: <revision plus dirty-file fingerprints>
depends_on: <accepted prerequisite IDs>
owner_and_workspace: <exclusive scope; isolated worktree when parallel mutable work>
goal:

acceptance:
- <criterion>

scope:
- allowed: <path/symbol>
- forbidden: <path/module/behavior, if material>

facts:
- <source> -> <observed fact>

constraints:
- <unit-specific constraint, if any>

validate:
- executor: <implementer self-check | tester test_author/test_executor; independent review is separate>
- <exact external check>

return:
- changed files and resulting revision/dirty fingerprint
- checks actually run and evidence per criterion
- concise rationale
- unresolved concern or BLOCKED reason
```

This is a field guide, not a mandatory full-length form: reference existing contract
values, omit irrelevant fields and avoid duplicating stable policy. Do not append a
rationale chart or dispatch scorecard. Omitted role_mode defaults to test_executor.
An explicit test_author assignment without owned test paths or write authority is
BLOCKED pending clarification, never silently downgraded to test_executor.

Same-context Direct work follows loops/direct.md without this form. Local diagnostic
experiments follow loops/exploratory.md within existing authority; this brief grants
no permissions.
