---
name: runtime-ops
description: Host-neutral control framework for operating registered external tools through explicit adapters with capability checks, preserved failure semantics, recoverable mutation, and evidence-bounded verification claims. Use when a task can read, inspect, modify, execute, migrate, test, or otherwise affect a host environment and the agent must load the adapter contract before acting.
---

# Runtime Operations

Control plane for operating registered external tools against live hosts. This framework fixes safety and honesty invariants; every host- and tool-specific fact lives in an adapter under `adapters/`.

## Scope

Applies wherever an external tool or host exposes an explicit contract and a task must inspect, modify, execute against, migrate, or test state in that environment. The framework does not define concrete languages, databases, build systems, or application-domain semantics; it defines how capability is claimed before action, how mutation stays recoverable, and what evidence a verification claim requires. All relative paths in this skill resolve against the directory containing this file.

## Core contract

1. Establish a valid selected adapter contract under Adapter routing before using its capabilities. With no valid contract, or when the needed capability is not declared, stop the affected operation or degrade to analysis that does not depend on it. Never assume a capability exists merely because a workflow describes it; follow the exact contract and preserve actual errors.
2. Preserve exact operation identity, relevant inputs, returned status, and failure message. Never rewrite an actual failure into a qualified success.
3. Distinguish observation, mutation, and verification. A completed write is not behavioral correctness.
4. A mutation executes only when it satisfies the adapter's recovery contract; without one, high-impact writes are prohibited.
5. A verification claim may rest only on evidence the adapter explicitly requires for that state.
6. Pass environment and profile values explicitly on every tool call; tools do not read skill or profile files automatically.
7. Project conventions never override adapter-declared host or tool facts; report conflicts instead of resolving them silently.

## Operation lifecycle

1. Classify intent and blast radius.
2. Select the adapter and target environment.
3. Establish declared capabilities and preconditions using the load/reuse rules below.
4. Inspect or read the current state the operation depends on.
5. When mutating, prepare and verify the recovery path first.
6. Execute the smallest scoped operation.
7. Reread or reobserve the changed state where applicable.
8. Run the adapter-declared targeted verification.
9. Recover when the failure policy requires it.
10. Report achieved verification states, failures, and remaining uncertainty.

Adapters may layer mode-specific workflows onto this sequence, but they may not weaken these invariants.

## Adapter routing

Load only the adapter selected by the current v4 route's nested `adapters`
mapping before using its capabilities. Match task and host/toolchain evidence
against active descriptions: zero matches means unavailable, multiple matches
mean ambiguous. Stop only the adapter-dependent work in either case. Resolve
the unique `adapter_path` against `router_root`; do not scan for alternatives.
No adapter is needed for work without external host/tool capabilities.

Reuse the contract while it remains available in the current task context and
its identity, provider compatibility and capability scope remain current.
Reload or reconfirm the affected requirement when those change. Check each
operation's preconditions even when reusing the adapter.

## Verification discipline

Follow the selected adapter’s verification model: states with required evidence, explicit non-claims, inter-state relations, and unsupported states. Iron rule: never report a higher or stronger verification state than the evidence actually achieved. Only linear models may use highest-achieved wording; every other model reports each state individually as achieved or unverified. One evidence item proves only the scope its state declares, and a successful mutation never substitutes for a stronger state's evidence.

## Mutation and recovery

Before a high-impact mutation, the adapter's recovery contract must name the mechanism (for example file snapshots, transaction rollback, restore points, or rebuild-from-source), its preparation and rollback steps, rollback verification, and stop conditions for irreversible or partially reversible operations. Prepare and verify the recovery path before writing. The framework fixes no directory layout or naming scheme; those belong to the adapter.

## Evidence discipline

Separate documented behavior, observed results and inference. Resolve source
conflicts using the selected adapter's source policy; never generalize a single
experiment beyond its recorded environment and scope.

## Prohibited behaviors

- Assuming a capability or invoking an undeclared tool.
- Reporting lower-strength evidence as a stronger verification state.
- Executing a high-impact mutation without a prepared, verified recovery path.
- Modifying a test fixture to manufacture a passing result.
- Hardcoding any adapter's tool names or host-specific rules into this Core.
- Depending across the skill root on a reference repository at deployment time.
- Silently swallowing, paraphrasing away, or downgrading an actual error.
