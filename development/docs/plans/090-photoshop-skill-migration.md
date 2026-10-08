# Photoshop skill migration

Status: original draft phase and current activation phase **PHASE_ACCEPTED**. The activation amendment was **PLAN_SEALED** under the supplied independent planning reviewer PASS and is deployed to `C:/Users/tiany/.codex/skills`. Pre-apply validation/review, actual apply, postapply tester verification, and independent acceptance review passed. Native operations remain **UNVERIFIED**. Supplied reviewed source `4039f71d23383d6615c1b2235615e5626302fad2` is eligible for adaptation; retain this immutable implementation pin separately from the requirements-plan reference.

## Evidence and decision

The sole upstream requirements baseline is [commit d3f2a1e6b6fb654b060abd2bb30c6434b6b0d56d, §§7–8](https://github.com/solo-race/photoshop-mcp-windows-first-pnpm-migration/commit/d3f2a1e6b6fb654b060abd2bb30c6434b6b0d56d). Treat this SHA as a **requirements-plan reference**, never as an implementation pin or evidence of completed upstream capability.

The scout evidence unit is complete at clean local HEAD `d968802899c164df9d2f371182af0e1bdd65ee6f`. Scout findings establish the canonical origin, historical `image-editing-agent`, and discovery LICENSE: MIT, copyright 2026 `rookietopred02-gif`. The historical skill is not an eligible reviewed adapted source. At the inspected upstream requirements-plan revision above, no eligible reviewed adapted implementation was found.

The accepted draft was an original, self-contained local operating contract without an upstream skill copy; source registration, active status, and router composition were deferred in that phase. The new activation phase uses the supplied reviewed eligible implementation `4039f71d23383d6615c1b2235615e5626302fad2`, with an optional, absent local checkout. Draft acceptance does not certify Photoshop availability or real operation safety.

## Accepted draft scope (historical)

The accepted draft phase had this exact six-file write allowance:

1. `development/docs/plans/090-photoshop-skill-migration.md`
2. `development/skill/manifest.yaml`
3. `development/skill/photoshop-ops/SKILL.md`
4. `development/skill/photoshop-ops/agents/openai.yaml`
5. `development/skill/photoshop-ops/references/operation-contract.md`
6. `development/skill/photoshop-ops/references/provenance.md`

That phase permitted no other tracked changes, deployment payload writes, `--apply`, or live operations. These historical limits do not prohibit the separately scoped activation and deployment below. Preserve concurrent work and leave `000-platform-skeleton.md` unchanged. Across both phases, do not change runtime code, pnpm tooling, upstream repositories, project art, or assets; do not install, register, configure, launch, or operate Photoshop, invoke COM, create source checkouts, or run `test:real`.

## Accepted draft contract and acceptance

### Registry and discovery

Add one manifest entry with these values, following the existing schema:

```yaml
name: photoshop-ops
path: development/skill/photoshop-ops
status: planned
deployment_role: module
routing_scope: global
routing_priority: 80
routing_outcome: terminal
routing_selector: Operate selected local Adobe Photoshop documents through registered MCP; excludes imagegen, repository implementation, and MCP security review.
scenarios: []
deps: []
composed_of: []
entrypoint: true
version: 0.1.0
```

The selector must remain at most 180 characters. In the accepted draft phase, no source record, active entry, or router composition was added. Planned status excluded the module from both payload and generated routes, even when its directory existed; the activation phase intentionally changes that status and composition together.

`SKILL.md` must be short, English, and kilobyte-scale. Frontmatter contains exactly `name: photoshop-ops` and a one-sentence `description` ending with a “Use when …” trigger for the same document-operation scope. `agents/openai.yaml` supplies `interface.display_name`, `short_description`, and `default_prompt` containing `$photoshop-ops`. Resolve references against the skill's own root; keep the detailed contract in `references/operation-contract.md` and provenance in `references/provenance.md`. Runtime decisions must not depend on an optional source checkout or this plan.

### Availability and authority

Before operations, establish the actual registered MCP tools, their capabilities and version, registration policy, selected document identity, and Photoshop/COM availability. Disclose whether an authorized availability check may launch Photoshop; checking availability is not itself launch authorization. Missing registration, capability, version evidence needed by the operation, or COM availability means **unavailable** for that operation.

Allowed operations are the intersection of task authorization, registered MCP policy, actual capabilities, and project art constraints. Do not invent tool names or claim unobserved features. Exclude raw scripts, JSX, SendKeys, Photoshop Actions, automatic fallback, installation, registration, and configuration changes. Missing supported operations stop the task rather than expanding authority. Reports and saved report outputs are opt-in and require authorized destinations.

### Mutation and recovery

High-impact actions require explicit authorization covering the target, operation, output, and recovery. Identify protected layers and preserve them. Use an authorized working copy or a verified backup/rollback path before destructive operations. Photoshop history does not undo file writes; an unverified history checkpoint cannot justify destruction. Stop when required protection or recovery cannot be established. Restore only through an authorized, verified recovery path.

### Preview and disclosure

Default preview handling is local-only. Sending previews to any cloud receiver requires separate verified consent identifying the receiver and disclosure scope, including base64 data and tool image blocks. Window capture, layer preview, and production output are distinct artifacts with distinct authority; never substitute one for another. No unapproved UI capture. Capability discovery does not authorize a tool invocation that implicitly captures or transmits imagery.

### Project handoff

Require a handoff carrying `project_id`, document/layer identifiers, allowed operations, canvas coordinate conventions, H160-palette references when applicable, output paths and formats, approval requirements, and preview policy. Enforce the project's registered output rules; do not expand permitted output paths or overwrite source files (PS01). Preserve the project's responsibility for art decisions. Do not automatically fit, center, scale, quantize, feather, or rasterize without approval. Missing art or placement decisions return to the project owner; the operating skill does not invent them.

### Results and reporting

By default, return in conversation the actual changed layers, operations performed, outputs produced, and unverified items (PS02). Write a report only when the user or project explicitly asks for one and its output path is authorized under the project's registered output rules. Project art QC and owner acceptance remain with the art skill or designated reviewers.

### Provenance

The accepted draft recorded the canonical origin `https://github.com/solo-race/photoshop-mcp-windows-first-pnpm-migration`, requirements-plan SHA, and then-missing reviewed implementation pin separately. Preserve the fact that the original draft copied no upstream skill, the historical skill's ineligibility at the inspected requirements revision, and LICENSE discovery. Activation must update current provenance to the reviewed implementation and preserve the applicable MIT notice and attribution for adapted material; original drafting alone does not establish adaptation eligibility.

## Accepted draft work units (historical)

| Unit | Owner and input | Deliverable and completion gate |
|---|---|---|
| 0. Evidence | Scout; supplied clean HEAD and §§7–8 findings | Already complete as supplied evidence. Keep requirements provenance separate from implementation eligibility; do not repeat broad discovery. |
| 1. Draft | Implementer; this plan and relevant local conventions | Original four-file skill plus planned manifest entry, within the six-file allowance. Preserve others' edits. All contract requirements above are present; no source or router activation. |
| 2. Static validation | Tester; completed draft | Existing validator, targeted existing tests, and read-only isolated-target deployment plan pass. Record exact commands, outcomes, and planned exclusion evidence. No live operations. |
| 3. Acceptance | Independent reviewer; draft diff and tester evidence | Unattended **PASS** against scope, contract, provenance, and deployment exclusion. Explicitly verify PS01 (`project_id`, registered output rules, no expanded output paths or source overwrites) and PS02 (default conversation results, explicitly requested reports at authorized paths, art QC and owner acceptance retained by the art skill or designated reviewers). Return concrete issues to the owning unit; repeat only affected checks. |

These units completed under the sealed draft plan. The implementer does not run the test/build suite. Their reviewer PASS accepted only the draft; activation requires the separate review gate below.

### Tester checks

Use the existing environment and tools; do not introduce dependencies, fixtures, or test scaffolding. From the repository root, run:

```powershell
uv run python development/tools/validate_skills.py
uv run python development/tools/run_tests.py development/tools/test_validate_skills.py development/tools/test_deploy_skills.py
uv run python development/tools/deploy_skills.py --target-root .tmp/photoshop-plan-target
```

The last command is a read-only plan for an isolated target, without `--apply` or live target defaults. Use the existing repository temporary-directory conventions. Confirm the planned Photoshop module contributes no payload files, global route, scenario route, or router composition. Existing tests check validator/deployment behavior; reviewer inspection must also cover this specific entry and the prose contract. Do not equate static success with real MCP or Photoshop validation.

Inspect the bounded six-file diff for unintended changes; distinguish pre-existing/concurrent edits from this unit's changes. Verify selector length, frontmatter/interface shape, relative references, self-containment, manifest values, and absence of invented implementation pins. If existing tools cannot establish planned exclusion or require out-of-scope changes, report the missing evidence or required scope change rather than broadening the phase.

## Activation and deployment amendment — PLAN_SEALED

### Scope and source

The sealed amendment permits exactly the prior six files plus these three, for a nine-file repository write allowance:

7. `development/docs/scenario-routing.md`
8. `development/tools/test_deploy_skills.py`
9. `development/tools/test_control_integration_p3.py`

No other repository files may change under implementer ownership. PS03 was resolved separately by the user's one-line model correction in `development/skill/development-delegation/agents/implementer.toml`, the user-owned tenth file; preserve that correction, which is included in the reviewed deployment payload. This does not expand the implementer's nine-file repository allowance. The only deployment target is `C:/Users/tiany/.codex/skills`, using existing deployment tooling after reviewer PASS; tool-managed payload, inventory, and recovery artifacts there are authorized only for that deployment. No upstream/runtime/pnpm/COM work, source checkout, Photoshop operation, or asset editing is included.

The supervisor supplies authoritative reviewed eligible implementation `4039f71d23383d6615c1b2235615e5626302fad2` (PR1 merge with an identical reviewed implementation tree). Use this immutable SHA for the source entry, separately from the requirements-plan SHA. The optional source record must contain all existing-schema required fields:

- `id: photoshop-mcp-windows-first-reference`
- `path: development/skill-repos/photoshop-mcp-windows-first-pnpm-migration`
- `kind: development-repository`, `required: false`
- `origin: https://github.com/solo-race/photoshop-mcp-windows-first-pnpm-migration`
- `pinned_ref: 4039f71d23383d6615c1b2235615e5626302fad2`
- `version: 4039f71d23383d6615c1b2235615e5626302fad2` (source snapshot version).
- `description: Optional reviewed upstream source for the self-contained Photoshop operating skill.`

The checkout is absent and stays optional; neither validation, deployment, nor deployed decisions may require it. If reviewed adaptation evidence is missing, stop at that evidence boundary without creating a checkout or substituting a pin.

### Atomic repository change and acceptance

Adapt only the relevant reviewed skill material. Update `SKILL.md` and self-contained references/UI metadata as needed to reflect the current operating contract, preserving every availability, authorization, preview, recovery, project-art, PS01, and PS02 requirement above. Update provenance to distinguish original draft history, requirements-plan SHA, reviewed implementation SHA, and adaptation; remove stale current claims that the implementation pin is missing. Preserve the applicable MIT copyright 2026 `rookietopred02-gif`, permission notice, and attribution with adapted material.

In one coherent change, register the optional source, set `photoshop-ops` to `active`/`module`/`global`/priority `80`/`terminal`, and add it to `global-skill-router.composed_of`. Keep the selector at most 180 characters, `scenarios: []`, `deps: []`, the module's `composed_of: []`, `entrypoint: true`, and version `0.1.0`; make its description current. Update the derived `scenario-routing.md` projection and the two scoped test files together. Preserve existing routes, modules, and composition members, including development-delegation's priority 100 continue behavior. Do not hand-edit deployed router content; existing tooling generates it from the manifest.

Acceptance must establish source/skill identity, optional-absent source support, payload inclusion, exactly one global Photoshop route at priority 80 with terminal outcome, no Photoshop scenario route, and router composition consistent with the manifest and derived projection. Deployment must preserve unrelated/unmanaged target content under the existing managed-payload rules. Native Photoshop/COM operations remain **UNVERIFIED**, disclosed by the skill; native-operation verification is not an activation gate and this phase supplies no permission to perform it.

### Order and validation gates

| Unit | Owner | Completion gate |
|---|---|---|
| 1. Adapt and activate locally | Implementer | Bounded nine-file change, current provenance/MIT preservation, atomic manifest/projection/identity tests; no target writes. |
| 2. Pre-deployment validation | Tester | Validator, three targeted test files, and read-only plan for the actual target pass; review payload, route, composition, and managed-target actions. |
| 3. Pre-apply review | Independent reviewer | Unattended PASS on the bounded change and tester evidence, including PS01/PS02, source pin/license, absent-checkout behavior, actual-target plan, and recovery. PASS is required before apply. |
| 4. Apply | Implementer | Only after PASS, apply the reviewed plan through existing tooling to the explicit target; preserve existing backups/recovery evidence. |
| 5. Verify and accept | Tester, then reviewer | Verify deployed managed payload and generated routing; accept only with successful apply/verification and independent acceptance evidence. |

Tester pre-deployment commands from the repository root:

```powershell
uv run python development/tools/validate_skills.py
uv run python development/tools/run_tests.py development/tools/test_validate_skills.py development/tools/test_deploy_skills.py development/tools/test_control_integration_p3.py
uv run python development/tools/deploy_skills.py --target-root C:/Users/tiany/.codex/skills
```

The third command is read-only; inspect actual-target additions, replacements, and removals before reviewer PASS. The implementer does not run tests. After PASS, the implementer runs:

```powershell
uv run python development/tools/deploy_skills.py --apply --target-root C:/Users/tiany/.codex/skills
```

The tester then runs:

```powershell
uv run python development/tools/deploy_skills.py --verify --target-root C:/Users/tiany/.codex/skills
```

On apply or verification failure, stop acceptance and use the existing deployment backup/rollback mechanism to restore the recorded prior managed state. Report rollback only with actual recovery evidence. Check recovery against the saved pre-apply payload/inventory and preservation of unmanaged content; equality to the new source is a successful-deployment check, not proof of rollback. If recovery cannot be established, report the specific failure and retain evidence rather than claiming restoration or widening scope. Repeat only affected validation/review after a correction.

The supplied independent planning reviewer PASS seals this amendment and authorizes its bounded local implementation. External tester validation and independent pre-apply reviewer PASS are required before target writes; planning PASS alone does not authorize apply or establish phase acceptance.

## Exit, risks, and status

The draft phase exited with the evidence below. Activation acceptance requires the amendment's repository gates, pre-apply reviewer PASS, successful explicit-target apply, and tester verification. Do not mark native capabilities tested in Photoshop. Full upstream runtime migration remains outside this phase.

Known risks are incomplete adaptation evidence, unavailable registered MCP/COM capabilities, preview tools with implicit cloud disclosure, and project handoffs lacking protection or art authority. Their consequences are respectively a source-evidence stop, unavailable operations, withheld preview invocation, and a stop for project decisions. Native operation unavailability does not block static activation. Deployment failure requires evidenced recovery as specified above. Do not solve these by automatic fallback or expanding this skill's responsibilities.

Historical draft status: **PHASE_ACCEPTED** for the original, self-contained local draft and planned manifest entry under the sealed draft plan. Supplied acceptance evidence for the draft tester commands: validator exit 0 (`ok: true`, `errors: []`); targeted tests exit 0, 152 passed; isolated-target read-only deployment plan exit 0 (`ok: true`), no target created, planned Photoshop excluded from payload, routes, and composition. Independent reviewer `01a0fc5e-c9a3-7290-82a9-f08ab932bf06` returned PASS with no findings. This acceptance does not certify live MCP or Photoshop behavior.

Current activation status: **PHASE_ACCEPTED**, implemented, deployed to `C:/Users/tiany/.codex/skills`, and accepted after postapply tester verification and independent reviewer PASS. The supplied reviewed eligible `4039f71d23383d6615c1b2235615e5626302fad2` implementation supersedes the historical missing-source finding. The nine-file change registers its optional source, activates the global Photoshop module and router composition, refreshes the self-contained contract/provenance and routing projection, and updates the two route/identity tests. The user-owned PS03 model correction remains preserved. Full upstream runtime migration remains pending separately; native operations remain **UNVERIFIED**.

Supplied pre-apply acceptance evidence: validator PASS; the three targeted test files passed with 187 tests; actual-target read-only plan returned `ok: true`, no removals, and unmanaged-content preservation. Independent pre-apply reviewer returned PASS after the user-owned PS03 correction. The implementer ran no tests.

Actual apply evidence: the authorized `uv run python development/tools/deploy_skills.py --apply --target-root C:/Users/tiany/.codex/skills` exited 0 with `action: applied`, `ok: true`, and `previous_snapshot: true`. The managed target is `C:/Users/tiany/.codex/skills/global-skill-router`. Comparison with the saved prior inventory shows three added Photoshop files (`MODULE.md`, `references/operation-contract.md`, `references/provenance.md`), replacements of `_platform/routes/index.yaml` and the user-owned `library/development-delegation/agents/implementer.toml`, and no removals. Full apply output is saved at `C:/Users/tiany/AppData/Local/Temp/photoshop-skill-deploy-apply-761a0410344f4d048ce1fc05d58bfc37.log`. The existing manager retained the prior snapshot at `C:/Users/tiany/.codex/.skills-global-skill-router-backup/previous`, including `_platform/deployment-state.json` for the previous four-module inventory.

Supplied postapply acceptance evidence: the tester's explicit-target `--verify` command exited 0 with `ok: true`, `errors: []`. The 63-file payload contains three new Photoshop files with the existing 60 preserved. Routing contains exactly one global Photoshop entry at priority 80/terminal, retains development-delegation at priority 100/continue, and has no Photoshop scenario route. Source, deployed file, and deployment state agree on the preserved user-owned implementer model `gpt-6.1-sol`. Together with the 187-test pre-apply PASS above, independent postapply reviewer `01a0fc5e-c9a3-7290-82a9-f08ab932bf06` returned PASS with no findings, completing activation acceptance. This status update ran no tests and changed no deployment payload; native operations remain **UNVERIFIED**.
