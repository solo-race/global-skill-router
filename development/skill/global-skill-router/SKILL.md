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

1. Read `router_root/_platform/routes/index.yaml` (schema v4). Evaluate unvisited
   active `global_routes` against task evidence, highest `routing_priority`
   first. If equally ranked matches cannot be distinguished, report
   `ROUTE_AMBIGUOUS`; name ordering is not a tie-breaker. Read the selected
   `skill_path`, mark and initialize the module. `ROUTE_CONTINUE` repeats this
   step; `ROUTE_TERMINAL` stops without reading a scenario shard.
2. When no unvisited global route matches, resolve one scenario from available
   task, repository or environment evidence. If plausible scenarios remain
   ambiguous, report `ROUTE_AMBIGUOUS` without reading shards. Otherwise read
   only that scenario's registered shard and apply the same priority,
   initialization and outcome rules to applicable unvisited modules. Continue
   within that shard only; exhaustion ends discovery. If no scenario applies,
   finish discovery with already initialized orchestrators still active.
3. When a selected module needs external host/tool capabilities, require one
   matching active entry from its nested `adapters` mapping, using task and
   host/toolchain evidence. Zero matches means unavailable; multiple matches
   mean ambiguous. Stop adapter-dependent work before reading either. Resolve
   the unique `adapter_path` against `router_root`. Adapter-free work may use
   an empty mapping. Do not enumerate `library/` or `adapters/` for alternatives.
4. Reuse selected contracts while loaded and current in this task; follow each
   module's reference/adapter load rules. Pass specialized contracts to workers
   within their bounded assignments; an orchestrator does not replace them.

If no module matched, report `ROUTE_NO_MATCH` and continue without a managed
module. Missing, malformed or unsupported routing data stops discovery; report
it rather than guessing paths. Load only active selected entries, never planned
entries, unselected modules or a second scenario shard.
