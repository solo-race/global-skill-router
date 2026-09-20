# Error Handling and Cancellation

Knowledge entries for VBA error-handler structure and user-cancellation
propagation. Host-agnostic; applies under Access and Excel.

### Standard Function error handler

Behavior: `On Error GoTo Catch` with an explicit success exit keeps the return
value assignment inside the protected region and a default value in the handler.

```vba
Public Function SomeFunction() As String
    On Error GoTo Catch
    ' ... work ...
    SomeFunction = "ok"
    Exit Function
Catch:
    MsgBox Err.Description, vbExclamation
    SomeFunction = ""   ' error-time default
End Function
```

Evidence: documented_fact

Source: Microsoft - VBA Language Reference - On Error statement; vba-doctor project - the legacy vba-doctor knowledge notes section 3 (last verified 2026-02-24)

Guidance: Use this shape for new Functions. Do not leave the happy path falling into the Catch label.

### Finally-style cleanup with GoTo Finally

Behavior: When state restored after the body (e.g. `Application.DisplayAlerts`) must be restored on both paths, route both the success and error paths through a `Finally:` label.

```vba
Public Sub SomeSub()
    Dim previousDisplayAlerts As Boolean
    previousDisplayAlerts = Application.DisplayAlerts
    On Error GoTo Catch
    Application.DisplayAlerts = False
    ' ... work ...
    GoTo Finally
Catch:
    MsgBox Err.Description, vbExclamation
Finally:
    Application.DisplayAlerts = previousDisplayAlerts
End Sub
```

Evidence: project_convention

Source: maintainer-documented observation in the legacy vba-doctor knowledge notes section 3 (last verified 2026-02-24; not independently reproduced during this migration)

Guidance: Any temporary global-state change (`DisplayAlerts`, `EnableEvents`, `ScreenUpdating`) gets this pattern. Capture the flag's value before changing it and restore that captured value rather than assuming its default. Never restore such flags only on the success path.

### InputBox cancel detection requires StrPtr

Behavior: `InputBox` returns `""` for both Cancel and empty-input OK. `StrPtr(ans)` distinguishes them: non-zero for any OK (including empty string), zero for Cancel.

| Action | `StrPtr(ans)` |
|---|---|
| text + OK | `<> 0` |
| empty + OK | `<> 0` |
| Cancel | `0` |

Evidence: project_convention

Source: maintainer-documented observation in the legacy vba-doctor knowledge notes section 1 (last verified 2026-02-24; not independently reproduced during this migration)

Guidance: Declare the result and assign InputBox on **separate lines**:

```vba
' Required: declaration and assignment split
Dim ans As String
ans = InputBox("prompt", "title", "default")
If StrPtr(ans) = 0 Then
    Exit Sub   ' cancelled
End If
```

A combined `Dim ans As String: ans = InputBox(...)` can break StrPtr detection. Treat that one-line form as a defect.

### Cancel must propagate as a Boolean function result

Behavior: Exiting a Sub early does not stop its caller. A cancelled dialog step must convert the callee to `Function As Boolean` and gate the caller on the result.

```vba
Public Sub MainProcess()
    If Not ShowDialog() Then Exit Sub
    Call DoWork()
End Sub

Public Function ShowDialog() As Boolean
    On Error GoTo Catch
    Dim ans As String
    ans = InputBox("...")
    If StrPtr(ans) = 0 Then
        ShowDialog = False
        Exit Function
    End If
    ' ... work ...
    ShowDialog = True
    Exit Function
Catch:
    MsgBox Err.Description, vbExclamation
    ShowDialog = False
End Function
```

Evidence: project_convention

Source: maintainer-documented observation in the legacy vba-doctor knowledge notes section 2 (last verified 2026-02-24; not independently reproduced during this migration)

Guidance: During review, flag any `Exit Sub` cancellation whose caller continues unconditionally afterwards.
