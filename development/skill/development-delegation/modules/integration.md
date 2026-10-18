# Integration Contract

Load only when combining isolated outputs or reconciling a shared dependency boundary.
The integrator is an on-demand capability, not a mandatory standing agent. It can be
assigned to an authorized supervisor/implementer binding; selected identities and all
permission/quota constraints still apply. Receive unit IDs, accepted prerequisite
states, base revisions, diffs, exclusive ownership, target baseline and exact checks.

1. Verify outputs are within scope and based on recorded state. Inventory unrelated
   dirty work and preserve it. Reject failed/partial units, stale bases, missing
   prerequisites, unowned files and changes to undeclared shared resources.
2. Integrate in deterministic topological order (stable lexical ID tie-break). A merge,
   cherry-pick or file application must be within explicitly authorized write scope.
   Do not reset, discard or overwrite unrelated work. Conflicts pause affected units
   for bounded reconciliation; no automatic semantic choice or scope expansion.
3. Record the combined tree's revision/dirty fingerprint and execute declared combined
   checks. Individual branch tests are insufficient. A failed check invalidates affected
   unit acceptance and dependent evidence; retain unaffected evidence with provenance.
4. Return integrated paths, baseline/output identity, exact checks/results, conflicts,
   residual risks and rollback state. Required independent review uses another context.
   Only verified integrated units become ACCEPTED; overall phase exit criteria are
   checked at phase close, not demanded before each prerequisite can be accepted.
   Incremental unit checks must not require unfinished successor units; if they do,
   correct the unit boundaries/dependencies before dispatch instead of waiving checks.

Rollback uses only the approved, non-destructive recovery procedure for owned outputs.
If restoration could lose unrelated work, is unsafe or fails, stop and report exact
state. No forced resets, permission changes or external publication are implied.
