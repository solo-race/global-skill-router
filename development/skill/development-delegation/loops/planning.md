# Planned Work

Use for requested planning, complex dependency coordination or high-risk work. Load
only existing project/phase documents relevant to the requested scope. Missing a
master plan does not require inventing a whole-project roadmap: create a bounded
standalone plan unless the user requested project planning. Preserve established
planning conventions and existing master plans when relevant.

Gather only missing source evidence under references/discovery.md. Give an assigned
planner references/planning-packet.md, not a broad rediscovery request. The planner
returns NEED_EVIDENCE, PLAN_DRAFT or BLOCKED. Evidence/revision/assignment budgets
apply to every continuation. Materialize the plan through an authorized writer;
a read-only planner must not gain write permission from this workflow.

An executable plan names objective, scope/exclusions, stable unit IDs and dependency
DAG, ownership/isolation, acceptance and validation per unit, integration checks,
exit criteria, risks/rollback, assumptions and unresolved authority decisions. Use
references/phase-plan.md if the repository has no format. Reject cycles or unknown
dependencies before dispatch. Apply modules/review.md at the plan boundary; required
review must PASS before PLAN_SEALED. Sealing a plan does not authorize implementation.

When execution is authorized, use loops/implementation.md. A plan-only request ends
with the sealed plan; do not automatically implement it. Legacy compatibility alone
retains its whole-project planning prerequisite and supervision-derived review gates.
