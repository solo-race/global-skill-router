# Photoshop operation contract

## Scope and authority

For direct editing, use the user's selected document, requested transformation, and output destination.
Do not require a project ID, fixed palette, or formal handoff for an ordinary edit. Choose routine
layout and rendering details within that request. Ask when the target, required appearance, or
output remains materially ambiguous.

For managed-project work, also follow its project ID, registered outputs, art direction (including
H160 when applicable), protected layers, and review requirements. Tool capability is not permission
to expand either scope. Do not overwrite source files or alter protected layers without authorization.
All operations must also comply with registered MCP policy. Project output restrictions
cover working copies, backups, exports, previews, reports, and final deliverables.

## Tool availability

Use registered MCP tools and their current schemas; do not invent endpoint names or assume that
registration proves native Photoshop/COM operations work. Ordinary launch needed for a requested
operation does not need a second approval, unless the user restricted it. Disclose unexpected
side effects before proceeding. Missing capabilities are a blocker, not permission to install or
register tools, run raw scripts/JSX, use SendKeys, or invoke arbitrary Actions as a fallback.

## Recovery and verification

Before destructive edits (flattening, rasterization, deletion, or irreversible transformations),
secure an authorized working copy or verified backup and identify the recovery path. Preserve
protected layers. Photoshop history does not undo file writes; do not claim rollback from history
alone or improvise restoration over the source.

Check the edited document and requested exports separately. Report observed changes and output
paths; distinguish successful tool calls from verified appearance. Native execution and art/QC
approval remain unverified unless actually checked by the relevant capability or reviewer.

## Preview and reporting

Keep previews local unless transmission to the intended receiver is authorized. Tool image blocks
and cloud previews can transmit document content too; inspect capture behavior before invoking it.
Capture only the authorized document/UI scope, not unrelated desktop content.

Report results in conversation. Write sidecar reports only when requested and within authorized
outputs. Stop for unavailable capability, insufficient recovery, protected-content changes outside
scope, or unauthorized output/transmission. Otherwise continue without repetitive confirmation.
