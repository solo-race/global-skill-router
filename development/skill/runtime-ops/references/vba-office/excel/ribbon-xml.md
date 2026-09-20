# Excel Custom Ribbon XML

Entries for workbook custom UI XML and the vba-doctor bridge.

### Custom Ribbon XML is a package part, not VBA source

Behavior: A macro-enabled Office workbook can contain a Custom UI XML part. Office 2007+ custom UI uses the `customUI`/`customUI14` namespace appropriate to the target Office version; the XML is separate from `.bas`, `.cls`, `.frm`, and document-module source.

Evidence: documented_fact

Source: Microsoft - [MS-CUSTOMUI] Office Custom UI XML specification - https://learn.microsoft.com/en-us/openspecs/office_standards/ms-customui/ (last verified 2026-08-24)

Guidance: Review Ribbon XML separately from VBA source. Preserve the namespace and callback names when editing; a VBA compile result does not prove that custom UI XML is valid or loaded.

### Ribbon callback signatures must match the XML contract

Behavior: Ribbon callback signatures depend on the specific XML attribute,
control type, and target Custom UI schema. A single generic signature is not
valid for every callback; compile success alone does not establish that Office
can bind a named callback.

Evidence: documented_fact

Source: Microsoft - [MS-CUSTOMUI] Office Custom UI XML specification - https://learn.microsoft.com/en-us/openspecs/office_standards/ms-customui/ (legacy source last verified 2026-08-24)

Guidance: Look up each callback's member-specific signature in the applicable
schema before changing its VBA handler. Preserve argument and return contracts,
then verify Ribbon loading and callback behavior independently. Use
`adapters/vba-office.md` for XML read/write, workbook ownership, and recovery
operations; this reference does not duplicate the provider ABI.

### Ribbon callbacks still require VBA runtime verification

Behavior: XML can name VBA callbacks, but XML presence alone does not prove that the callback exists, has the required signature, or runs in the intended workbook.

Evidence: evidence_based_inference

Source: Microsoft - [MS-CUSTOMUI] Office Custom UI XML specification - https://learn.microsoft.com/en-us/openspecs/office_standards/ms-customui/; Excel Workbook object reference - https://learn.microsoft.com/en-us/office/vba/api/excel.workbook (last verified 2026-08-24)

Guidance: Verify the XML artifact and the callback separately: read/inspect the document module or standard module, then run a targeted macro where the callback can be exercised. Report XML verification and VBA runtime verification as separate evidence.
