# Evidence Report

Scout and test returns use the same compact evidence shape.

```text
EVIDENCE_REPORT

unit:
role: SCOUT | TEST_EXECUTOR
status: COMPLETE | PARTIAL | BLOCKED

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

Use exact sources and reproducible checks. Scouts do not edit; test executors do not repair failures.
