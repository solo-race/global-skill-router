# Access SaveAsText Source Extraction

Use this reference when an Access review receives a `.txt` created by
`Application.SaveAsText`. The `.txt` is a mixed object dump, not a native VBA
export and not a vba-lint workspace source file.

## Decision contract

1. Classify `.bas`, `.cls`, `.frm`, and `.dcm` as native VBA exports. Classify
   an Access SaveAsText `.txt` as a mixed object dump regardless of its name.
2. For a mixed dump, locate the earliest supported code boundary: an exact
   `CodeBehindForm` line or one `Attribute VB_Name = "..."` module attribute.
   `CodeBehindForm` takes precedence when its code tail also contains module
   attributes. After a valid VBA opening starts the extracted code tail,
   boundary-like text inside that VBA is never reinterpreted as object metadata.
3. After optional blank/comment lines, the extracted tail must start with a
   recognizable VBA module opening such as a module attribute, `Option`
   statement, declaration, or procedure. Only that extracted text may be
   passed as `code` to `vba_parse` or `vba_inspect`.
4. If no code boundary and no VBA-like text exists, report that the mixed dump
   has no VBA section and do not call parser/lint.
5. If a boundary is malformed before extraction, missing around VBA-like text,
   or its tail does not start with recognizable VBA, report
   `source extraction unresolved`. Stop the parser/lint path; a parser error
   would describe the serialization dump, not the VBA module.

The bundled helper `scripts/vba-office/extract_access_saveastext.py` implements this
gate. Its `ready`, `no_vba`, and `unresolved` states are intentionally
distinct. If workspace analysis is required, write a `ready` result to a
controlled temporary `.bas`, `.cls`, or `.frm` file first. Do not rename or
copy the original `.txt` into a vba-lint workspace.

Evidence: `project_convention`

Source: migrated SaveAsText extraction contract (migration reviewed 2026-09-20).

Regression cases are synthetic strings and temporary files in
`scripts/vba-office/test_extract_access_saveastext.py`; no Office fixture or
application business data is required.
