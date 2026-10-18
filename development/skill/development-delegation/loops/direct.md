# Direct Execution

Use a brief when files/solution and acceptance are known, scope bounded and risk low.
A master plan, planning role and fixed team are unnecessary. Include authority,
identity constraints, ownership, checks and finite budgets in the brief.

Inspect only missing relevant evidence; assign an implementer only if needed. Validate
against explicit criteria, using a tester when independent execution or specialized
tools are needed. Implementation self-checks may be allowed by the brief, but are not
independent review. Apply modules/review.md regardless of human availability.

Accept only current criterion-level evidence and, for multiple changes, combined-tree
validation. New uncertainty -> Exploratory read-only; complex dependencies or risk ->
Planned. Pause writes while authority/contract is unresolved; preserve counters and
permissions. Follow loops/implementation.md for execution and recovery semantics.
