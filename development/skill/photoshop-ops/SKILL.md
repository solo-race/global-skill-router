---
name: photoshop-ops
description: Govern authorized document operations through registered MCP; Use when operating selected local Adobe Photoshop documents.
---

# Photoshop operations

Operate the selected documents within the project's art decisions and output rules. This self-contained module owns a terminal global route for those operations. Native Photoshop/COM operations remain **UNVERIFIED**; routing eligibility does not establish availability or permission. It does not handle imagegen, repository implementation, or MCP security review.

Environment: Windows, local Adobe Photoshop with COM available, and registered MCP tools whose actual contracts support the requested operation. No bundled runtime or assumed tool names.

All relative paths resolve against this skill's own root. Before any operation, read [references/operation-contract.md](references/operation-contract.md); it owns the availability, authority, output, preview, protection, and recovery gates. Read [references/provenance.md](references/provenance.md) when assessing origin, adaptation eligibility, or licensing.

1. Obtain the project handoff, including `project_id`, selected document/layer identifiers, permitted operations, art constraints, registered output rules, approvals, and preview policy.
2. Establish actual registration, capabilities/version, document identity, and COM availability. Disclose any possible Photoshop launch before the check; obtain launch authorization when needed. Missing support means unavailable for that operation.
3. Intersect task authorization, registered MCP policy, actual capabilities, and project art constraints. Preserve protected layers and enforce registered output rules: never expand permitted output paths or overwrite source files. High-impact operations need explicit authorization and an authorized working copy or verified recovery path.
4. Invoke only supported, authorized operations. Keep previews local unless separately verified receiver-specific consent permits disclosure. Stop at missing support, authority, protection, recovery, or project decisions; do not use raw scripts, JSX, SendKeys, Actions, automatic fallback, installation, registration, or configuration changes.
5. Return actual changed layers, operations performed, outputs produced, and unverified items in conversation. Write reports only on explicit user/project request at an authorized output path. Project art QC and owner acceptance remain with the art skill or designated reviewers.
