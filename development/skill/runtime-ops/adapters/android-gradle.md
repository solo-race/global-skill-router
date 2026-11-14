---
adapter_schema_version: 1
adapter: android-gradle
environments: [win-android]
capabilities: [project.inspect, task.execute, build.observe, dependency.inspect]
task_modes:
  closed: false
  modes: [inspect, build, test, diagnose, dependencies]
verification_model_kind: independent_checks
mutation_support: bounded
---

# Android / Gradle Adapter

## 1. Identity, version, and source of truth

Provider: `rnett/gradle-mcp`. Record the connected server identity/version from
MCP initialization metadata (or its configured executable's `--version`). Obtain
the current input schemas through the connected provider's MCP `tools/list`
response or the client's exposed equivalent before first invocation. Tool-name
search alone is not schema discovery. Bind client-qualified names to this server,
not merely to matching short names. Reconfirm on provider/catalog changes.

The admitted surface below is source-backed; activation does not certify that a
provider is online. If the provider or usable schema is absent or incompatible,
report that capability unavailable and use only the declared wrapper fallback,
in degraded mode. Never read a reference checkout to complete a runtime contract.

## 2. Capabilities

| Capability | Admitted operations |
|---|---|
| `project.inspect` | `gradle` for version, project and task reports; local wrapper/settings reads |
| `task.execute` | `gradle` for scoped local build/check/compile/test tasks and stopping an owned build |
| `build.observe` | `query_build`, `wait_build` |
| `dependency.inspect` | `inspect_dependencies` for resolved dependencies and optional update queries |

These are the complete admitted MCP tool names. Upstream installation, REPL,
preview, source-editing and other tools are not admitted by this version.

## 3. Operations

All operations apply to the selected Windows Android/Gradle project. The following
operation rules define the adopted surface; current live schemas govern
argument construction. Do not extend the capability boundary just because a
schema advertises more operations. Results are MCP tool results containing text,
including formatted summaries/tables; do not assume a JSON result object.

- `gradle`: pass the absolute project root and discovered task arguments.
  Prefer foreground; retain the server, root, tasks and returned BuildId for
  background work. Stop only an observed build owned by this task. Cancellation
  is not rollback. Task-output capture may truncate and is not test evidence.
- `query_build`: use the exact BuildId, not the default recent-build list.
  Inspect lifecycle/outcome and requested task/test scope, refining filters or
  pagination as needed. An empty failure filter does not prove success. Do not
  use report-file output for observation-only work.
- `wait_build`: use bounded waits (normally at most 60 seconds). A log/task
  condition can match before completion; timeout leaves the build running.
  Re-query the handle rather than launching a duplicate.
- `inspect_dependencies`: select an observed project/configuration. Disable
  update checks for graph-only inspection; enable them only for update intent.
  Unresolved or skipped entries remain unknown. Inspection neither changes
  declarations nor proves that an upgrade will build.

Use live schemas for parameter names, defaults, filters and pagination. Keep
calls within the admitted capability boundary even if a provider exposes more.

MCP first: read `gradle/wrapper/gradle-wrapper.properties` before version-sensitive
advice. Inspect settings or use `gradle` with `commandLine=[":projects"]`, then
the relevant `:tasks` or discovered project's `:project:tasks`. Reuse adequate
current evidence; expand only the relevant task report if needed. Never guess a
module, task path, variant, configuration, Gradle version or Kotlin version.
For a filtered test use the discovered test task's supported `--tests` option;
do not assume every Android test task accepts it. Diagnose with `PROBLEMS` first,
then relevant `FAILURES` and bounded `CONSOLE`. Use `TESTS` for test evidence,
not task-output capture or a grep of console output. Do not duplicate available
provider evidence with shell pipelines.

Wrapper fallback is deliberately smaller: after reporting degraded mode, resolve
the selected project's own `gradlew.bat`, run it from that root with argument
arrays, and preserve its exit code, stdout and stderr. The fixed sequence is
wrapper-properties read, `--version` when environment evidence is needed,
`:projects` when project identity is unresolved, the relevant `:tasks` report
when task identity is unresolved, then the exact approved task (with a supported
test filter only if requested). Use no global Gradle and no automatic extra
flags. Stop if the wrapper is absent or cannot run. Execution is foreground;
there is no MCP BuildId, structured problem/test query or dependency-update
capability. Existing report files tied to this invocation may supply test
evidence; without them tests remain unverified. A timeout/interruption leaves
completion unknown until the process state is observed; do not silently restart.

## 4. Preconditions and failures

Confirm root/settings/wrapper identity, required JDK and Android SDK availability,
and the requested task's effects before execution. Project configuration itself
executes build logic and can resolve/download dependencies. A task name alone
does not establish its side effects; inspect unknown custom task definitions or
project documentation before deciding it is local.

Stop before publish/upload/release, device or remote deploy/install, signing or
credential-dependent distribution, production migration, or deletion outside
regenerable project outputs. These exceed this bounded adapter even when the
provider can run them: they require explicit user authorization and a separate
operation-specific recovery contract before execution. Do not enable build-scan
publication (`publishScan` defaults false) merely for diagnosis.

Preserve actual failure text verbatim with operation, relevant inputs and returned
status. Source-observed failures include `commandLine is required when not
stopping a build.`, `Unknown or expired build ID: <id>`, and `Build <id> is not
running or not found`. A wait may report `Wait timed out after <seconds>s` or
throw `Build finished without <condition>`. Preserve the actual instance, not
these placeholders. Missing test/task output and capture warnings are evidence
gaps. Tool transport success, an unset error flag, or a finished build alone does
not prove a successful Gradle outcome; inspect the result, including help/version
operations. Do not convert permission, configuration or resolution errors into
success or silently retry them with a different root/JDK.

## 5. Mutation model

The admitted tools do not directly edit source/build files, but Gradle executes
project code. Local tasks and dependency inspection may write build outputs,
caches and downloaded artifacts. Permit only effects whose scope is understood
and recoverable. Source-generating or rewriting tasks require snapshots of the
specific affected files first. Unknown/external effects stop execution. No
dependency update, wrapper upgrade or build-file rewrite is implied by inspection.

## 6. Verification model

```yaml
verification_model:
  kind: independent_checks
  states:
    - id: configuration_resolved
      meaning: The selected project configuration resolved for the requested scope.
      required_evidence:
        - Successful project/task report from this root and invocation with no configuration failure.
      does_not_prove: [requested tasks succeeded, tests passed, target runtime behavior]
    - id: requested_tasks_succeeded
      meaning: The exact requested local tasks completed successfully.
      required_evidence:
        - Final provider outcome and TASKS results for the retained BuildId, or wrapper exit zero and matching task outcomes.
        - Requested task scope and any skipped, cached, up-to-date or no-source outcomes recorded explicitly.
      does_not_prove: [tests executed or passed, target runtime behavior]
    - id: requested_tests_passed
      meaning: The requested test scope has observed passing test results.
      required_evidence:
        - Completed build and TESTS results tied to its BuildId and exact test task/filter, or matching reports produced by the completed wrapper invocation.
        - Observed executed test scope and pass/fail/skip counts with no missing or failed requested tests.
      does_not_prove: [unrequested tests passed, device or UI behavior, newly executed cached tests]
  relations: []
  unsupported:
    - id: target_runtime_exercised
      reason: REPL, preview and device execution are outside this adapter's admitted tool boundary.
```

Report each state as achieved or unverified, with its scope and evidence source.
Skipped/no-source tests or build success alone cannot establish tests passed.
Cached/up-to-date tasks prove reuse, not fresh execution; require observed test
results for any test claim and state that reuse explicitly. Degraded wrapper
evidence never becomes provider diagnostics. Runtime behavior stays unsupported.

## 7. Recovery model

Before mutation, record the bounded output scope and how it can be regenerated
from current inputs. Preserve existing user edits. For a task that writes source
or non-regenerable files, prepare readable snapshots of exactly those files,
including which paths were absent; if the write scope cannot be identified, stop.

After failure/cancellation, observe the retained build/process until stopped,
record partial outputs and preserve diagnostic evidence. Regenerate affected
outputs with the same scoped task after correcting the evidenced cause, or remove
only verified task-owned generated paths when cleanup is necessary and authorized.
Do not wipe global caches or run broad `clean` as automatic recovery. Restore
snapshotted files only after checking for intervening user changes; verify their
contents and re-run the targeted check. A successful restore does not prove the
build/test succeeded. External publication, device state and unknown side effects
cannot be rolled back by this adapter and remain stop conditions.

## 8. Environment and configuration

Pass `projectRoot` explicitly instead of relying on `GRADLE_MCP_PROJECT_ROOT`.
Keep Windows filesystem paths distinct from colon-prefixed Gradle project paths;
use argument arrays and quote the wrapper executable path through the host runner.
Record wrapper/JDK/SDK and relevant `GRADLE_USER_HOME` identity when comparing
runs. Never change them silently to make a failure disappear.

`invocationArguments` accepts explicit environment/system/JVM arguments. The
provider inherits environment by default (`envSource=INHERIT`), not arbitrary JVM
system properties; `SHELL` is an explicit environment-refresh choice when the
host's environment is stale. Explicit `javaHome` overrides project daemon JVM
settings and `JAVA_HOME`; an invalid explicit home does not fall through. When
omitted, project daemon settings precede `JAVA_HOME` and the Tooling API default.
Pass only task-required overrides. Do not assume IDE and provider JVMs agree.

## 9. Task routing

- `inspect`: establish root/wrapper, then only the project/task facts needed.
- `build`: classify effects, prepare recovery, execute the exact discovered task,
  observe final outcome and report `requested_tasks_succeeded` independently.
- `test`: select task and supported filter, execute, then inspect `TESTS` and
  report observed scope/counts; never promote a generic build success.
- `diagnose`: reuse the failed BuildId, read `PROBLEMS`, refine failure ids and
  console evidence as needed; rerun only after an evidenced change or necessity.
- `dependencies`: select project/configuration, inspect its resolved graph;
  enable update checks only when needed by the request.

Other intents follow the Core lifecycle within the declared capability boundary.
