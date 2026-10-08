# Operation contract

This contract governs selected local Adobe Photoshop documents through registered MCP. It supplies operating decisions without an upstream checkout, migration plan, or assumed implementation. Project art decisions and acceptance belong to the art skill or designated reviewers.

Native Photoshop/COM operations remain **UNVERIFIED**. Static activation and deployment evidence do not verify native operations; establish the following operation-specific prerequisites before any invocation.

## Project handoff

Require the following before operations:

- `project_id` and the project's registered output rules, including permitted destinations, formats, and overwrite restrictions.
- Selected document and layer identifiers, source files, protected layers, and allowed operations.
- Canvas coordinate conventions, intended placement, and H160-palette references when applicable.
- Output paths and formats, required approvals, and preview policy.

Bind every operation to those document/layer identifiers. Enforce the registered project output rules for working copies, backups, exports, and reports as well as production outputs. Do not expand permitted output paths or overwrite source files (PS01). Missing or conflicting rules stop affected operations for a project decision; task wording alone does not expand the registered rules.

Preserve the project's responsibility for composition, palette, placement, and other art decisions. Do not automatically fit, center, scale, quantize, feather, or rasterize without approval. Return missing art or placement decisions to the project owner instead of inventing them.

## Availability and tool contracts

Establish the actual registered MCP tools and their registration policy before use. Read their available contracts: supported operations, input signatures, result/failure semantics, capabilities, and version evidence needed by the requested operation. Bind the operation to observed tool names and signatures; never invent endpoints or claim unobserved features.

Establish selected document identity and local Photoshop/COM availability using only supported checks. Before an availability invocation, disclose whether it may launch Photoshop and obtain authorization for that launch when required. An availability check is not itself launch authorization. Check capture and transmission side effects before invocation too.

Missing registration, a required capability or version evidence, or COM availability means **unavailable** for that operation. State the missing prerequisite and stop the affected work. Do not install software, register tools, change configuration, or substitute another execution route.

## Authority and execution

Allowed operations are the intersection of task authorization, registered MCP policy, actual capabilities, and project art constraints. An available tool grants no extra authority. Execute within that intersection using the registered signatures and approved document/layer targets, destinations, and formats.

Raw scripts, JSX, SendKeys, Photoshop Actions, and automatic fallback are excluded. Do not use them to replace missing MCP operations. Installation, registration, and configuration changes are also outside this contract.

## Protection, backup, and rollback

High-impact operations, including destructive layer changes or document transformations, require explicit authorization covering target, operation, output, and recovery. Identify protected layers from the handoff and preserve them. A general document-edit request does not authorize their destruction.

Before destructive operations, use an authorized working copy or a verified backup/rollback path. Confirm that it covers the affected document/layers and any file writes, and that recovery is available through supported capabilities at authorized destinations. If those protections cannot be established, stop before mutation.

Photoshop history does not undo file writes. Do not justify destruction using an unverified history checkpoint, or describe history as recovery for saved or exported files. Preserve source files even when a working copy or backup exists.

After a failure, report what actually changed and what remains uncertain. Restore only through an authorized, verified recovery path covering the affected state; do not perform an automatic or speculative restore. Authorization for editing is not authorization for unrelated recovery actions or output-rule changes.

## Preview and disclosure

Default preview handling is local-only. Inspect the actual tool contract for capture and transmission behavior before invocation. Capability discovery does not authorize a call that implicitly captures or transmits imagery.

Sending a preview to any cloud receiver requires separate verified consent identifying the receiver and disclosure scope. This applies to base64 payloads and tool image blocks as well as uploaded files. If consent or the receiver cannot be established, withhold the transmitting invocation. An approved local preview does not grant cloud disclosure authority.

Window capture, layer preview, and production output are distinct artifacts with distinct authority. Do not substitute a window capture for a layer preview, or a preview for production output. Do not capture the UI without approval. Follow the project preview policy and registered output rules for any saved preview.

## Results and reporting

By default, return in conversation the actual changed layers, operations performed, outputs produced, and unverified items (PS02). Identify affected document/layer IDs and output destinations from observed results; distinguish performed work from requested work. If nothing changed or no output was produced, say so. Do not report a higher verification level than the evidence supports.

Write a report only when the user or project explicitly asks for one and its output path is authorized under the project's registered output rules. Do not create a report by default or choose an additional output directory. Report imagery remains subject to the preview/disclosure gates.

Project art QC and owner acceptance remain with the art skill or designated reviewers. Successful operations or file writes do not establish art approval.

## Stop conditions

Stop affected work when availability or tool support is missing; project identity, document/layer targets, output rules, or art decisions are unresolved; an operation exceeds the permission intersection; required high-impact authorization, protected-layer preservation, or verified recovery is absent; or preview capture/disclosure lacks approval. Return the specific missing prerequisite and any actual changes in conversation. Do not widen authority or claim completion to bypass a stop.
