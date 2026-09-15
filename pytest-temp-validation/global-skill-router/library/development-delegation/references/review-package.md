# Review Package

Use for unattended phase-close review and unattended plan review. Keep the package bounded and independent of worker reasoning history.

```text
REVIEW_PACKAGE

review_type: IMPLEMENTATION | PLAN
subject: <phase/plan identifier>
status: READY_FOR_REVIEW

contract_or_plan:
- <path/reference> -> <active acceptance/exit criteria>

changes_or_plan_delta:
- <path/unit/section> -> <what changed and why>

evidence:
- <criterion> -> <source/command/artifact> -> <PASS/FAIL/NOT_RUN or observed fact>

scope_integrity:
- unexpected_changes: none | <list>
- approved_scope_changes: none | <reference>

repo_state:
- head: <commit/ref>
- working_tree: <clean/dirty/unknown>

prior_findings:
- <none or finding id -> disposition/evidence>

material_risks:
- <none or explicit risk/decision>

review_questions:
- are all criteria directly evidenced?
- is scope preserved?
- is validation/evidence sufficient?
- are plan dependencies and later-phase assumptions still valid?
- are material risks or authority decisions exposed?

return:
- PASS | REVISE | BLOCK
```

For `REVISE`/`BLOCK`, use the finding schema defined in `modules/review.md`.
