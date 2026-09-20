# Excel Worksheet Events

Entries for worksheet callbacks and event re-entry.

### Worksheet_Change receives the changed Range

Behavior: `Worksheet_Change(ByVal Target As Range)` occurs when cells change through user input or an external link. `Target` can contain more than one cell. The event does not occur for changes made during recalculation; use the `Calculate` event for recalculation-driven behavior.

Evidence: documented_fact

Source: Microsoft - Worksheet.Change event (Excel) - https://learn.microsoft.com/en-us/office/vba/api/excel.worksheet.change (last verified 2026-08-24)

Guidance: Check `Target` shape before reading a scalar value, and distinguish user/external changes from recalculation. Keep the event signature intact.

### Worksheet_SelectionChange receives the selected Range

Behavior: `Worksheet_SelectionChange(ByVal Target As Range)` is a host callback for selection changes; the target can be a range of multiple cells.

Evidence: documented_fact

Source: Microsoft - Worksheet.SelectionChange event (Excel) - https://learn.microsoft.com/en-us/office/vba/api/excel.worksheet.selectionchange (last verified 2026-08-24)

Guidance: Do not use selection events as a substitute for a data-change event. Qualify any reads/writes from `Target` and account for multi-cell selections.

### Worksheet_Activate has no Target parameter

Behavior: `Worksheet_Activate()` runs when a worksheet becomes active. It is different from `Worksheet_SelectionChange`, which receives the selected range.

Evidence: documented_fact

Source: Microsoft - Worksheet.Activate event (Excel) - https://learn.microsoft.com/en-us/office/vba/api/excel.worksheet.activate (last verified 2026-08-24)

Guidance: Preserve the exact host callback name and signature. If the code needs the active sheet, qualify project-owned objects rather than treating activation as data ownership.

### Event handlers can re-enter after writing cells

Behavior: A `Worksheet_Change` handler that writes to cells can trigger another change event. Microsoft demonstrates temporarily setting `Application.EnableEvents = False` around the write. Because `Target` can contain more than one cell, the handler guards against a multi-cell `Target` before treating it as a single value.

```vba
Private Sub Worksheet_Change(ByVal Target As Range)
    Dim priorEvents As Boolean
    On Error GoTo Finally
    If Target.Cells.Count > 1 Then Exit Sub   ' multi-cell guard
    priorEvents = Application.EnableEvents
    Application.EnableEvents = False
    Target.Value = UCase$(Target.Value)
Finally:
    Application.EnableEvents = priorEvents
End Sub
```

Evidence: documented_fact

Source: Microsoft - Worksheet.Change event (Excel) - https://learn.microsoft.com/en-us/office/vba/api/excel.worksheet.change (last verified 2026-08-24)

Guidance: Guard only the smallest write region. Capture the prior `EnableEvents` value before changing it and restore that captured value on success and error rather than unconditionally writing `True`.

### Event callbacks are host-owned code

Behavior: Excel invokes worksheet event procedures by their object-module location, name, and signature; there need not be an explicit VBA call site.

Evidence: documented_fact

Source: Microsoft Worksheet.Change event - https://learn.microsoft.com/en-us/office/vba/api/excel.worksheet.change; Microsoft Worksheet.SelectionChange event - https://learn.microsoft.com/en-us/office/vba/api/excel.worksheet.selectionchange (last verified 2026-08-24)

Guidance: Do not remove an apparently unused event parameter or classify a worksheet event as dead code solely from static call-graph analysis.
