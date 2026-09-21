---
name: kotlin-tooling
description: Kotlin-specific toolchain, project-identity, and migration guidance for Android and Kotlin repositories. Use when deciding between Kotlin Toolchain and Gradle, classifying Kotlin or AGP migrations, or preserving Kotlin source-set and plugin semantics.
---

# Kotlin Tooling

## Contract

This module is a Kotlin-specific decision layer. It does not define a Gradle
tool ABI, run commands, parse provider results, or replace the selected
`runtime-ops` adapter. For pure Gradle discovery, build, test, diagnosis, or
task execution, load `runtime-ops` with the routed `android-gradle` adapter and
do not load this module merely because the sources are Kotlin. Load this module
when the task requires Kotlin Toolchain, Kotlin source-set, Kotlin plugin, KMP,
or AGP migration decisions.

All paths in this module are relative to the directory containing this file.
The source checkout used to derive these rules is development-only evidence and
is never a runtime dependency.

## Identify the project authority

Inspect the repository root before choosing a workflow:

- `project.yaml`, `module.yaml`, or a project `kotlin`/`kotlin.bat` wrapper
  identifies a Kotlin Toolchain project. Invoke the checked-in wrapper from the
  project root so its pinned version wins; do not substitute a global binary.
- `settings.gradle`/`.kts`, `build.gradle`/`.kts`, `gradlew`/`gradlew.bat`, or
  `gradle/wrapper` identifies a Gradle project. Delegate Gradle discovery and
  execution to `runtime-ops` and `android-gradle`.
- If both sets are present, treat the repository as a migration or mixed
  project only after inspecting which files are authoritative. Do not guess.
- A pure Gradle task does not require this module. A Kotlin migration or
  Toolchain decision may require both modules, while execution still requires a
  declared runtime capability.

In a Kotlin Toolchain project, `project.yaml` declares modules and local
plugins; a module's identity comes from the directory containing `module.yaml`.
`module.yaml` paths are module-relative and do not support `${...}`
interpolation. Treat `module.yaml`, `project.yaml`, `plugin.yaml`, version
catalogs, wrappers, and local plugins as project input: review repositories and
commands before executing anything, and never run `kotlin update` unless asked.

## Kotlin-specific task classification

1. **Toolchain model/configuration** — inspect `project.yaml`, module YAML, the
   wrapper, module product, toolchain/JDK settings, dependencies, and checks.
   Keep configuration decisions here; use only a declared runtime adapter for
   any command execution.
2. **Gradle build/test/task work** — use `runtime-ops` + `android-gradle` for
   wrapper precedence, project/task discovery, execution, diagnostics, and
   verification. This module contributes no duplicate Gradle commands or
   result interpretation.
3. **Gradle → Kotlin Toolchain migration** — inventory before editing:
   plugins, `buildSrc`/`build-logic`, custom tasks and generated artifacts,
   source sets, dependency scopes, version catalogs, properties, and CI
   commands. Preserve source code and every source-set dependency. Classify
   each third-party Gradle plugin as **drop**, **native**, or **reimplement**;
   translate convention/build-logic configuration to module templates and
   reserve local plugins for imperative behavior.
4. **AGP/KMP migration** — classify each module before changing it. A KMP
   library paired with `com.android.library` follows the library-plugin/source
   set migration; a KMP module paired with `com.android.application` requires a
   separate Android app module; a multi-platform app module may need the full
   split only when the requested scope permits it. For AGP 9+, remove
   `org.jetbrains.kotlin.android`, migrate `kapt` to KSP or explicitly approved
   legacy-kapt, and review source-set, DSL, namespace, resource, and dependency
   changes.

## Verification and stop conditions

- Verify project/configuration resolution, requested task/build success, and
  test success as separate facts. A successful build does not prove tests or
  runtime/UI behavior; use only evidence required by the selected adapter.
- Stop before execution when project authority is ambiguous, a wrapper or
  required capability is unavailable, a plugin/task's side effects are
  unknown, or a migration would drop a source set, dependency, generated
  artifact, or plugin behavior.
- Report unknown or degraded provider/tooling state explicitly. Do not turn a
  shell fallback into structured-provider evidence, and do not treat a
  successful configuration parse as behavioral verification.

## Progressive disclosure

Read [`references/kotlin-decision-notes.md`](references/kotlin-decision-notes.md)
only for the migration/toolchain decision details it covers. It is not needed
for ordinary Gradle execution.

