# Access Form Lifecycle

Entries for form open/close event order and event signatures.

### Form open event order

Behavior: When a form is first opened, events occur in this order:

```text
Open -> Load -> Resize -> Activate -> Current
```

Evidence: documented_fact

Source: Microsoft - Form.Open event (Access) - https://learn.microsoft.com/en-us/office/vba/api/access.form.open (last verified 2026-08-24)

Guidance: Do not claim an earlier event can observe work done in a later one (e.g. `Form_Open` cannot rely on `Current` having run). Re-opening via `OpenForm` on an already-open form fires `Activate`, not `Open`.

### Form close event order

Behavior: When a form closes, events occur in this order:

```text
Unload -> Deactivate -> Close
```

Evidence: documented_fact

Source: Microsoft - Form.Open event (Access) - https://learn.microsoft.com/en-us/office/vba/api/access.form.open (last verified 2026-08-24); Microsoft - Form.Unload event (Access) - https://learn.microsoft.com/en-us/office/vba/api/access.form.unload (last verified 2026-08-24)

Guidance: Cancellation of closing belongs in `Unload`; `Close` cannot be canceled.

### Open and Unload are cancellable; Load and Close are not

Behavior: The `Open` event procedure receives a `Cancel` argument that aborts opening the form. `Load` cannot cancel. Symmetrically, `Unload` can cancel closing; `Close` cannot.

Evidence: documented_fact

Source: Microsoft - Form.Open event (Access) - https://learn.microsoft.com/en-us/office/vba/api/access.form.open (last verified 2026-08-24); Microsoft - Form.Unload event (Access) - https://learn.microsoft.com/en-us/office/vba/api/access.form.unload (last verified 2026-08-24)

Guidance: Put "refuse to open / refuse to close" logic in `Form_Open(Cancel As Integer)` / `Form_Unload(Cancel As Integer)`, never in `Load`/`Close`.

### Event procedure signatures are host-bound

Behavior: Event procedures bind by name and signature, e.g.:

```vba
Private Sub Form_Open(Cancel As Integer)
Private Sub Form_Load()
Private Sub Form_Current()
Private Sub Form_BeforeUpdate(Cancel As Integer)
Private Sub Form_AfterUpdate()
Private Sub Form_BeforeInsert(Cancel As Integer)
Private Sub Form_AfterInsert()
```

The host invokes them without any explicit VBA call site.

Evidence: documented_fact

Source: Microsoft Access event reference - `access.form.open`, `access.form.load`, `access.form.current`, `access.form.beforeupdate`, `access.form.afterupdate`, `access.form.beforeinsert`, `access.form.afterinsert` pages under https://learn.microsoft.com/en-us/office/vba/api/ (last verified 2026-08-24)

Guidance: Never delete an unused-looking `Cancel` parameter, rename the procedure, or classify it as dead code from call-graph analysis alone. The `Form_<Event>` naming shown above is a legacy project convention for event procedures, not a host requirement.

### Related-event groups must be inspected together

Behavior: One interaction typically spans several events; changing state in one triggers others.

Typical groups:

- open path: `Form_Open`, `Form_Load`, `Form_Current`;
- editing path: control `BeforeUpdate`/`AfterUpdate`, `Form_BeforeUpdate`, `Form_AfterUpdate`;
- insert path: `Form_BeforeInsert`, `Form_AfterInsert`;
- focus path: `Enter`, `Exit`, `GotFocus`, `LostFocus`.

Evidence: project_convention

Source: legacy VBA Skill event-group convention (migration reviewed 2026-09-20)

Guidance: When investigating an event-driven defect, inspect every event in the relevant group before proposing a fix. The grouping itself follows the documented open/close orders above.
