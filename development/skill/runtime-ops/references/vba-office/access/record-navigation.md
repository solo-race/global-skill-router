# Access Record Navigation

Entries for locating and synchronizing the form's current record.

### RecordsetClone is a navigable copy of the form's record source

Behavior: `Form.RecordsetClone` returns a DAO `Recordset` that is a copy of the recordset defined by the form's `RecordSource`. It exists so the form's records can be searched or operated on independently of what the form displays.

Evidence: documented_fact

Source: Microsoft - Form.RecordsetClone property (Access) - https://learn.microsoft.com/en-us/office/vba/api/access.form.recordsetclone (last verified 2026-08-24)

Guidance: Use it for `FindFirst`/`Move*` operations on the form's data without disturbing the form. Do not assume an independently opened DAO `Recordset` (`CurrentDb.OpenRecordset`) behaves identically for form navigation.

### Find / Move require explicit Bookmark synchronization

Behavior: After a `Find` or `Move` method makes another record current in the clone, the form's current record changes only if you assign the clone's `Bookmark` to the form: `Me.Bookmark = rst.Bookmark`.

Evidence: documented_fact

Source: Microsoft - Form.RecordsetClone property (Access) - https://learn.microsoft.com/en-us/office/vba/api/access.form.recordsetclone (last verified 2026-08-24)

Guidance: Any `RecordsetClone` search that intends to move the form must end in the Bookmark assignment; otherwise the user sees no change.

### Always check NoMatch after FindFirst

Behavior: `FindFirst` leaves the clone at the first matching record, or — when nothing matches — sets `NoMatch = True`. Microsoft's own pattern checks `NoMatch` before using the result.

```vba
Set rst = Me.RecordsetClone
rst.FindFirst "SupplierID = " & Str(Me!SupplierID)
If rst.NoMatch Then
    MsgBox "Record not found"
Else
    Me.Bookmark = rst.Bookmark
End If
```

Evidence: documented_fact

Source: Microsoft - Form.RecordsetClone property (Access) - https://learn.microsoft.com/en-us/office/vba/api/access.form.recordsetclone (last verified 2026-08-24)

Guidance: A missing `NoMatch` check after `FindFirst` is a statically detectable defect candidate; flag it during review.

### Record ID is not record position

Behavior: A primary key / business key value identifies a record logically; ordinal position (e.g. "record 5") depends on current sort/filter/order and has no stable meaning.

Evidence: evidence_based_inference grounded in the documented navigation model above

Source: see the `RecordsetClone` entry; classification per `references/vba-office/shared/sources.md`

Guidance: Locate records by key via `FindFirst`, never by `GoToRecord` offsets computed from IDs. Use `DoCmd.GoToRecord` only for genuinely positional navigation (next/previous).

### Filter changes flow into the clone

Behavior: If a filter is applied to the form, the form's `Recordset` reflects the filtering; searches against the clone operate on the filtered set.

Evidence: documented_fact

Source: Microsoft - Form.RecordsetClone property (Access) - https://learn.microsoft.com/en-us/office/vba/api/access.form.recordsetclone (last verified 2026-08-24)

Guidance: Before diagnosing "record not found" reports, inspect `Filter`/`FilterOn`; a search can be correct yet fail against a narrowed recordset.
