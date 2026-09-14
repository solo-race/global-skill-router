# Final Review Package

Use when all acceptance units in a phase are mechanically complete.

```text
FINAL_REVIEW_PACKAGE

phase:
status: READY_FOR_FINAL_REVIEW

units:
- <unit> -> ACCEPTED -> <evidence reference>

changes:
- <path> -> <purpose>

validation:
- <check> -> <PASS/FAIL/NOT_RUN> -> <evidence>

scope_integrity:
- unexpected_changes: none | <list>
- approved_contract_changes: none | <reference>

repo_state:
- head: <commit/ref>
- working_tree: <clean/dirty/unknown>

residual_risks:
- <none or risk>

review:
- contract satisfied?
- scope preserved?
- evidence sufficient?
- later-phase assumptions still valid?
```

The supervisor reports readiness; architectural approval remains upstream.
