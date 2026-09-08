# Scenario Routing

This document is a readable projection of the registry in
[`../skill/manifest.yaml`](../skill/manifest.yaml). The manifest is the authority;
this page must not be edited as a second route registry.

## Current projection

| Scenario | Intent / control plane | Current route | State |
|---|---|---|---|
| `win-access-vba` | Repository discovery, read/control, validation, and review | `runtime-ops` + `gpt-repo-local` | active |
| `win-access-vba` | Host/tool inspection, mutation, and testing | `runtime-ops` + `vba-office` | active |
| `win-access-vba` | SQL Server runtime operations | `runtime-ops` + `sql-server` | planned; no adapter capability yet |
| `win-android` | Repository discovery, read/control, validation, and review | `runtime-ops` + `gpt-repo-local` | active |
| `win-android` | Android/Gradle runtime operations | `runtime-ops` + `android-gradle` | planned; no adapter capability yet |
| `wsl-python` | Repository discovery, read/control, validation, and review | `runtime-ops` + `gpt-repo-local` | active |
| `wsl-python` | Evidence-first external investigation | `research-investigation` + selected profile | active |
| `wsl-python` | WSL/Python runtime operations | `runtime-ops` + `wsl-python` | planned; no adapter capability yet |

## Routing rules

- A scenario is not an automatic task selector. Choose the route from the task intent,
  then check the applicable profile or adapter and live tool availability.
- A `planned` route records an extension point only. It does not authorize a tool call or
  claim that the capability is available.
- A scenario may have more than one route. For example, `wsl-python` can use the active
  research control plane and the active repository-control route (`runtime-ops` +
  `gpt-repo-local`); its scenario-specific `wsl-python` runtime adapter remains planned.
- Adapters are owner-contained under `runtime-ops` and are deployed with that Skill; they
  are not independently installable top-level Skills.
