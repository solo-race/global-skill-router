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

## Routing steps

1. Bind `router_root`, then read exactly
   `router_root/_platform/routes/index.yaml`.
2. Evaluate `global_routes` first using only task evidence already available.
   If exactly one global route matches, read its `skill_path` relative to
   `router_root`, load that module, read zero scenario shards, and stop routing.
3. If multiple global routes remain plausible and existing evidence cannot
   select one, report `ROUTE_AMBIGUOUS`; do not fall through to scenario shards.
4. If no global route matches, resolve exactly one scenario from explicit task,
   repository, or environment evidence already available. If managed scenario
   routing is plausible but the scenario cannot be resolved, report
   `ROUTE_AMBIGUOUS` instead of reading multiple shards.
5. Read only that scenario's registered shard, choose the smallest matching
   module set (normally one module), then read each selected
   `library/<module>/SKILL.md` relative to `router_root`.
6. Reuse a selected module while reliably loaded and unchanged in the current
   task scope. Follow that module's load/reuse rules for profiles, adapters, and
   references.

If neither a global route nor a scenario route matches, report `ROUTE_NO_MATCH`
and continue without loading a managed module.

## Stop conditions

- Never resolve payload paths from the process CWD or retry them against a
  source-repository path.
- Never read a second scenario shard merely to compare candidates.
- Never scan `library/`, glob module paths, or pre-read unselected modules.
- Never load a planned or unavailable entry as if it were active.
- A missing or malformed route index is deployment corruption: stop and report
  it instead of guessing a route or module path.
