# Explicit Legacy Compatibility

Load only when the operator explicitly chooses `compatibility: legacy`. Existing
session data or missing policy fields do not select it. Record the choice; returning
to dynamic also requires explicit selection. Current safety, quota, permission and
mandatory high-risk review requirements remain applicable and cannot be weakened.

Preserve the earlier workflow semantics:
1. Before repository discovery/planning/implementation, ask for exact host-registered
   scout_identity, implementer_identity and tester_identity if not already selected.
   Show only registered choices (native and matching DeepSeek options when present).
   Unset identities are errors; preserve choices across retries.
2. Separately ask, unless explicitly answered for this session:
   `Session supervision: is a human supervisor actively present for this session? [Yes/No]`
   Map Yes to human_supervisor=true / interactive; No to false / unattended. Never
   infer presence. Keep the setting stable until the operator changes it.
3. Dispatch via the exact selected registered identities; use registered planner,
   reviewer and conditional codebase-memory-scout for those assignments. No inline
   planner/implementer fallback and no generic substitute. Missing registration or
   route stops that assignment for an explicit change.
4. Explicit planning or absence of a usable detailed current-phase plan enters the
   planning loop. If no master project plan exists, establish it before detailing the
   phase; otherwise preserve it. The phase must have bounded units, dependencies,
   validation and exit criteria before execution.
5. Supervised work has no automatic independent review unless requested, except the
   mandatory high-risk override. Unattended work reviews newly created plans and every
   phase close; PASS is required. REVISE is bounded repair/revalidation/review, BLOCK
   stops. Dynamic review policy may add stricter review but never remove these gates.

Use current graph discipline, isolated DAG rules and finite budgets. Legacy gates are
an explicit compatibility overlay, never an alternate route around safety. Do not
silently migrate owner registrations, model/provider/effort settings or quota choices.
