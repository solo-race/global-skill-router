# Routing Projection

This document is a readable projection of the registry in
[`../skill/manifest.yaml`](../skill/manifest.yaml). The manifest is the authority;
this page must not be edited as a second route registry.

## Current projection

| Scope | Intent / control plane | Current route | State |
|---|---|---|---|
| `global` | Execute an existing implementation/acceptance contract | `development-delegation` | active |
| `win-access-vba` | Host/tool inspection, mutation, and testing | `runtime-ops` + `vba-office` | active |
| `win-access-vba` | SQL Server runtime operations | `runtime-ops` + `sql-server` | planned; no adapter capability yet |
| `win-android` | Android/Gradle runtime operations | `runtime-ops` + `android-gradle` | planned; no adapter capability yet |
| `wsl-python` | Evidence-first external investigation | `research-investigation` + selected profile | active |
| `wsl-python` | WSL/Python runtime operations | `runtime-ops` + `wsl-python` | planned; no adapter capability yet |

## Routing rules

- Global task-intent routes are checked before scenario routing. A global hit loads its
  module directly from the route index and does not read a scenario shard.
- Scenario selection comes from task/repository/environment evidence already available;
  once selected, at most one scenario shard is read. Ambiguity is reported rather than
  resolved by scanning multiple shards.
- Runtime payload paths resolve from the loaded `global-skill-router/SKILL.md` directory,
  never from the process current working directory or source repository root.
- A `planned` route records an extension point only. It does not authorize a tool call or
  claim that the capability is available.
- `wsl-python` currently selects only the research control plane; `win-android` has no
  active scenario module route. Their scenario-specific runtime adapters remain planned.
- Adapters are owner-contained under `runtime-ops` and are deployed with that Skill; they
  are not independently installable top-level Skills.
