---
name: global-skill-router
description: Selectively load a managed platform module for the current task. Use when a task may match a managed global-skill scenario.
---

# Global Skill Router

## Contract

The router is the single platform entrypoint. It selects a scenario and loads
the smallest applicable managed module from the assembled payload. It does not
replace a selected module's contract and it never treats planned capability as
active capability.

## Routing steps

1. Read `_platform/routes/index.yaml` to identify the relevant scenario shard.
2. Read only the shard needed for the current task; read a second shard only
   when the scenario is genuinely ambiguous.
3. Choose the smallest matching module set, normally one module.
4. Read the selected `library/<module>/SKILL.md` and follow that module's
   progressive-disclosure rules for profiles, adapters, and references.

Do not scan `library/`, glob module paths, or pre-read modules that were not
selected. If no route matches, report no-match and continue without loading a
module. A missing or malformed route index is deployment corruption: stop and
report it instead of guessing a module path.

## Stop conditions

- Never load a planned or unavailable entry as if it were active.
- Never use an absolute source-repository path; all payload paths are relative
  to this router root.
- Do not infer a route by enumerating the private library.
