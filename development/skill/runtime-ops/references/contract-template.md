# Adapter Contract

An adapter document is this framework's extension ABI: the complete, self-sufficient statement of what one host/tool integration can do and how it must be operated. Write adapters in Markdown with YAML frontmatter, conforming to this specification. Structural enforcement (schema fields, capability deduplication, task-mode closure, verification-kind and mutation-support vocabularies, recovery-model presence for mutating adapters) is applied by the platform lifecycle gate before activation; until that gate exists, this file is normative. Whether a declared tool is actually online is a live runtime check, never a gate assertion.

## Required metadata

```yaml
adapter_schema_version: 1
adapter: <kebab-case>
environments: [<scenario-or-host>]
capabilities: [<stable-capability-id>]
task_modes:
  closed: false
  modes: []
verification_model_kind: linear | partial_order | independent_checks
mutation_support: none | bounded | high-impact
```

`capabilities` MUST be non-empty and deduplicated. Include `task_modes` with an explicit `closed` value even when `modes: []`. `mutation_support`: `none` = read-only surface; `bounded` = reversible scoped writes; `high-impact` = destructive or whole-artifact replacement.

The body answers the ten questions below, in order.

## 1. Identity, version, and source of truth

Name the real provider, server, or tool; how to obtain its version; and the authoritative implementation source. Contracts describe registered reality, not assumed APIs.

## 2. Capabilities

List stable capability ids and map every concrete registered tool to one. The Core consumes capability ids only; tool names stay inside the adapter. Ids must remain stable within the adapter and interpretable across its own sections; a cross-adapter capability registry is deliberately not standardized yet — promote one only when actual reuse demand appears.

## 3. Operations

For each operation give the real registered name, signature, defaults, return shape, host applicability, and the load-bearing semantics a caller cannot infer from the signature: replacement scope, timeout behavior, encodings, async handles, id conventions. Inline everything needed to form correct calls and judge results; external documentation is never a runtime dependency of a deployed adapter.

## 4. Preconditions and failures

Permissions, open/closed state, environment dependencies, and the failure shapes actually returned. Require preserving real failure text verbatim in records and reports; a paraphrased failure is a fabricated result.

## 5. Mutation model

Which operations change state, at what granularity, with what blast radius. Whole-artifact replacements deserve an explicit warning and drive the recovery model below.

## 6. Verification model

Declare the full `verification_model` block per `references/verification-ladder.md`, consistent with frontmatter `verification_model_kind`: states with required evidence and non-claims, relations, unsupported states with reasons.

## 7. Recovery model

Mechanism, preparation steps, recovery steps, rollback verification, and unrecoverable conditions. Mandatory whenever `mutation_support` is not `none`; for `high-impact`, preparation must precede any write and be confirmed complete before the write proceeds.

## 8. Environment and configuration

Host/platform versions, session topology and identity rules, profile/config injection rules (values passed explicitly per call; servers do not read skill files), casing quirks, and local asset provisioning (fixtures, exports, ignore files).

## 9. Task routing

Optional. When `task_modes.modes` is non-empty, define each mode's trigger and sequence, and honor `closed`: with `closed: false`, unmatched intents fall back to the Core operation lifecycle instead of being forced into a mode.

## 10. Provenance

Record design-reference sources and external implementation origins. The adapter remains deployable without them: reference repositories are read-only design inputs, never runtime dependencies of the deployed skill.
