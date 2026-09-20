# Excel Workbook, Worksheet, and Range Model

Entries for Excel object ownership and qualified cell access.

### ThisWorkbook identifies the code's owning workbook

Behavior: `ThisWorkbook` returns the workbook where the VBA code is running. `ActiveWorkbook` returns the workbook currently active in the Excel window. They are usually the same for ordinary workbook code, but differ when code runs from an add-in: `ThisWorkbook` is the add-in and `ActiveWorkbook` is the caller.

Evidence: documented_fact

Source: Microsoft - Application.ThisWorkbook property (Excel) - https://learn.microsoft.com/en-us/office/vba/api/excel.application.thisworkbook; Application.ActiveWorkbook property (Excel) - https://learn.microsoft.com/en-us/office/vba/api/excel.application.activeworkbook (last verified 2026-08-24)

Guidance: Use `ThisWorkbook` for assets owned by the project containing the code. Use an explicitly identified workbook for a caller's data. Never choose between them by convenience.

### Qualify the Workbook -> Worksheet -> Range chain

Behavior: A `Workbook` owns worksheets; a `Worksheet` owns ranges; `Range` represents one or more cells. Unqualified `Range`, `Cells`, `Rows`, `Columns`, `Worksheets`, `Sheets`, and `Names` resolve through active objects and can target a different workbook or sheet after focus changes.

Evidence: documented_fact

Source: Microsoft - Workbook object (Excel) - https://learn.microsoft.com/en-us/office/vba/api/excel.workbook; vba-lint catalog (`ImplicitActiveSheetReference`, `ImplicitActiveWorkbookReference`) in the legacy vba-lint catalog (last verified 2026-08-24)

Guidance: Prefer a fully qualified chain, for example:

```vba
ThisWorkbook.Worksheets("Input").Range("A1").Value = value
```

Treat any unqualified range access as a review finding until its intended owner is established.

### Range.Value is Variant and arrays are two-dimensional

Behavior: `Range.Value` returns or sets a `Variant`. For a multi-cell first area, a get returns a two-dimensional array; assigning a two-dimensional array writes many cells in one operation. The `Range` default member forwards a no-argument call to `Value`.

Evidence: documented_fact

Source: Microsoft - Range.Value property (Excel) - https://learn.microsoft.com/en-us/office/vba/api/excel.range.value (last verified 2026-08-24)

Guidance: Declare the expected data shape. Handle the single-cell versus multi-cell return difference, and avoid assuming a multi-area range can be assigned an array correctly.

### Worksheet codename and displayed name are different references

Behavior: A worksheet's VBA codename is stable within the project and is distinct from its user-visible `Name`. String lookup through `Worksheets("...")` depends on the displayed name and can break after a rename; vba-lint exposes `SheetAccessedUsingString` for this fragility.

Evidence: documented_fact

Source: Microsoft - Workbook object (Excel) - https://learn.microsoft.com/en-us/office/vba/api/excel.workbook; vba-lint catalog (`SheetAccessedUsingString`) in the legacy vba-lint catalog (last verified 2026-08-24)

Guidance: Use a codename where the target sheet is project-owned and fixed. Use an explicit displayed name only when the name is part of the external contract, and then handle rename/configuration failure deliberately.

### Excel and Access host rules are not interchangeable

Behavior: Excel's active workbook/sheet model and Access's form/record/control model have different ownership and event semantics.

Evidence: project_convention

Source: this skill's host split; see `references/vba-office/access/` references and `references/vba-office/shared/sources.md`

Guidance: Classify the host before loading references or interpreting lint results. Never apply Access `Form`/`RecordsetClone` rules to Excel code or Excel active-object rules to Access code.
