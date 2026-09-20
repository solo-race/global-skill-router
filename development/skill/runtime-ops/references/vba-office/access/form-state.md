# Access Form State

Entries for record-state properties and the Requery / Refresh / Repaint distinction.

### State properties to inspect before navigation or requery changes

Behavior: These form properties define the current data context:

- `Dirty` — unsaved edits exist on the current record;
- `NewRecord` — the current record is a new, not-yet-saved row;
- `AllowAdditions`, `DataEntry` — whether new records may be entered and whether the form shows only new records;
- `Filter`, `FilterOn` — active filter expression and whether it applies;
- `RecordSource`, `RecordsetType` — what data the form shows and how it can be updated.

Evidence: documented_fact (property definitions)

Source: Microsoft - Access VBA Object Model Reference (Form properties) - https://learn.microsoft.com/en-us/office/vba/api/overview/access (last verified 2026-08-24)

Guidance: Inspect these at runtime before changing navigation, filtering, or requery logic; each is a runtime fact, not a source-code fact. When runtime tooling is available (vba-doctor `run_macro` harness), read them rather than guessing.

### Requery, Refresh, Repaint are distinct operations

Behavior:

- `Requery` reruns the form's underlying query: it shows records that are new to or deleted from the record source and updates display per any `Filter` change.
- `Refresh` shows only changes to the *current set* of records; it does not reflect new or deleted records.
- `Repaint` only repaints the form and its controls on screen; no data operation occurs.

Evidence: documented_fact

Source: Microsoft - Form.Requery method (Access) - https://learn.microsoft.com/en-us/office/vba/api/access.form.requery (last verified 2026-08-24)

Guidance: Never substitute one for another. "My update doesn't show" after `Refresh` where rows were added/deleted is a documented cause, not a mystery.

### Requery can reposition and retrigger events

Behavior: `Requery` re-runs the form's data source; Microsoft documents that it updates which records are shown. Whether the current record survives identically after Requery is not fully specified for every state combination.

Evidence: documented_fact

Source: Microsoft - Form.Requery method (Access) - https://learn.microsoft.com/en-us/office/vba/api/access.form.requery (last verified 2026-08-24)

Guidance: If `Requery` is invoked from an event that Requery itself can trigger again (e.g. `Form_Current` calling `Requery`), evaluate re-entry explicitly before shipping the fix; the re-triggering consequence is an inference from these documented semantics, not a separately documented guarantee. Where documentation is insufficient, reproduce in a controlled test (an identified synthetic/dev `.accdb` fixture) and classify as `verified_empirical_behavior`.

### Subform focus limits Requery scope

Behavior: If a subform control has focus when the parameterless form-level `Requery` path runs, only the subform's record source is requeried, not the parent form's. More generally (Form.Requery page Note): with the expression omitted, if the focused control has a record source or row source it is requeried; otherwise its data is merely refreshed.

Evidence: documented_fact

Source: Microsoft - Form.Requery method (Access) - https://learn.microsoft.com/en-us/office/vba/api/access.form.requery (last verified 2026-08-24)

Guidance: Qualify the target explicitly (`Me.SubformControl.Form.Requery` vs `Me.Requery`); do not rely on implicit focus-dependent targets.
