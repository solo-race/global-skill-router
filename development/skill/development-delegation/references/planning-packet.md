# Planning Packet

Use this packet to keep repository discovery outside the high-reasoning planner.

```text
PLANNING_PACKET

request:
- objective: <what must be planned>
- scope: project | current phase | requested subset

mode_and_authority:
- compatibility: dynamic | explicitly_selected_legacy
- scope_authority: <source and unresolved decisions>
- budgets_and_bindings: <selected constraints>
- risk_and_review: <triggers and policy independent of supervision>

plan_state:
- master_plan: none | <path/reference>
- current_phase: <name or unresolved>
- detailed_phase_plan: none | <path/reference>

project_docs:
- <path/section> -> <directly observed requirement/constraint>

evidence_state:
- baseline: <revision plus dirty-file fingerprints and environment>
- freshness_and_coverage: <limits; refresh stale affected facts>

repo_evidence:
- <path/symbol> -> <directly observed fact>

tests_and_validation:
- <path/command/fixture> -> <what it covers or constrains>

existing_contracts:
- <source> -> <contract/API/schema/compatibility fact>

constraints_and_decisions:
- <source> -> <known constraint or already-made decision>

open_questions:
- <question that evidence has not resolved>

return:
- NEED_EVIDENCE | PLAN_DRAFT | BLOCKED
```

Keep observation separate from inference. Prefer exact paths, symbols, document sections, commands, and plan references. Do not collapse contradictory evidence into a single unsupported summary.

A dynamic scoped plan may have no master plan or phase. Preserve existing project
conventions without inventing broader scope. Legacy prerequisites apply only when
explicitly selected.
