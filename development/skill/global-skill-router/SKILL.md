---
name: global-skill-router
description: Selectively load a managed platform module for the current task. Use when a task may match a managed global-skill scenario or global task-intent route.
---

# Global Skill Router

## Contract

The router is the single platform entrypoint. It checks global task-intent
routes before scenario routes, then loads the smallest applicable managed module
from the assembled payload. It does not replace a selected module's contract and
never treats planned capability as active capability.

`router_root` is the directory containing this currently loaded `SKILL.md`.
Resolve every `_platform/...` and `library/...` path against `router_root`, never
against the process current working directory, repository root, or source tree.
Do not probe alternate roots after a failed relative read.

## Routing state and outcomes

A match selects a module for initialization; it does not complete routing.
Each v4 module route declares an integer `routing_priority` and
`routing_outcome: continue | terminal`. Higher priority is considered first
within each scope. Priority never implies terminal ownership.

Keep `activated_modules` (module names), the current route, and the selected
scenario in the current task scope. Mark a selected module before initializing
it; initialize each module at most once. If initialization pauses for input,
resume that initialization before advancing. Preserve this state across
delegated work and planning-loop re-entry; do not restart at the first match.

After initialization the module returns a routing result to the supervisor:

- `ROUTE_CONTINUE`: the route declares `continue`; keep its orchestration
  contract active and resume discovery among unvisited candidates. Check
  another candidate only when it also applies to the task; continuation does not
  make every unvisited module applicable.
- `ROUTE_TERMINAL`: the route declares `terminal` and fully owns execution
  of the routed task; routing is complete and no further candidates are read.

These are control results, not claims that task execution has finished. A
missing result or a result inconsistent with the declared outcome is a contract
error; stop and report it rather than silently treating a match as completion.

## Routing steps

1. Bind `router_root`, then read exactly
   `router_root/_platform/routes/index.yaml`. Use schema v4 for continuation;
   legacy v1/v2/v3 payloads require redeployment before using this contract.
2. Evaluate unvisited `global_routes` using task evidence already available.
   Select a matching route at the highest `routing_priority`. If equally
   ranked candidates remain plausible and existing evidence cannot select one,
   report `ROUTE_AMBIGUOUS`; do not fall through to scenario shards. Name
   ordering makes the index deterministic and does not resolve ambiguity.
3. Read the selected `skill_path` relative to `router_root`, mark its name,
   and initialize the module. On `ROUTE_TERMINAL`, stop routing with zero
   scenario shards read. On `ROUTE_CONTINUE`, repeat step 2 while excluding
   `activated_modules`. Each continuing match consumes one unvisited route.
4. When no unvisited global route matches, resolve exactly one scenario from
   explicit task, repository, or environment evidence already available.
   If managed scenario routing is plausible but the scenario cannot be
   resolved, report `ROUTE_AMBIGUOUS` instead of reading multiple shards.
   If no managed scenario applies, finish discovery with the initialized
   orchestrators still active; no specialized managed module was resolved.
5. Read only that scenario's registered shard. Select the smallest applicable
   unvisited module at the highest priority, using the same ambiguity and
   outcome rules as global routes. Initialize it once. `ROUTE_CONTINUE`
   resumes within this same shard; `ROUTE_TERMINAL` stops routing. Exhaustion
   ends discovery without revisiting earlier modules or reading another shard.
6. The `adapters` list may be empty: a module is usable without an adapter
   when the task needs no external host/tool capability. If it does need an
   adapter, compare active mapping descriptions with the task and host/toolchain
   evidence and require exactly one match. Report adapter unavailable when
   there is no match, or adapter ambiguity before reading any adapter when
   multiple mappings match. Only after a unique match is selected, resolve its
   `adapter_path` relative to `router_root` and read that adapter contract.
   Do not enumerate `library/` or `adapters/` to discover alternatives.
7. Reuse a selected module while reliably loaded and unchanged in the current
   task scope. Follow that module's load/reuse rules for profiles, adapters, and
   references. Pass selected specialized contracts to delegated workers within
   their bounded assignments; activating an orchestrator does not replace them.

If no module matched in either scope, report `ROUTE_NO_MATCH` and continue
without loading a managed module.

## Stop conditions

- Never resolve payload paths from the process CWD or retry them against a
  source-repository path.
- Never read a second scenario shard merely to compare candidates.
- Never scan `library/`, glob module paths, or pre-read unselected modules.
- Never load a planned or unavailable entry as if it were active.
- A missing or malformed route index is deployment corruption: stop and report
  it instead of guessing a route or module path.
