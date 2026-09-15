# Phase Plan

Use only when the repository has no established detailed-plan format. Preserve an existing project planning convention when available.

```text
PHASE_PLAN

phase:
status: ACTIVE | PLANNED | BLOCKED
objective:
master_plan_relation:

scope:
- allowed: <paths/modules/behavior>
- excluded: <material exclusions>

units:
- id: <stable id>
  goal: <bounded implementation outcome>
  depends_on: <ids or none>
  acceptance:
    - <observable criterion>
  validate:
    - <exact check/test/manual evidence>
  notes:
    - <constraint or risk if material>

phase_exit:
- <observable condition proving phase completion>

material_risks:
- migration/compatibility/rollback/permission/data-loss/irreversible: <none or explicit issue>

assumptions:
- <assumption with source or authority owner>

authority_decisions:
- <none or decision that must be resolved outside mechanical execution>
```

Every implementation unit must be independently understandable and externally verifiable. Put architecture decisions into the plan before implementation rather than allowing workers to improvise them.
