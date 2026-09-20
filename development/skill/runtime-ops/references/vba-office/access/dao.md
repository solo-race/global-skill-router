# Access DAO Data Access

Entries for DAO `Database` and `Recordset` lifecycles, navigation, and updates.

### Database and Recordset are separate objects

Behavior: A DAO `Database` represents an open database. Its `OpenRecordset`
method executes a select query and creates a `Recordset` object representing
rows and fields. `CurrentDb` is the normal Access expression for obtaining the
current database object; `Me.Recordset` and `Me.RecordsetClone` are form-owned
DAO `Recordset` objects.

Evidence: documented_fact

Source: Microsoft - Database object (DAO) - https://learn.microsoft.com/en-us/office/client-developer/access/desktop-database-reference/database-object-dao (last verified 2026-08-24); Microsoft - Recordset object (DAO) - https://learn.microsoft.com/en-us/office/client-developer/access/desktop-database-reference/recordset-object-dao (last verified 2026-08-24)

Guidance: Keep the data-access path (`CurrentDb.OpenRecordset`) distinct from
the form-bound objects. For locating records and synchronizing the form's
current row, see `references/vba-office/access/record-navigation.md`.

### Choose and record the Recordset type

Behavior: DAO supports table-, dynaset-, snapshot-, forward-only-, and
(ODBCDirect) dynamic-type recordsets. In an Access workspace, the chosen type
affects whether records are updatable and which navigation methods are
available. `Type` identifies the created type and `Updatable` identifies
whether changes are permitted.

Documented caveats: ODBCDirect workspaces are not supported in Access 2013 and
later (ADO is the replacement), and the dynamic type (`dbOpenDynamic`) is not
available in ACE DAO (.accdb) projects.

Evidence: documented_fact

Source: Microsoft - Recordset object (DAO) - https://learn.microsoft.com/en-us/office/client-developer/access/desktop-database-reference/recordset-object-dao (last verified 2026-08-24)

Guidance: State the intended type explicitly when correctness depends on updateability or navigation. Do not assume a query result is editable.

### Empty Recordsets require BOF/EOF handling

Behavior: A newly created recordset with no rows has `RecordCount = 0` and both `BOF` and `EOF` set to `True`. `MoveFirst`/`MoveNext`/`MoveLast` navigation must be guarded by the recordset state.

Evidence: documented_fact

Source: Microsoft - Recordset object (DAO) - https://learn.microsoft.com/en-us/office/client-developer/access/desktop-database-reference/recordset-object-dao (last verified 2026-08-24)

### FindFirst failure is reported through NoMatch

Behavior: Dynaset- and snapshot-type recordsets support the `Find` methods
(`FindFirst`, `FindLast`, `FindNext`, `FindPrevious`). If no record matches,
DAO sets `NoMatch = True`; a matching record must be checked before reading
its fields or bookmark. Table-type recordsets instead use `Seek`.

Evidence: documented_fact

Source: Microsoft - Recordset object (DAO) - https://learn.microsoft.com/en-us/office/client-developer/access/desktop-database-reference/recordset-object-dao (last verified 2026-08-24)

Guidance: Branch on `NoMatch` immediately after any `Find` method; never use
the current row as if a match were guaranteed. For the form-synchronization
pattern built on these methods, see `references/vba-office/access/record-navigation.md`.

### Updates use the Edit/AddNew/Update state machine

Behavior: To change an existing row, call `Edit`, assign fields, then call `Update`. To insert a row, call `AddNew`, assign fields, then call `Update`. A write is not complete until `Update` succeeds; the recordset's `Updatable` state and error result determine whether the operation is valid.

Evidence: documented_fact

Source: Microsoft - Recordset object (DAO) - https://learn.microsoft.com/en-us/office/client-developer/access/desktop-database-reference/recordset-object-dao (last verified 2026-08-24)

Guidance: Keep `Edit`/`AddNew` and `Update` adjacent, handle errors, and verify the intended row/key after the update. Do not call `Update` on a recordset that is not updatable.

### Close DAO objects explicitly

Behavior: Opening a recordset adds it to the database's `Recordsets` collection; closing it removes it. Local database and recordset objects are eventually closed when procedure scope ends, but pending updates or transactions can be lost. Explicit completion and cleanup make the outcome observable and deterministic.

Evidence: documented_fact

Source: Microsoft - Database object (DAO) - https://learn.microsoft.com/en-us/office/client-developer/access/desktop-database-reference/database-object-dao (last verified 2026-08-24); Microsoft - Recordset object (DAO) - https://learn.microsoft.com/en-us/office/client-developer/access/desktop-database-reference/recordset-object-dao (last verified 2026-08-24)

Guidance: Close `Recordset` objects after use and complete/rollback pending edits or transactions before leaving the procedure. Use a cleanup path that runs on both success and error.

### Workspace transactions cover its databases

Behavior: `BeginTrans`, `CommitTrans`, and `Rollback` on a `Workspace` apply to all databases opened on that workspace. Independent transaction scopes require a separate workspace/database arrangement.

Evidence: documented_fact

Source: Microsoft - Database object (DAO) - https://learn.microsoft.com/en-us/office/client-developer/access/desktop-database-reference/database-object-dao (last verified 2026-08-24)

Guidance: Identify the workspace boundary before claiming a transaction protects only one database. On errors, choose and document `Rollback` versus propagating the error.
