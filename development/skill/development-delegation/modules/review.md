# Independent Review

Review policy is independent of interactive/unattended supervision. Evaluate risk at
classification, plan sealing, scope change and delivery/integration boundaries.

- on_demand: review when requested, plus mandatory high-risk override.
- risk_based: review material risk, uncertain evidence or mandatory triggers.
- always: review every plan and delivery boundary.
- All policies: security/permissions, destructive/irreversible changes, migrations/data
  loss, external/production effects and consequential compatibility/API changes require
  independent review. Unknown material risk is unresolved, never assumed low-risk.

High-risk plans require review before execution; delivered changes require review of
the actual integrated state before acceptance. Review is additional to required user
approval and cannot grant permission. Interactive cannot waive a mandatory review;
unattended cannot waive an approval. Legacy compatibility adds its historical gates.

Use a separate read-only reviewer context with references/review-package.md: contract,
diff/plan, source-backed validation, repository fingerprint, prior findings and risks.
Do not pass implementer private reasoning or ask the reviewer to repair. Review checks
scope, criteria, reproducibility, skipped checks, dirty/generated state, dependencies,
rollback and consequential risks. A plan review checks executable units and assumptions;
no whole-project master plan is required for a bounded dynamic plan.

Return PASS, REVISE or BLOCK. Every REVISE/BLOCK finding includes finding_id, severity,
criterion_or_source, evidence and required_change. PASS requires sufficient current
evidence, not plausibility. REVISE -> bounded authorized repair and fresh validation,
then review within counters. BLOCK or exhausted budget stops affected work. If required
review is unavailable, report BLOCKED; never silently approve or replace the reviewer.
