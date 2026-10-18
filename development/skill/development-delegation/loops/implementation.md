# Implementation and Dependency DAG

Execute a bounded Direct brief or usable Planned units. Scout only missing evidence,
assign the smallest adequate role set, implement within scope, then validate exact
acceptance criteria. Do not require a master plan for Direct work. Use current source
and references/supervisor.md for budgets, bindings and transitions.

## Ready selection and isolation

Represent units by stable IDs, dependencies, acceptance, owner, allowed paths/resources,
base revision, output location and validation. Reject missing dependencies, duplicate
IDs and cycles before execution; report the cycle and request/revise the plan under
existing authority. Never break dependencies just to create parallelism.

A unit is ready only when prerequisites are ACCEPTED on the integration baseline and
its authority, budget and evidence are current. Choose ready IDs in stable lexical
order; dispatch at most the remaining concurrency/assignment limits. Read-only jobs
may share a tree if it stays stable for their evidence snapshot.

Concurrent mutable units require separate worktrees or equivalent isolated snapshots,
explicit disjoint path/resource ownership, and no hidden shared writes (generated
files, build outputs, database state, caches or external services). Disjoint filenames
alone are insufficient. If isolation or ownership cannot be established, serialize.
Creating worktrees/environments must itself be authorized. Shared contracts or overlapping
resources are ordered through dependencies or an explicitly owned integration unit.

## Integration and acceptance

Load `modules/integration.md` for the combined-tree acceptance procedure. The
supervisor records each output's base and changed paths; authorized integration uses
stable dependency order and preserves unrelated dirty work. Only current integrated
unit criteria plus any required unit review permit unit ACCEPTED. Dependants may then
run. Phase-wide exit criteria and required boundary review are checked only at phase
close before PHASE_ACCEPTED; they do not block acceptance of prerequisite units.
Isolated unit test passes never prove combined correctness.

## Failure and recovery

Failed prerequisites block their dependants; independent branches may continue only
within existing authority/budgets. Do not integrate failed or partial outputs as accepted.
Repair uses a bounded brief, existing binding and remaining retry budget. Testers report
failures rather than repairing them. Stale evidence -> refresh/reverify affected checks;
changed scope/architecture -> ESCALATE_PLAN and pause affected writes. Failed integration
invalidates affected acceptance and downstream evidence, even if isolated checks passed.
Review REVISE consumes revision budget, then repair, revalidate and review again. BLOCK,
missing authority, unsafe rollback or exhausted budget -> stop affected work and report.
