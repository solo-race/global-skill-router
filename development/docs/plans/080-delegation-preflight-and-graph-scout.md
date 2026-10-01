# Delegation preflight and graph-scout integration plan — legacy record

Status: SUPERSEDED / LEGACY.
Date: 2026-09-30 (UTC+08:00).
Retired: 2026-10-01 (UTC+08:00).
Baseline: global-skill-set/master at 762770d23ccb21cd2835af0c916bb66da4c34ca5.
Owner request: document the preflight gaps, role ownership, and codebase-memory-scout integration in this local repository.

Retirement decision: OpenCodex experiments established that the extra route-readiness layer is not needed for normal delegated execution. The active `development-delegation` Skill therefore no longer invokes, documents, or deploys the bootstrap/router-preflight/runtime-receipt chain. The implementation is archived under `development/legacy/delegation-preflight/` for historical reference only and is outside the active deployment and default pytest surface. Graph-scout orchestration that remains useful is retained in the active Skill. The historical sections below are non-normative and must not be treated as current runtime requirements.

## 1. Goal and boundaries

Make the delegation gate describe the actual host, registered roles, effective routing evidence, and uncertainty. Stop conflating a failed detector, a static route declaration, and a verified model invocation.

Scope:
- Python bootstrap for the deployed delegation helper.
- Per-role route resolution, including OpenCodex routes and explicit provider overrides.
- Independent v1/v2 delegation capability checks.
- Structured readiness and provenance reports.
- One authoritative runtime role configuration per registered identity.
- Conditional use of the existing codebase-memory-scout role.
- Source/deployment contract alignment and focused regression tests.

Not authorized by this plan:
- Starting, resuming, retrying or probing a model task.
- Installing dependencies, changing proxy/security settings or reading credentials.
- Editing the user's global roles or applying a deployment automatically.
- Committing/pushing changes or updating unrelated legacy/reference repositories.
- Rebuilding OpenCodex, replacing the delegation framework, or introducing a general agent runtime.

Documentation approval is not implementation, deployment or live-test approval.

## 2. Evidence and confirmed gaps

### 2.1 Current source and deployed helper

Source:
- ../../skill/development-delegation/SKILL.md
- ../../skill/development-delegation/scripts/router_preflight.py
- ../../skill/development-delegation/scripts/test_router_preflight.py
- ../../skill/development-delegation/agents/registry.example.toml
- ../../skill/development-delegation/loops/implementation.md

The source helper and the inspected deployed helper have identical SHA-256:
a65410b1cc24b1f81cd0b5815947bfc4d146c18d3959d1197d19cb9299c7ab17.

The helper currently:
1. Hardcodes ROUTE=deepseek/deepseek-v4.1-flash and three *-deepseek identities.
2. Requires the same exact slug in the catalog and role profile.
3. Rejects any per-role model_provider field.
4. Requires catalog multi_agent_version=v2 for every DeepSeek role.
5. Resolves a user config plus a selected inline/standalone profile, but does not observe the full running session's effective configuration.
6. Returns unavailable for configuration/read failures; the skill also maps inability to run the helper to DeepSeek unavailable.
7. Always exits zero after producing its report, so exit success alone does not mean readiness.
8. Optionally GETs a loopback /models endpoint; this is not inference or proof of child execution.
9. Never verifies runtime routing itself. The existing skill asks for marker plus router metadata, but does not specify an implementable evidence acquisition/correlation contract.

The current regression test test_v1_route_blocks_every_deepseek_agent explicitly enshrines the overbroad v2 restriction.

### 2.2 Observed local configuration

Inspected on 2026-09-30; re-read before implementation because the user can change it:
- Main model: deepseek/deepseek-flash.
- openai_base_url: loopback port 10101, /v1.
- model_catalog_json: user-owned opencodex-catalog.json.
- multi_agent=true; multi_agent_v2.enabled=false.
- scout-deepseek: model=deepseek-flash, model_provider=deepseek.
- The declared deepseek provider points to api.deepseek.com.
- Ordinary scout/implementer/tester have separate user-selected GPT models.
- codebase-memory-scout: model=deepseek-flash, no explicit provider override, read-only sandbox.

The loopback URL passes the current URL-shape check. Do not report its port as the cause of rejection.

A parent routed through OpenCodex does not prove that an explicitly overridden child provider uses OpenCodex. Likewise a registered role or a model name does not prove actual upstream selection.

The large OpenCodex catalog could not be fetched through the bridge size limit. Exact catalog aliases/capability entries were NOT verified. The owner reports successful DeepSeek use through OpenCodex; no correlated request receipt was captured during this inspection.

### 2.3 Python startup gap

The skill requires Python >=3.11, but supplies no deterministic interpreter discovery entrypoint. The helper needs tomllib; generic repository conventions still describe Python 3.9+. Existing tests import the module using the already-running test interpreter and do not cover first-launch executable discovery.

The owner reports a first-run "no Python environment" error. The exact original stderr was not captured, so PATH, app-execution aliases, interpreter version, execution denial and other launch failures remain hypotheses. Do not claim Python is absent from the machine.

Observed 2026-09-30 (P1; sandbox versus unrestricted policy):
- Default PATH discovery reproduces the reported first-run failure inside the Codex sandbox: `py -3` exits 1 with "No suitable Python runtime found", `python` exits 1 without running the interpreter, and `python3` is not resolvable.
- The same candidates and the repository virtualenv work under an unrestricted policy, so this is an execution-policy denial class rather than a missing interpreter. The launcher must classify it and must never install or download anything.

### 2.4 Role ownership and deployment drift

deploy_skills.py copies internal module role files into the managed payload. It does not register them into the user's Codex config. registry.example.toml currently recommends copying role TOMLs into a separate agents directory.

A role file inside a Skill is not automatically a registered dispatch target under this repository's current contract. A registry entry can reference an existing role file; two physical copies are not inherently necessary.

During review, the deployed MODULE.md differed from source: it contained AI_IGNORE markers and fixed scout/implementer/tester dispatch, while source/loop text expected selected identity variables.
The owner removed the markers. A fresh bridge read at approximately 21:13 UTC+08:00 confirmed no AI_IGNORE lines in the deployed module; SHA-256:
ab242249bc3ba15f88cc04818f19cf0369f87ad7bb8982b2925808c815637c72.
Do not reintroduce the removed markers. Removal does not establish that all remaining source/deployment differences are reconciled.

Observed 2026-09-30 (filesystem and bridge read; re-read before implementing):
- The deployed `global-skill-router/library/development-delegation/` under the user Codex skills root contains only `loops/`, `modules/`, `references/`, `scripts/` and `MODULE.md`; the entire `agents/` directory is absent.
- The deployed `_platform/deployment-state.json` still lists nine `library/development-delegation/agents/*.toml` payload entries, so recorded state does not match deployed disk and deployment verification would report missing managed files.
- All shared files under `loops/`, `modules/`, `references/` and `scripts/` are byte-identical to source; the observed drift is confined to `MODULE.md` wording plus the missing `agents/` directory.
- The deployed `MODULE.md` uses fixed `scout`/`implementer`/`tester` dispatch and contains an extra supervision paragraph absent from current source `SKILL.md`.
- The `SKILL.md` gate forbids per-agent `model_provider = "deepseek"`, contradicting section 3.2's allowance for explicit role provider overrides and the host's registered `scout-deepseek`, `implementer-deepseek` and `tester-deepseek` definitions with `model = "deepseek-flash"` plus `model_provider = "deepseek"`; P2 must resolve this contradiction without changing routing semantics in P0.

- Role template inventory (review finding 080-P0-R3-01): source `development/skill/development-delegation/agents/` versus registered roles under the user Codex agents directory:
  - Source templates declare `scout.toml` model `gpt-6-sol`, `implementer.toml` model `gpt-6-sol`, `tester.toml` model `gpt-6-luna`, `planner.toml` model `gpt-6-astra`, `reviewer.toml` key `model_id` value `gpt-6-astra`, and `scout-deepseek.toml`, `implementer-deepseek.toml` and `tester-deepseek.toml` model `deepseek/deepseek-v4.1-flash`. No template exists for `codebase-memory-scout`.
  - Registered roles declare `scout` model `gpt-6.1-sol`, `implementer` model `gpt-6-astra`, `tester` model `gpt-6-luna`, `planner` model `gpt-6-astra`, `reviewer` model `gpt-6-astra`, `scout-deepseek`, `implementer-deepseek` and `tester-deepseek` model `deepseek-flash` with provider `deepseek`, and `codebase-memory-scout` model `deepseek-flash`. Reasoning-effort values differ for most roles.
  - Source `reviewer.toml` uses `model_id`, whereas registered role files use `model`, so the template cannot be copied verbatim.
  - Source `scout.toml` and `implementer.toml` name `gpt-6-sol`, which is neither registered model `gpt-6.1-sol` nor `gpt-6-astra`; the DeepSeek templates name `deepseek/deepseek-v4.1-flash`, which the user model catalog does not advertise.
  - Ownership is unchanged: registered role TOMLs remain authoritative for model, effort, permissions and tool bindings; module templates are examples and must never overwrite registered runtime settings.

### 2.5 Graph scout has no dispatch policy

The existing global codebase-memory-scout is registered and has a focused read-only contract:
- Usually 3–4 graph calls with bounded results and shallow traces.
- Tools: list_projects, index_status, check_index_coverage, search_graph, trace_path, get_code_snippet, get_architecture.
- Provisional positive discovery; no exhaustive, absence, dead-code or complete-impact claims.
- No state-changing operations.

The delegation loop does not name a selection rule for this role. Registration alone therefore gives it little practical use. Its bare deepseek-flash model also requires route validation; do not silently rewrite or assume its provider.

## 3. Target design

### 3.1 Bootstrap before provider checks

Add a thin Windows PowerShell launcher alongside the helper. Python remains the deterministic implementation; the shell wrapper only discovers and invokes it. Document this narrowly scoped launcher exception in repository conventions.

Discovery order:
1. Explicitly supplied interpreter path.
2. Host-local, explicitly configured existing interpreter from an approved runtime record, if available.
3. py -3, python, then python3 candidates.

For each ordinary discovery candidate, verify that it launches, is >=3.11, and imports tomllib. Resolve and record the actual executable/version. Do not trust executable existence alone. An invalid explicit override should report its error instead of silently selecting another interpreter.

Use bounded timeouts, argument arrays and quoted paths; no Invoke-Expression or shell-string interpolation. Resolve the helper relative to the launcher/module directory, never the repository CWD. Probe without installing packages, downloading Python, creating a venv, or changing the project.

Classify bootstrap failures separately:
- interpreter_not_found
- interpreter_too_old
- dependency_unavailable
- execution_denied
- probe_timeout
- helper_failed

An access-policy denial stops the affected operation; do not try another route to evade it. Ordinary missing or too-old discovery candidates may proceed to the next candidate. Capture diagnostic category without leaking environment values or credentials.

Provide a POSIX invocation contract using the same version validation for WSL. Never treat a Windows interpreter/config path as a valid WSL environment by assumption.

### 3.2 Per-role route resolver

Accept the exact registered identities selected for this session instead of scanning only three fixed DeepSeek names.

For each identity, report:
- role_id, registration source and profile path/hash.
- declared model slug and model/provider overrides.
- inherited configuration evidence and effective values when genuinely available.
- Codex-facing provider identity and redacted endpoint classification.
- optional router identity/version and upstream mapping evidence.
- delegation interface/capability evidence.
- unresolved layers and reason codes.

Resolve supported user/profile/role layers using documented host semantics. Inputs from CLI overrides, project configuration, host policy or session overrides must either be supplied by a supported effective-config source or remain explicitly unknown. A static file reader must not pretend to replicate all Codex precedence rules.

Use each role's actual slug when looking up catalog entries. Do not globally normalize aliases, infer providers from prefixes, or equate provider=openai with an OpenAI upstream when a router is configured.

An explicit role provider override is not intrinsically invalid. Evaluate the resulting path and host support; reject unsupported combinations with a specific reason. A direct-provider route and an OpenCodex route are distinct supported/unknown cases, not interchangeable proofs.

Only label a server as OpenCodex with an appropriate verified identity/config contract. A loopback /v1 URL alone identifies an endpoint shape, not a product.

Do not read broad router configuration containing credentials merely to resolve routes. Prefer a documented, narrow redacted mapping/status surface. If no such surface exists, report mapping unknown and propose the smallest separate integration; do not invent an endpoint.

### 3.3 Separate delegation capability from model identity

Represent independently:
- Runtime/host: Codex or SpineCodex product version and verified upstream baseline, if known.
- Selected interface: v1 or v2.
- Relevant feature/config state.
- Exact role registration.
- Catalog declaration.
- Observed runtime child dispatch evidence.

Do not require v2 when the selected host uses v1. Conversely, removing the old v2 gate is not proof that all routes support v1. Known unsupported combinations are blocked; unverified combinations remain unknown until adequate evidence exists.

### 3.4 Structured evidence states

Use separate fields rather than one overloaded available boolean:
- bootstrap: ready | blocked | unknown
- configuration: consistent | conflict | unknown
- catalog: present | missing | ambiguous | unchecked | error
- delegation: supported | unsupported | unknown
- endpoint: reachable | unreachable | unchecked
- runtime_route: verified | unverified | mismatch

Compute dispatch eligibility explicitly for the chosen operation and evidence requirements. Keep reason codes, scope and provenance. If a compatibility available field remains, document its exact meaning and never let it imply runtime verification.

Define a schema version and stable exit semantics:
- 0: a complete report was produced; consumers must still read readiness fields.
- nonzero: bootstrap/internal execution failure; emit a machine-readable error where possible.
- interrupt: 130.

A transient failure invalidates only affected evidence/roles. Do not permanently ban all DeepSeek identities for an entire session after a recoverable observation error. Invalidate stale success when the role/config/catalog/router identity or session context changes.

No implicit fallback from DeepSeek to a GPT/Codex-billed model. Selection changes remain explicit and obey the owner's approval requirements.

### 3.5 Passive runtime evidence before any active probe

Prefer existing sanitized execution/router receipts. Correlate child identity/session, request ID, timestamp, requested slug, route decision and reported upstream provider/model. Record attribution strength and limitations; router metadata is routing evidence, not cryptographic proof of the remote model's identity.

A unique response marker proves response association only. It does not prove a model identity. Catalog visibility, parent model name and model self-identification are also insufficient.

Define bounded retention/invalidation rules. Do not correlate merely by similar timestamps or reuse a prior session's success without matching context.

Static checks must never issue inference. An active child probe is a separate opt-in action requiring explicit approval, bounded scope and a stated cost/uncertainty. No probe should be added automatically to every session.

### 3.6 Single source of truth for roles

Adopt the deployment-owned runtime-role strategy for this environment:
- Managed Skill files contain role templates and workflow contracts.
- Global registered role TOMLs are authoritative for actual model, effort, permissions and tool bindings.
- The Skill references registered identity IDs rather than copying complete role instructions into its body.
- Deployment validates registration and drift but does not overwrite owner-selected runtime roles.

Separate workflow-owned role behavior from owner-owned execution settings in documentation and verification. Flag template/behavior differences for review instead of blindly replacing entire files.

An optional future direct-reference layout may point config_file into a managed payload, but requires explicit migration and an override-preservation policy. Do not maintain both layouts or perform that migration as part of the initial repair.

Reconcile fixed-role and session-selection policies into one documented mechanism. Fixed defaults must explicitly initialize the identity mapping; user-selected identities must be carried consistently through planning, implementation and retry. Never use an uninitialized *_identity variable or silently fall back to default.

### 3.7 Integrate codebase-memory-scout conditionally

Keep the existing role ID: codebase-memory-scout. This is integration of an existing role, not automatic creation of an extra agent on every task.

Select graph scouting when:
- Relevant files/symbols are not yet known.
- Cross-file call/dependency relationships or architectural entrypoints materially guide the task.
- A suitable project/index with adequate coverage is available.

Use ordinary scouting directly when:
- The user supplies exact files or a narrow known defect.
- The task is configuration/document verification.
- Graph coverage is unavailable or insufficient.
- A graph pass would duplicate already adequate evidence.

Workflow:
1. Supervisor classifies the discovery question from available task evidence.
2. Graph scout resolves one unambiguous graph project/worktree and checks index status/coverage.
3. Run a bounded graph pass, normally 3–4 graph queries; count metadata checks separately and keep total work bounded.
4. Return exact paths/symbols, relationship evidence, index identity/freshness, coverage limitations and source checks still required.
5. Verify relevant current source before implementation or consequential impact conclusions.
6. Reuse the evidence packet; do not automatically repeat whole-repository discovery with another scout.

Fallback:
- Ambiguous project, stale/partial coverage, unsupported files or unavailable tools -> report the gap.
- Continue with source inspection through the selected authorized role when feasible.
- Switching to a different registered role/model requires the existing selection/approval policy; never silently incur different quota.
- Do not rebuild the index or launch extra agents merely to make a graph precheck pass.
- No "not found means absent", exhaustive impact, dead-code or readiness claims from graph evidence alone.

Preflight includes this role's model routing and required MCP tool capabilities. Preserve its read-only sandbox and allowlist, but do not claim that an allowlist alone proves the complete effective tool surface.

## 4. Implementation sequence

### P0 — Freeze contracts and reconcile ownership

Deliver:
- Capture current source/deployed differences and runtime role registrations without reading secrets.
- Choose and document the single identity-selection mechanism.
- Define the report schema, reason codes, evidence scope and consumer decisions.
- Preserve the owner's removal of AI_IGNORE markers.

Exit:
- No contradictory fixed/selected dispatch instructions.
- Missing evidence is distinguishable from unsupported configuration.
- No deployment or role settings overwritten.

### P1 — Deterministic bootstrap

Deliver:
- Thin Windows launcher and documented WSL entrypoint.
- Interpreter/version checks, safe invocation, timeouts and classified failures.
- Python dependency/version conventions aligned with the actual helper.
- Colocated launcher contract/subprocess tests under the approved local test environment.

Exit:
- First invocation works with a supported existing interpreter from arbitrary CWD.
- Missing/old/denied runtimes produce explicit diagnostics without provider misclassification.
- No environment installation or automatic downloads.

### P2 — Role-aware preflight

Deliver:
- Parameterized role resolution; actual slug/provider/catalog handling.
- Independent v1/v2 capability checks.
- Structured static evidence and optional bounded loopback catalog checks.
- Tests replacing the blanket v1-rejection expectation.

Exit:
- Fixtures matching the inspected OpenCodex configuration are not rejected solely for the old slug or v1.
- Explicit provider overrides are represented accurately.
- Unknown session overrides or missing mapping evidence remain unknown.
- No inference requests or credentials in output.

### P3 — Graph-scout orchestration

Deliver:
- Role template/registration example for the existing codebase-memory-scout identity.
- Discovery selection policy integrated into planning and implementation loops.
- Bounded graph evidence packet and source-verification/fallback rules.
- Route verification for its actual runtime model configuration.

Exit:
- Cross-file discovery can select graph scout; known-file tasks skip it.
- Ordinary scout and graph scout do not duplicate broad discovery by default.
- Coverage failure and model fallback are explicit.
- No automatic indexing or extra model calls during static preflight.

### P4 — Provenance and deployment validation

Deliver:
- Passive receipt input contract and validation with sanitized fixtures.
- Schema/source hashes and meaningful invalidation criteria.
- Managed-payload tests; registration validation without overwriting global role files. Reconcile source role templates against registered role TOMLs, including the unrecognized `model_id` key, and validate template keys without changing registered runtime settings.
- Document the runtime-probe approval boundary and recovery procedure.

Exit:
- Source-generated MODULE.md and loop contracts agree.
- No stale AI_IGNORE markers or manual deployment edits are silently restored.
- Runtime settings remain owner-controlled.
- A verified receipt cannot be reused for a different role/session/route.

### P5 — Optional controlled acceptance

Requires separate approval for any local execution, deployment and potentially metered live operation as applicable.

Order:
1. Run focused offline tests in the selected authorized environment.
2. Assemble and verify a temporary payload without touching active deployment.
3. Review diff and preservation of user runtime roles.
4. Apply an explicitly approved deployment with existing managed snapshot/rollback.
5. Verify registration and static preflight without inference.
6. Only if separately approved, exercise one bounded read-only child assignment and inspect correlated routing evidence.
7. Record offline pass, deployed-static pass and live verification as separate outcomes.

Never describe offline fixtures as a successful live DeepSeek or graph-scout run.

## 5. File-level change map

Expected implementation targets:
- ../../skill/development-delegation/scripts/router_preflight.py — role-aware evidence model.
- ../../skill/development-delegation/scripts/test_router_preflight.py — current routes, v1/v2 and error cases.
- New bootstrap launcher plus colocated tests under that scripts directory.
- New concise preflight/provenance and scout-selection reference documents within the module.
- ../../skill/development-delegation/SKILL.md — gate, identity ownership and recoverable states.
- ../../skill/development-delegation/loops/implementation.md and loops/planning.md — conditional graph discovery and consistent identity mapping.
- ../../skill/development-delegation/references/evidence-report.md and planning-packet.md — graph coverage and route provenance fields.
- ../../skill/development-delegation/agents/registry.example.toml and a codebase-memory-scout template — examples, not automatic runtime replacement.
- ../../tools/deploy_skills.py and focused tests — only if necessary for registration/drift validation; preserve managed ownership boundaries.
- ../repo-conventions.md — supported Python and thin-launcher policy.
- ../../skill/manifest.yaml — update only if actual dependency/packaging changes require it; no speculative framework version churn.

Global ~/.codex/config.toml, ~/.codex/agents/*.toml and deployed payload are inspection/acceptance targets, not automatically authorized implementation outputs.
The optional independent source library under development/skill-repos/ is not the managed source of truth; do not silently edit it or references/.

## 6. Regression matrix

Bootstrap:
- Python available only through py; Python only through python; only Python 3.10; none installed.
- Broken app alias, paths with spaces/non-ASCII, arbitrary CWD, explicit interpreter invalid.
- Permission denial, timeout, valid Python but helper error; no automatic download.
- Windows and WSL paths/config homes remain separate.

Routing/capability:
- OpenCodex loopback + deepseek/deepseek-flash + v1.
- Legacy route slug still supported when genuinely configured.
- Explicit child provider override vs parent router inheritance.
- Bare slug without an established alias -> unresolved, not guessed.
- Catalog missing/duplicate/malformed/oversized/stale.
- Ambiguous profile or unknown session override.
- Role unregistered, wrong name, unsupported effort, disabled delegation.
- v2-only and v1-only host scenarios; unknown capability remains unknown.
- Router stopped, redirected catalog, slow endpoint and transient recovery.
- Probe scope/fingerprint changes invalidate affected prior evidence.

Graph scouting:
- Correct/ambiguous project, dirty worktree and index/source revision mismatch.
- Partial/excluded file coverage, missing tools and empty results.
- Known-file task skips graph; architecture task selects bounded graph discovery.
- No graph-derived absence/exhaustiveness claims.
- Explicit fallback policy and no automatic extra model invocation.

Deployment/provenance:
- Source/payload behavior matches and no manual gate bypass survives assembly.
- Owner runtime models/effort/permissions unchanged by Skill update.
- Registration points to one existing authoritative file.
- Marker without route receipt does not verify routing.
- Wrong request/session/role, expired receipt and fallback upstream are rejected.
- Static preflight has zero inference calls and outputs no secrets.
- Exit zero with unknown/blocked readiness cannot be consumed as a pass.

## 7. Completion criteria

Implementation is complete only when the focused tests and controlled payload verification pass, documentation matches the implemented contract, and runtime settings are preserved.
Deployment and live acceptance remain separately recorded gates.
The owner receives a per-file diff mapping, exact checks run, checks not run, and any remaining unknowns.
