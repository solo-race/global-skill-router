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

At first activation for a session, before repository discovery, planning, or implementation, run `scripts/router_preflight.py` with Python 3.11 or newer. It reads the active user-level Codex config, installed role profiles, and local model catalog. It does not modify files or make inference requests.

Offer `scout-deepseek`, `implementer-deepseek`, or `tester-deepseek` only when that exact profile reports `available: true`. The active Codex provider must route through an installed Codex Router, and the local catalog must advertise the profile's exact route with `multi_agent_version = "v2"`. If preflight is blocked or cannot run, mark DeepSeek identities unavailable and offer only registered native roles. Do not send the upstream ID `deepseek-flash` directly to Codex, add a per-agent `model_provider = "deepseek"`, or silently substitute another model.

The DeepSeek custom agent's Codex-facing model slug is `deepseek/deepseek-v4.1-flash`; Codex Router maps it to the upstream provider model ID `deepseek-flash`. A v2 catalog entry is still only static readiness. On the first delegated task that uses this route in a session, make that assignment read-only, require a unique marker in its result, and verify the actual route from Router request metadata before allowing writes or test execution through DeepSeek. Set `deepseek_runtime_verified=true` only after both the marker and route are confirmed. If the child fails or its route cannot be verified, mark all DeepSeek identities unavailable for the rest of the session and stop the assignment. The optional `--check-local-router` flag only GETs the local `/models` catalog and never proves a child spawn.

If role identities have not been selected, ask the session operator to choose one available globally registered identity for each role. Use `scout`, `implementer`, or `tester` as the native options; add the matching `*-deepseek` option only when preflight marks it available. Use the host's structured choice controls when available. Otherwise, show the currently available IDs and request the three exact choices in one reply. Store the choices as `scout_identity`, `implementer_identity`, and `tester_identity`; keep them stable for the session unless the user changes them. Do not begin task work until all three are set.

After role selection, if supervision has not already been explicitly declared for this session, ask exactly one separate user decision:

`Session supervision: is a human supervisor actively present for this session? [Yes/No]`

Set `human_supervisor=true` for Yes and `false` for No. Do not infer supervision from time of day, user activity, or prior sessions. Keep the value stable for the session unless the user changes it.

## Global agent dispatch

The declarations in `agents/registry.example.toml` are deployment examples. The deployment must make the corresponding role TOMLs available as globally registered native agents before this skill can dispatch them.

For every role assignment, the main supervisor must call the host's native subagent interface using the exact global identity selected for that role. Use `scout_identity`, `implementer_identity`, or `tester_identity` for those roles; use the existing global `planner` and `reviewer` identities for planning and review. Do not perform delegated work inline or silently substitute a different identity or model. If an identity is not registered or its model route is unavailable, stop that assignment and report the missing deployment configuration.

## Route selection

After the session gate and platform routing continuation finish, inspect current HEAD plus the minimum project/plan documents needed to classify the task.

Enter the **planning loop** when either condition is true:
- the user explicitly asks to plan, re-plan, decompose, or phase the work;
- the current phase has no usable detailed phase plan.

A usable detailed phase plan names the current phase objective, bounded implementation units, dependencies/order, material scope and constraints, validation for each unit, and phase exit criteria. A roadmap or phase list alone is not sufficient.

Otherwise enter the **implementation loop**.

After planning is sealed, return to route selection; normally the new current-phase plan then enters implementation.

## Supervision policy

`human_supervisor=true` -> supervised execution. Run the implementation loop without automatic independent review. The human remains the live escalation/review authority.

`human_supervisor=false` -> unattended execution. Run implementation plus the independent review module at each phase-close boundary. A phase does not advance until review returns `PASS`. `REVISE` findings are converted into bounded repair work, revalidated, and reviewed again. Stop on `BLOCK`, an unresolved planning/architecture decision, or a deployment-defined review budget.

The same review module may gate a newly created plan in unattended planning. In supervised planning, do not add an automatic reviewer unless the user asks for one.

## Roles

- **Main supervisor**: owns routing, session mode, delegation, evidence comparison, persisted state, and retry/review transitions.
- **Scout**: read-only repository/document inspection; returns source-backed facts and separates inference.
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
