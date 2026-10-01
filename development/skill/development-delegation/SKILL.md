---
name: development-delegation
description: Route repository work through planning or delegated implementation with session-level human supervision and optional independent review. Use when repository work needs a detailed phase plan or execution through bounded delegation and evidence gates.
---

# Development Delegation Loop

Load this skill once in the main supervisor. The supervisor owns routing and state; workers receive only bounded role-specific context.

## Routing contract

This skill is routing middleware / an orchestrator, with
`routing_outcome: continue`. It is not a terminal execution skill.
Its priority determines when orchestration is initialized, independently of
specialized skill discovery.

After the mandatory session gate is satisfied, return `ROUTE_CONTINUE` to the
global router before repository discovery or loop execution. The router keeps
this orchestration contract active, resolves remaining matching global layers
and the applicable scenario module, and supplies those specialized contracts
to the supervisor. If no specialized route applies, the supervisor may still
run the delegation loop for the accepted task.

Carry the router's `activated_modules` through planning and implementation.
Re-entry into this skill's route selection chooses a loop; it does not rerun
platform discovery or initialize this orchestrator again. Delegate execution
with the selected specialized module and adapter contracts included in each
relevant bounded assignment. A loop result such as `PLAN_SEALED` or
`PHASE_ACCEPTED` never changes this skill's routing outcome to terminal.

## Mandatory session gate

At first activation for a session, before repository discovery, planning, or implementation, initialize the exact role identities and supervision mode. Registered role TOMLs and the host runtime (Codex/OpenCodex) are authoritative for model/provider routing; this skill does not add a separate route-readiness gate.

If role identities have not been selected, ask the session operator to choose one host-registered identity for each role. Use `scout`, `implementer`, or `tester` as the native options and include the matching `*-deepseek` identities when they are registered in the host. Use the host's structured choice controls when available. Otherwise, show the currently registered IDs and request the three exact choices in one reply. Store the choices as `scout_identity`, `implementer_identity`, and `tester_identity`; keep them stable for the session unless the operator changes them. An unset `*_identity` is a contract error, never a cue to fall back to a default identity. If native dispatch later reports that an identity or its configured route is unavailable, stop only that assignment, report the host error, and require an explicit identity change; never silently substitute another model.

After role selection, if supervision has not already been explicitly declared for this session, ask exactly one separate user decision:

`Session supervision: is a human supervisor actively present for this session? [Yes/No]`

Set `human_supervisor=true` for Yes and `false` for No. Do not infer supervision from time of day, user activity, or prior sessions. Keep the value stable for the session unless the user changes it.

## Global agent dispatch

The declarations in `agents/registry.example.toml` are deployment examples. The deployment must make the corresponding role TOMLs available as globally registered native agents before this skill can dispatch them.

For every role assignment, the main supervisor must call the host's native subagent interface using the exact global identity selected for that role. Use `scout_identity`, `implementer_identity`, or `tester_identity` for those roles; use the existing global `planner` and `reviewer` identities for planning and review, and the existing global `codebase-memory-scout` identity for a graph pass. Do not perform delegated work inline or silently substitute a different identity or model. If an identity is not registered or its model route is unavailable, stop that assignment and report the missing deployment configuration.

## Route selection

After the session gate and platform routing continuation finish, inspect current HEAD plus the minimum project/plan documents needed to classify the task.

Enter the **planning loop** when either condition is true:
- the user explicitly asks to plan, re-plan, decompose, or phase the work;
- the current phase has no usable detailed phase plan.

A usable detailed phase plan names the current phase objective, bounded implementation units, dependencies/order, material scope and constraints, validation for each unit, and phase exit criteria. A roadmap or phase list alone is not sufficient.

Otherwise enter the **implementation loop**.

After planning is sealed, return to route selection; normally the new current-phase plan then enters implementation.

## Discovery selection

Repository discovery starts with the session-selected `scout_identity` (ordinary scouting) and stays there by default. Add the registered `codebase-memory-scout` graph pass only when the relevant files and symbols are not yet known, cross-file call/dependency relationships or architectural entrypoints materially guide the task, and a graph project with adequate coverage exists. Use ordinary scouting directly when the task supplies exact files or a narrow known defect, when it is configuration or document verification, when coverage is unavailable or insufficient, or when the graph pass would duplicate adequate evidence.

Run at most one of the two over the same ground: ordinary scouting and the graph pass must not duplicate broad repository discovery in one task. The graph pass is bounded (normally 3-4 graph queries, with metadata checks counted separately) and returns the packet described in [Graph evidence packet](references/graph-evidence-packet.md). Verify the relevant current source before implementation or a consequential impact conclusion.

Graph evidence is provisional: absence, exhaustive impact, dead code, and readiness are never established from it alone. If the graph project is ambiguous, coverage is stale or partial, the files are unsupported, or the tools are unavailable, report the gap explicitly and continue with source inspection through the selected authorized role; switching role or model follows the existing selection policy and never silently incurs different quota; never rebuild the index and never launch an extra agent merely to make a graph precheck pass.

Dispatch `codebase-memory-scout` through the same native host interface as the other registered identities. If native dispatch or its required graph tools are unavailable, report the gap and continue with source inspection through the selected `scout_identity` when feasible; never silently substitute a different model.

## Supervision policy

`human_supervisor=true` -> supervised execution. Run the implementation loop without automatic independent review. The human remains the live escalation/review authority.

`human_supervisor=false` -> unattended execution. Run implementation plus the independent review module at each phase-close boundary. A phase does not advance until review returns `PASS`. `REVISE` findings are converted into bounded repair work, revalidated, and reviewed again. Stop on `BLOCK`, an unresolved planning/architecture decision, or a deployment-defined review budget.

The same review module may gate a newly created plan in unattended planning. In supervised planning, do not add an automatic reviewer unless the user asks for one.

## Roles

- **Main supervisor**: owns routing, session mode, delegation, evidence comparison, persisted state, and retry/review transitions.
- **Scout**: read-only repository/document inspection; returns source-backed facts and separates inference.
- **Graph scout** (`codebase-memory-scout`): read-only, provisional structural discovery through the Codebase Memory graph; selected before or instead of ordinary scouting when the relevant files and symbols are not yet known and cross-file relationships guide the task; returns the bounded packet in [Graph evidence packet](references/graph-evidence-packet.md) and is verified against current source.
- **Planner**: reasons over a prepared planning packet and produces or revises the project/phase plan; it does not perform broad repository discovery itself.
- **Implementer**: changes only the bounded implementation brief.
- **Test executor**: runs requested validation and reports reproducible evidence without repairing failures.
- **Reviewer**: independent read-only audit of a plan or mechanically completed phase; returns `PASS`, `REVISE`, or `BLOCK` and does not implement fixes.

## Shared boundaries

- Prefer current HEAD and direct evidence over stale summaries or prior conversation.
- Keep repository discovery with scouts; expensive reasoning roles should receive compressed, source-backed packets.
- The supervisor coordinates and accepts; it is not the fallback implementer or planner.
- Material repository-state changes invalidate affected evidence.
- Record only work actually performed and validation actually observed.
- Architecture changes, irreversible/migration/permission/data-loss decisions, or scope expansion require explicit plan-level authority.

## States

Implementation units end as `ACCEPTED`, `RETRY_IMPLEMENTATION`, `REVERIFY`, `BLOCKED`, or `ESCALATE_PLAN`.

A mechanically complete phase is `READY_FOR_REVIEW` when unattended and becomes `PHASE_ACCEPTED` only after reviewer `PASS`. Under human supervision, mechanical acceptance may directly produce `PHASE_ACCEPTED` unless the human requests review.

Planning ends as `PLAN_SEALED`, `NEED_EVIDENCE`, `REVISE_PLAN`, or `BLOCKED`.

## Loop contracts

- [Implementation loop](loops/implementation.md)
- [Planning loop](loops/planning.md)
- [Independent review module](modules/review.md)

## Handoff templates

- [Implementation brief](references/implementation-brief.md)
- [Evidence report](references/evidence-report.md)
- [Planning packet](references/planning-packet.md)
- [Phase plan](references/phase-plan.md)
- [Review package](references/review-package.md)
- [Graph evidence packet](references/graph-evidence-packet.md)
