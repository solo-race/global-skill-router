# Excel Add-ins and Document Modules

Entries for `.xlam` file ownership and safe module transfer.

### A loaded xlam can lock file-level overwrite

Behavior: When Excel has an `.xlam` loaded and enabled as an add-in, attempting to overwrite that same file from an external process can fail with a file-lock error.

Evidence: project_convention

Source: maintainer-documented observation in the legacy vba-doctor knowledge notes section 6 (last verified 2026-02-24; not independently reproduced during this migration)

Guidance: Before file-level import/overwrite of an `.xlam`, confirm Excel is not holding the file open. Prefer the vba-doctor code-module API for an in-place edit when its contract supports the target.

### Document modules are not ordinary importable modules

Behavior: `ThisWorkbook` and worksheet document modules are type 100 (`Document`) components. Passing their exported `.dcm` contents to generic `VBComponents.AddFromString` or `Import` can make Excel hang; vba-doctor's `set_vba_code` writes directly to the document module instead.

Evidence: project_convention

Source: maintainer-documented observation in the legacy vba-doctor knowledge notes section 6; module types in the legacy vba-doctor module specification (last verified 2026-02-24; not independently reproduced during this migration)

Guidance: Never import a document-module export as if it were a standard `.bas` module. Identify component type first; use direct `set_vba_code` for document-module edits and keep a recoverable backup.

### .xlam behavior requires host-specific verification

Behavior: An `.xlam` change can affect add-in load state, workbook callbacks, and document-module callbacks. A successful source write does not prove Excel can load the add-in or execute its callback.

Evidence: evidence_based_inference

Source: Microsoft - Workbook object (Excel) - https://learn.microsoft.com/en-us/office/vba/api/excel.workbook; vba-doctor project - the legacy vba-doctor knowledge notes section 6 (last verified 2026-08-24)

Guidance: After an add-in change, reread the changed component, invoke the
target-checked Excel compile command, reopen/load the add-in in a controlled
fixture where possible, and run the targeted macro. The registered compile
operation reports `unverified` after dispatch, so report the compile-command
result separately from any independently observed compile or runtime evidence.
