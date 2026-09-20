# Excel UserForm Model

Entries for MSForms UserForm lifecycle and dialog state.

### UserForm lifecycle events are host callbacks

Behavior: A UserForm exposes lifecycle events including `Initialize`, `Activate`, and `Terminate`. `Initialize` occurs when the instance is loaded/initialized, `Activate` when it becomes active, and `Terminate` when the instance is released. The event procedures are bound by object-module name and signature.

Evidence: documented_fact

Source: Microsoft - VBA UserForm / UserForm object reference - https://learn.microsoft.com/en-us/office/vba/language/reference/user-interface-help/userform-object (last verified 2026-08-24)

Guidance: Inspect lifecycle handlers together when diagnosing startup, repeated display, or cleanup behavior. Do not infer invocation only from explicit calls.

### UserForm_QueryClose intercepts close requests

Behavior: `Private Sub UserForm_QueryClose(Cancel As Integer, CloseMode As Integer)` runs when the form is about to close. `CloseMode` is `vbFormControlMenu` (0) when the user chose the Close/X button and `vbFormCode` (1) when the close came from an `Unload` statement. Setting `Cancel` to a nonzero value stops the close.

Evidence: documented_fact

Source: Microsoft - QueryClose event (VBA Forms/UserForm object) - https://learn.microsoft.com/en-us/office/vba/language/reference/user-interface-help/queryclose-event (last verified 2026-08-24)

Guidance: Read `CloseMode` before deciding cleanup so an X-button close and a programmatic unload are distinguishable. Use `Cancel` to defer or veto a close deliberately, not as ordinary flow control.

### Hide preserves module state; Unload destroys the instance

Behavior: `Hide` removes the form from view without raising `Terminate`; the instance survives with its module-level state, so a subsequent `Show` resumes that state. `Unload` destroys the instance and raises `Terminate`; module state does not survive it.

Evidence: documented_fact

Source: Microsoft - Hide method (VBA UserForms) remarks - https://learn.microsoft.com/en-us/office/vba/language/reference/user-interface-help/hide-method (last verified 2026-08-24)

Guidance: Choose `Hide` when dialog state must survive redisplay and `Unload` when the instance must be released. Do not read form state after `Unload` expecting persisted values.

### MSForms control value members are control-specific

Behavior: Excel UserForms use MSForms controls, not Access controls. A control may expose `.Text`, `.Value`, or other value members with semantics defined by that control; Access's focus rule must not be copied into a UserForm without checking the MSForms reference.

Evidence: documented_fact

Source: Microsoft - Microsoft Forms controls reference - https://learn.microsoft.com/en-us/office/vba/language/reference/user-interface-help/controls-objects-properties-methods (last verified 2026-08-24)

Guidance: Identify the concrete MSForms control and read its member contract before changing `.Text`/`.Value`. Do not apply `references/vba-office/access/controls.md` to UserForms.

### Modal and modeless forms have different interaction contracts

Behavior: A UserForm shown modally blocks interaction with the calling Excel UI until it is hidden or unloaded. A modeless UserForm permits interaction with Excel while the form remains displayed; code must therefore tolerate changes in active workbook, sheet, and selection during the form's lifetime.

Evidence: documented_fact

Source: Microsoft - Show method (VBA UserForms) - https://learn.microsoft.com/en-us/office/vba/language/reference/user-interface-help/show-method (last verified 2026-08-24)

Guidance: For modeless forms, qualify all workbook/sheet targets and avoid storing active-object assumptions across callbacks. Test both the form lifecycle and the caller's continuation path.

### InputBox cancellation is shared VBA behavior

Behavior: InputBox cancel detection — the `StrPtr` distinction and the declaration/assignment separation — is defined once in `references/vba-office/shared/error-handling.md` and applies identically under Excel VBA.

Evidence: project_convention

Source: maintainer-documented observation in the legacy vba-doctor knowledge notes section 1 (last verified 2026-02-24; not independently reproduced during this migration)

Guidance: Load the shared error-handling reference for cancellation code; do not duplicate or alter the rule in the Excel file.
