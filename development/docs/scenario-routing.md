# Scenario Routing

This document is a readable projection of the registry in
[`../skill/manifest.yaml`](../skill/manifest.yaml). The manifest is the authority;
this page must not be edited as a second route registry.

## Current projection

| Scenario | Intent / control plane | Current route | State |
|---|---|---|---|
| `win-access-vba` | Execute an existing implementation/acceptance contract | `development-delegation` | active |
| `win-access-vba` | Host/tool inspection, mutation, and testing | `runtime-ops` + `vba-office` | active |
| `win-access-vba` | SQL Server runtime operations | `runtime-ops` + `sql-server` | planned; no adapter capability yet |
| `win-android` | Execute an existing implementation/acceptance contract | `development-delegation` | active |
| `win-android` | Android/Gradle runtime operations | `runtime-ops` + `android-gradle` | planned; no adapter capability yet |
| `wsl-python` | Execute an existing implementation/acceptance contract | `development-delegation` | active |
| `wsl-python` | Evidence-first external investigation | `research-investigation` + selected profile | active |
| `wsl-python` | WSL/Python runtime operations | `runtime-ops` + `wsl-python` | planned; no adapter capability yet |

## Routing rules

- A scenario is not an automatic task selector. Choose the route from the task intent,
  then check the applicable profile or adapter and live tool availability.
- A `planned` route records an extension point only. It does not authorize a tool call or
  claim that the capability is available.
- `wsl-python` currently selects only the research control plane; `win-android` has no
  active module route. Their scenario-specific runtime adapters remain planned.
- Adapters are owner-contained under `runtime-ops` and are deployed with that Skill; they
  are not independently installable top-level Skills.
