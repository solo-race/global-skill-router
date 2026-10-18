# Implementation Brief

Pass only the information needed for this acceptance unit. Stable rules live in
the loaded module contract (source `SKILL.md`, deployed payload `MODULE.md`).

```text
IMPLEMENTATION_BRIEF

unit:
mode: direct | planned | exploratory_experiment
role_module: <skill-root-relative role file>
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
- executor: <implementer self-check | tester; required independent review is separate>
- <exact external check>

return:
- changed files and resulting revision/dirty fingerprint
- checks actually run and evidence per criterion
- concise rationale
- unresolved concern or BLOCKED reason
```

Direct work uses this brief without a master plan. An exploratory experiment also
requires explicit mutation scope, finite experiment/time/tool/cost bounds, rollback
and stop conditions; a brief alone is not permission.
