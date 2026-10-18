# Supervisor Contract

## Task record and classification

Persist a bounded task record: objective, acceptance, authorized scope/exclusions,
mode with rationale, supervision, review policy, risk triggers, authority source,
selected identity/model constraints, capabilities, budget limits/counters, repository
revision plus dirty-file fingerprints, dependency DAG, ownership, validation and status.
Use existing project conventions; no new scheduler/database is implied. YAML is a
reviewable policy input, not code that enforces host permissions or launches workers.

Resolve higher-priority safety/host/user constraints first, then explicit task choices,
then policy defaults. Defaults cannot authorize an action. If explicit choices conflict
with eligibility or safety, pause that action and ask; do not silently change the task.
An unspecified human mode defaults to interactive for asking questions, not as evidence
that a human is present. Unattended requires an explicit task/session selection.

Classification precedence: unresolved scope/solution -> Exploratory; otherwise explicit
planning request, complex dependency coordination or high-risk change -> Planned;
otherwise bounded known low-risk work -> Direct. An explicit valid mode wins. A request
for planning may create a plan containing a bounded discovery unit instead of inventing
unknown facts. Missing a master plan alone never forces Planned in dynamic mode.

## Role, capability, identity and model

Read `routing/capabilities.yaml` when binding a role; its requirements are not permission grants.
A role defines responsibilities/output. Capabilities are the actual tools, filesystem,
network and mutation rights required and allowed. Identity is a host registration or
explicitly permitted generic agent. Model/provider/effort are host execution settings,
not inferred from role names. Record each independently in every assignment.

Preserve explicit identity/model selections across retries. The host's registered
configuration owns actual routing; templates are optional examples, never permission
to overwrite settings. Do not probe inference to establish readiness. Missing or
unavailable chosen identity stops that assignment; report host evidence and obtain an
explicit change before substitution. Never silently switch model/provider, quota pool,
permission level or paid route. If cost/quota permission is required or uncertain,
obtain it before creating, starting, continuing or retrying the affected work.

Without a chosen identity, use only an already authorized host/default binding; a
generic host agent can receive one role module and bounded context if its actual
capabilities fit. Do not demand pre-registration of five roles. If no binding is
adequate, ask for the missing choice instead of inventing one. Loading a role grants
no tools or authority. Host-denied operations remain denied under every mode.

Supervisor owns classification, assignment, acceptance and escalation. Assign only
needed roles; it may perform a small role inline only when authorized, with explicit
role boundaries and actual evidence. Independent review must use a separate reviewer
context. Load role instructions on assignment, not all role files on activation.

## Finite budgets

Policy budgets are conservative ceilings, not spending authorization. Record limits
and counters before dispatch; stricter host/user limits win. Count every launch,
continuation and retry toward total assignments, including failed dispatch attempts.
Count a repair after failed validation as an implementation retry; each new review
repair cycle, planning revision and evidence refresh consumes its named counter.
Initial work consumes total assignments but not a retry counter. Exploration passes
and experiments consume their own counters as well as any applicable assignments.

Check all relevant remaining counters before action and increment on action start.
Counters survive mode changes, handoffs and resumes; do not reset them to escape a
limit. A pass is one bounded question set and tool allowance declared in its brief.
Explicitly authorized experiments also need a finite experiment count (default zero),
time/tool/cost ceilings, workspace, rollback and stop conditions. No implicit retries.
Elapsed-time or cost ceilings, when supplied, are checked alongside count limits.

Exhaustion -> BLOCKED with completed evidence, remaining work and the exact additional
budget/authority needed. Only explicit authorized revision may increase a ceiling;
permission and quota approvals still apply separately. Narrowing scope is possible
only without dropping requested acceptance silently.

## Deterministic transitions

- NEW -> classify -> READY (Direct/Planned usable contract) or EXPLORING.
- EXPLORING -> bounded evidence -> Direct or Planned only when eligibility and authority
  are established; unresolved after its budget -> BLOCKED. Never auto-promote to writes.
- Planned without executable units -> PLAN_DRAFT -> applicable review -> PLAN_SEALED;
  missing evidence -> NEED_EVIDENCE within refresh budget; unresolved decisions -> BLOCKED.
- READY -> RUNNING only after dependencies, ownership, authority and budgets pass.
- RUNNING -> VALIDATING -> VERIFIED only with criterion-level current evidence.
- Failed implementation -> RETRY_IMPLEMENTATION within budget; stale validation ->
  REVERIFY after refreshing affected evidence; material contract change -> ESCALATE_PLAN.
- VERIFIED -> integration validation -> applicable review -> ACCEPTED. Planned phase
  closure uses PHASE_ACCEPTED; a sealed plan is not implementation acceptance.
- Review REVISE -> bounded repair/revalidation/review within revision and assignment
  budgets; BLOCK or exhaustion -> BLOCKED; PASS never authorizes extra actions.

Any mode transition preserves permissions, chosen bindings, counters and evidence
provenance. Changes to authority/scope need the appropriate approval before execution.
Invalidate only affected evidence on revision, file, environment, configuration or
criteria change; no stale PASS may authorize acceptance. An unavailable check is
NOT_RUN/BLOCKED, not PASS. Resume rechecks state and dependencies before dispatch.
