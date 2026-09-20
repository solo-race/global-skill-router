# Access Control Value and Focus

Entries for `.Text` / `.Value` semantics and focus-dependent members.

### .Text requires control focus

Behavior: Setting or returning a control's `Text` property requires the control to have the focus; otherwise a runtime error occurs.

Evidence: documented_fact

Source: Microsoft - TextBox.Text property (Access) - https://learn.microsoft.com/en-us/office/vba/api/access.textbox.text (last verified 2026-08-24)

Guidance: Treat any `.Text` reference in code that does not provably own focus as a runtime defect candidate. Move focus with `SetFocus` first, or use `.Value`.

### Text vs Value while the control has focus

Behavior: While the control has focus:

- `Text` = text currently in the control (in-progress edit);
- `Value` = last saved/committed data for the control.

When focus moves away, the control's data is updated and `Value` receives the new value; `Text` becomes unavailable until the control regains focus.

Evidence: documented_fact

Source: Microsoft - TextBox.Text property (Access) - https://learn.microsoft.com/en-us/office/vba/api/access.textbox.text (last verified 2026-08-24)

Guidance: Use `.Text` only when the in-progress edit is genuinely required. When the committed value is intended, use `.Value` (or the control's default property). Never mechanically replace one with the other.

### Focus state is a runtime fact

Behavior: Which control has focus at a given moment depends on user interaction and event sequence; it cannot be determined from source code alone.

Evidence: evidence_based_inference grounded in the documented focus requirement above

Source: see the `.Text` entries; classification per `references/vba-office/shared/sources.md`

Guidance: Classify every focus-dependent member access as runtime-sensitive unless the enclosing event guarantees focus (e.g. control `_Change` fires with focus on that control). Verify at runtime with tooling when available.

### Enabled / Locked are distinct state dimensions

Behavior: `Enabled` gates user interaction and focus; `Locked` gates editing of the bound value. A control can be enabled but locked, or disabled entirely.

Evidence: documented_fact

Source: Microsoft - Access VBA Object Model Reference (Control.Enabled, Control.Locked) - https://learn.microsoft.com/en-us/office/vba/api/overview/access (last verified 2026-08-24)

Guidance: When diagnosing "user cannot edit" reports, check both properties before blaming code paths; do not use them interchangeably in fixes.
