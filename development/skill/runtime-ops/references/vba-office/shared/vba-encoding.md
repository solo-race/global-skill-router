# VBA Source File Encoding

Knowledge entries for VBA export/import file encoding under both hosts.
The CP932 rules below are migrated Japanese-Windows project conventions;
confirm the actual export/worktree encoding before applying them elsewhere.

### VBE exports are CP932 on Japanese Windows

Behavior: Files exported by the Visual Basic Editor on Japanese Windows are encoded CP932 (Shift-JIS), regardless of extension: `.bas`, `.cls`, `.frm`, `.dcm`.

Evidence: project_convention

Source: maintainer-documented observation in
the legacy vba-doctor knowledge notes §5 and §7 (not reproduced in this
repository)

Guidance: When reading or writing exported VBA source with external tooling, use CP932 explicitly. Never assume UTF-8.

### git working-tree-encoding converts checked-out files back to UTF-8

Behavior: When `.gitattributes` sets `working-tree-encoding=UTF-8`, files are stored as UTF-8 in git but the working tree copy is UTF-8 too; VBE still expects CP932 on import.

| Extension | VBE export | Working tree with `working-tree-encoding=UTF-8` |
|---|---|---|
| `.bas` | CP932 | UTF-8 |
| `.cls` | CP932 | UTF-8 |
| `.dcm` | CP932 | UTF-8 |
| `.frm` | CP932 | UTF-8 |

Evidence: project_convention

Source: maintainer-documented observation in
the legacy vba-doctor knowledge notes §7 (not reproduced in this
repository)

Guidance: Convert a UTF-8 working-tree copy to CP932 before handing it to the
VBE (import, `AddFromString` alternatives). Read with `encoding="utf-8-sig"`
so a leading BOM is stripped automatically. In Python:

```python
with open("src/Module1.bas", encoding="utf-8-sig") as f:
    content = f.read()
with open("src/Module1.bas", "w", encoding="cp932") as f:
    f.write(content)
```

In VSCode: status-bar encoding → "Save with Encoding" → `Japanese (Shift JIS)`.

### Working-tree UTF-8 copies may carry a leading BOM

Behavior: A UTF-8 working-tree copy of an exported module may begin with a
leading U+FEFF byte order mark. The BOM cannot be encoded back to CP932, so
byte-level CP932 round-trips fail or leave a stray character at the top of the
module. VBE CP932 exports contain no BOM.

Evidence: project_convention

Source: legacy maintainer-recorded convention (not reproduced in
this repository; not covered by the legacy vba-doctor knowledge notes)

Guidance: Read working-tree copies with `encoding="utf-8-sig"` (or strip a
leading U+FEFF manually) before any byte-level operation, especially before
re-encoding to CP932.

### Exported sources may mix CRLF and LF

Behavior: Line endings in exported `.bas`/`.cls`/`.frm` files can be mixed (CRLF and LF), e.g. after passing through git `autocrlf`.

Evidence: project_convention

Source: maintainer-documented observation in
the legacy vba-doctor knowledge notes §5 (not reproduced in this
repository)

Guidance: Do text replacement line-aware or normalize line endings first; a naive multi-line string replace can silently fail to match.

### Python tooling reads/writes bytes as cp932

Behavior: The validated IO pattern keeps scripts UTF-8 but decodes/encodes VBA files as cp932 at the file boundary.

Evidence: project_convention

Source: maintainer-documented observation in
the legacy vba-doctor knowledge notes §5 (not reproduced in this
repository)

```python
with open(fpath, 'rb') as f:
    raw = f.read()
text = raw.decode('cp932')
# ... edit ...
with open(fpath, 'wb') as f:
    f.write(text.encode('cp932'))
```

Guidance: Follow this pattern in any script that post-processes exported VBA source.
