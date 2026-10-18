# Dynamic Delegation Contracts

## Objective and authority

Replace the mandatory role-selection/planning ceremony with bounded, policy-driven
supervision. This is declarative orchestration guidance, not a runtime scheduler.
Keep the existing router continuation and deployment boundaries. This plan covers
only the managed delegation module; host configuration, registered agent settings,
external source repositories, live dispatch and deployment are not changed.

## Evidence and design decisions

The previous entry mandates three selected identities, a separate human-presence
question, a detailed plan for every task, fixed registered planner/reviewer dispatch,
and unattended-only review. Existing loops and role templates repeat those rules.
Architecture references 01, 02 and 04 require progressive loading, explicit task
classification, bounded retries, authority boundaries and evidence-based acceptance.
Keep graph selection and its provisional evidence discipline unchanged.

Separate four dimensions: task mode (Direct/Planned/Exploratory), human availability
(interactive/unattended), review policy (on_demand/risk_based/always), and host binding
(role behavior/capabilities/identity/model). Defaults never override user approval,
chosen identities or host permissions. High-risk review cannot be disabled. Preserve
old ceremonies only through explicitly selected legacy compatibility.

## Implementation units and dependency DAG

1. CONTRACT: thin entry plus policy YAML, assignment/authority schema and deterministic
   classification, budgets and transitions. Acceptance: bounded Direct works without
   a master plan; ambiguity selects read-only exploration; missing authority blocks.
2. ROLES (depends CONTRACT): load-on-assignment scout/planner/implementer/tester/reviewer
   modules and optional specialist contract; reconcile every role TOML without changing
   its model/effort/sandbox/tool bindings. Acceptance: no mandatory five-role team,
   registered settings remain examples/owner-controlled, no silent fallback.
3. LOOPS (depends CONTRACT, ROLES): Direct/Planned/Exploratory loops, independent review,
   isolated DAG execution, integration verification and bounded recovery. Acceptance:
   parallel writes require disjoint ownership and isolated workspaces; cycles, stale
   evidence, failed prerequisites and conflicts cannot produce acceptance.
4. PACKETS (depends LOOPS): update existing references, legacy profile, graph selection
   and metadata. Acceptance: old unconditional planning/review/identity rules remain
   only in explicitly selected legacy guidance; all links resolve within skill root.
5. VALIDATE (depends all): parse YAML/TOML, inspect links and contradictions, run repository
   validator and relevant regression/deployment tests through the owning coordinator.
   Acceptance: report actual checks, failures and unrun live-host checks separately.

## Execution and validation details

The contract writer owns development/skill/development-delegation except scripts and
this plan. Other repository/tool changes are coordinated separately. Do not parallelize
writes to the same files. Check source diff and template execution-setting preservation.
Validate policy enums/defaults, role mappings, required high-risk review, all three modes,
legacy explicit selection, bounded experiments, permissions/quota gates, stale evidence,
cycle/failure handling and combined-tree validation. Temporary payload assembly may
verify packaging; it must not change active deployment or owner registrations.

## Risks and stop conditions

Policy YAML does not dispatch agents or enforce host sandboxes. A host adapter/supervisor
must interpret the contract and enforce capabilities. Stop on missing authorization,
unknown quota permission, unavailable explicitly selected identity, exhausted budgets,
ambiguous ownership, conflicting scope or unverified integration. Do not replace a model,
expand scope, index a repository or retry a metered action merely to finish a workflow.
Legacy semantics retain their session questions and unattended phase/plan review, while
mandatory high-risk review and current safety/approval requirements apply in all modes.

## Completion and rollback

Completion requires internally consistent contracts and passing relevant offline checks.
Live dispatch, deployed configuration and upstream/provider identity remain unverified
unless separately observed with authorization. Roll back by restoring this bounded source
diff; no data migration or host configuration change is part of this work.

## Delivery phases and synthetic scenarios

P0 freezes the authority, routing and mode contracts (CONTRACT). P1 implements role
loading and capability/identity separation (ROLES). P2 completes loops, packets and
legacy reconciliation (LOOPS, PACKETS). P3 runs offline regression and temporary
payload verification (VALIDATE). Test scenarios are synthetic repository fixtures,
including bounded document fixes, cross-file dependency work and read-only uncertain
requests. They do not run a live customer-screening project or dispatch model agents.

## Verification record — 2026-10-18

Implemented P0–P3 in the managed module and router registration; no independent source
repository, live user deployment or host agent registration was changed.

- Baseline at `c9109018aeb470c96f5b710c98a13e8ecf16064d`: 238 passed, 1 failed because
  an optional ignored `references/access-vba-dev` checkout was absent.
- Split that legacy test into optional provenance verification (explicit skip when
  checkout absent) and always-on managed fixture-safety checks. No production fixture
  substitution, reference fabrication, or safety-assertion removal was used.
- Final `uv run python development/tools/run_tests.py -q`: **292 passed, 1 skipped**,
  including 53 new dynamic-delegation cases. The skipped check is optional provenance;
  absence inside an existing but incomplete reference checkout still fails.
- `uv run python development/tools/validate_skills.py`: `ok: true`, no errors.
- Temporary payload construction, apply/verify, source/deployed link checks and private
  module discovery checks pass; these do not modify a live installation.
- All pre-existing role TOMLs parse and retain model/provider/effort/sandbox/tool settings.
- Independent contract review: PASS after correcting a graph-discovery pointer and
  separating per-unit ACCEPTED from PHASE_ACCEPTED to prevent A→B dependency deadlock.
- `git diff --check`: clean.

Environment note: commands used `UV_CACHE_DIR=/tmp/gsr-uv-cache` because the default
cache was read-only. Policy evaluators are test-only reference models. Real agent
scheduling, isolation enforcement, provider availability, quota accounting and live
customer-screening/Auto-Manual-Production behavior remain **UNVERIFIED**.
