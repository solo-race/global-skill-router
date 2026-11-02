# Evidence Report

Scout and test returns use the same compact evidence shape.

```text
EVIDENCE_REPORT

unit:
role: scout | tester | implementer_self_check | specialist
role_mode: <locate | evidence_digest | test_author | test_executor, when applicable>
status: COMPLETE | PARTIAL | BLOCKED

provenance:
- revision_and_dirty_fingerprint: <actual inspected/tested state>
- environment: <relevant tools/config>
- scope_and_coverage: <included/excluded; stale or partial evidence>
- binding: <actual host identity; no inferred model verification>

observed:
- <path/symbol | command | artifact> -> <fact/result>

inference:
- <optional; keep separate from observed facts>

validation:
- command: <exact command or n/a>
  exit: <code or n/a>
  result: PASS | FAIL | NOT_RUN
  decisive_output: <minimal output>

blockers_or_scope_notes:
- <none or issue outside delegated scope>
```

Use exact sources and reproducible checks. Scouts do not edit; test executors do not
repair failures. Test authors additionally return changed test paths, criterion-to-case
coverage and applicable red/green evidence; report uncovered risks, not invented passes.
Scout returns preserve material counterevidence, unknowns and the few passages requiring
direct supervisor inspection. Keep returns decision-sized; link raw artifacts instead
of copying logs. Omit inapplicable detail rather than filling repetitive boilerplate.
