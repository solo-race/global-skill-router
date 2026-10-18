---
name: development-delegation
description: Coordinate bounded repository work with dynamic roles, explicit authority and evidence gates. Use when repository work needs direct execution, planning, exploration or delegated validation.
---

# Development Delegation

Load once in the supervisor. This is routing middleware / an orchestrator with
`routing_outcome: continue`, not a terminal execution skill. Initialize the task
contract from [policy](routing/task-policy.yaml) and [supervisor rules](references/supervisor.md),
then return `ROUTE_CONTINUE` before discovery or execution. Preserve
`activated_modules`; subsequent loop selection never restarts platform discovery.
Carry specialized module/adapter contracts into relevant bounded assignments.
Loop acceptance never changes the routing outcome.

## Select only what the task needs

- **Direct**: known, bounded, low-risk work uses an implementation brief and explicit
  validation; no master plan or automatic planner is required.
- **Planned**: requested planning, complex dependencies or consequential changes use
  a usable scoped plan. Preserve existing project conventions.
- **Exploratory**: uncertain scope or solution starts read-only; experiments require
  explicit bounded authority before any mutation.

Supervision (`interactive` / `unattended`) and review policy (`on_demand` /
`risk_based` / `always`) are independent. High-risk work always requires independent
review and its applicable human approval. Interactive does not waive review;
unattended does not grant authority. Explicitly selected [legacy compatibility](references/legacy-compatibility.md)
preserves the earlier session gates; never activate it by inference.

Load a role module from policy only when assigning that role. A role is behavior,
not a model or registered identity. Use only necessary roles, not a mandatory team.
Honor explicit host identities, model choices, approval and quota limits; no silent
substitution. Registered TOMLs remain deployment-owned examples of bindings.
A generic authorized host agent may receive a role module with scoped capabilities.

## Conditional references

- [Supervisor, bindings, budgets and transitions](references/supervisor.md)
- [Direct execution](loops/direct.md), [planned execution](loops/planning.md),
  [exploration](loops/exploratory.md), [implementation DAG](loops/implementation.md)
- [Independent review](modules/review.md)
- [Discovery selection](references/discovery.md)
- [Implementation brief](references/implementation-brief.md),
  [planning packet](references/planning-packet.md), [phase plan](references/phase-plan.md),
  [evidence report](references/evidence-report.md), [review package](references/review-package.md)

Stop the affected work on missing authority, scope conflict, exhausted budget,
unavailable selected identity or insufficient evidence. Report checks actually
observed; role assignment or a successful dispatch is never proof of acceptance.
