# Planning Loop

Enter when the user explicitly requests planning/replanning or when the current phase lacks a usable detailed phase plan.

## 1. Determine planning depth

Inspect the existing project/roadmap/plan documents before deciding what must be created.

- **No project plan exists:** use project documents and current repository evidence to establish a master project plan first: objective, constraints, phase sequence, phase-level outcomes, dependencies, and completion conditions. Then identify the current phase and materialize its detailed plan.
- **A master plan exists but the current phase is not detailed enough to execute:** preserve the master plan and materialize only the current phase.
- **A detailed phase plan exists but the user explicitly requests planning:** revise, refine, or replace the requested planning scope; do not silently rewrite unrelated phases.

Planning must leave the current phase executable. A phase name or roadmap bullet is not enough.

## 2. Gather evidence cheaply

The main supervisor delegates project-document and repository discovery to scouts. Build `references/planning-packet.md` from source-backed facts rather than a free-form summary. Include relevant documents, current architecture/contracts, existing plan state, tests, dependencies, constraints, and unresolved questions.

Do not make the high-reasoning planner rediscover the repository unless a narrow follow-up inspection is essential.

## 3. Planner reasoning loop

Send the planning packet to the planner. The planner returns one of:

- `NEED_EVIDENCE` with precise missing questions;
- `PLAN_DRAFT` containing the project-plan changes, current-phase plan, assumptions, and unresolved decisions;
- `BLOCKED` when the plan requires an authority decision that evidence cannot resolve.

For `NEED_EVIDENCE`, delegate only the requested questions to scouts, append the new evidence to the packet, and invoke the planner again.

## 4. Materialize the plan

A detailed current-phase plan must define:

- phase objective and relation to the master plan;
- bounded implementation units;
- dependency/order graph;
- allowed scope and material exclusions;
- acceptance criteria for each unit;
- validation/checks for each unit;
- phase exit criteria;
- migration, compatibility, rollback, permission, data-loss, or other material risks when relevant;
- assumptions and explicit decisions still owned by a human/upstream authority.

Persist the plan using the repository's existing planning convention when one exists. Otherwise use the structure in `references/phase-plan.md` and avoid inventing a parallel planning system.

## 5. Seal or review

If `human_supervisor=true`, surface the materialized plan and mark it `PLAN_SEALED` unless the human requests review or revision.

If `human_supervisor=false`, build a planning review package and invoke the independent review module. `PASS` seals the plan; `REVISE` returns findings to the planner with only the relevant evidence; `BLOCK` stops unattended execution.

After `PLAN_SEALED`, return to the skill route selector. If the current phase is now executable, enter the implementation loop.
