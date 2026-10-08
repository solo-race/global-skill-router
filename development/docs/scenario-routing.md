# Routing Projection

This document is a readable projection of the registry in
[`../skill/manifest.yaml`](../skill/manifest.yaml). The manifest is the authority;
this page must not be edited as a second route registry.

## Current projection

| Scope | Intent / control plane | Current route | State |
|---|---|---|---|
| `global` | Explicit planning/re-planning, missing current-phase plan, or delegated implementation under an existing contract | `development-delegation` | active; priority 100; continue |
| `global` | Selected local Adobe Photoshop document operations through registered MCP; excludes imagegen, repository implementation, and MCP security review | `photoshop-ops` | active; priority 80; terminal; native operations UNVERIFIED |
| `win-access-vba` | Host/tool inspection, mutation, and testing | `runtime-ops` + `vba-office` | active |
| `win-access-vba` | SQL Server runtime operations | `runtime-ops` + `sql-server` | planned; no adapter capability yet |
| `win-android` | Kotlin Toolchain, KMP, and AGP-specific decisions | `kotlin-tooling` → continue | active; priority 10 |
| `win-android` | Android/Gradle runtime operations, when also required | `runtime-ops` + `android-gradle` | active; priority 0; terminal |
| `wsl-python` | Evidence-first external investigation | `research-investigation` + selected profile | active |
| `wsl-python` | WSL/Python runtime operations | `runtime-ops` + `wsl-python` | planned; no adapter capability yet |

## Routing rules

- Global task-intent routes are checked before scenario routing. Within each scope,
  higher `routing_priority` is selected first; equal-priority ambiguity is reported.
  A match initializes its module once. `routing_outcome: continue` resumes discovery;
  `terminal` stops it when the module fully owns execution. Priority does not imply stop.
- `development-delegation` is orchestration middleware. After its session gate it
  returns `ROUTE_CONTINUE`, leaving specialized scenario discovery active. On
  `win-android`, `kotlin-tooling` is priority 10 and continues to the next
  applicable route; `runtime-ops` is priority 0 and terminal. Other current
  scenario routes are priority 0 and terminal.
- `photoshop-ops` is a terminal global owner for authorized local document operations,
  with no scenario route. Its source checkout is optional; registration and native
  availability are checked by its self-contained contract. Native operations remain
  UNVERIFIED; activation does not establish tool availability or permission to edit art.
- Activated module names persist through the task, so continuation consumes only
  unvisited routes and multiple orchestration layers cannot repeatedly select themselves.
- Scenario selection comes from task/repository/environment evidence already available;
  once selected, at most one scenario shard is read. Ambiguity is reported rather than
  resolved by scanning multiple shards.
- Runtime payload paths resolve from the loaded `global-skill-router/SKILL.md` directory,
  never from the process current working directory or source repository root.
- A `planned` route records an extension point only. It does not authorize a tool call or
  claim that the capability is available.
- `wsl-python` currently selects only the research control plane; its scenario-specific
  runtime adapter remains planned. `win-android` loads `runtime-ops` with
  `android-gradle` only when that runtime capability is applicable; Kotlin
  decision work remains active across that continuation.
- Adapters are owner-contained under `runtime-ops` and are deployed with that Skill; they
  are not independently installable top-level Skills.
