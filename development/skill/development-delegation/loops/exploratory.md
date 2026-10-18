# Exploratory Work

Start with a bounded question, evidence needed, source/tool scope, finite pass budget
and stop condition. Read-only is the default. Use scout or a narrowly justified
specialist; no mandatory planner, implementer or team. Apply discovery selection.
Report observations, hypotheses, unknowns and the smallest next decision separately.

Experiments are not implied by exploration. Before any mutation or state-changing
command, require explicit authority naming the experiment, allowed changes/workspace,
data/services, cost/time/tool/count ceilings, validation, rollback/cleanup and stop
conditions. Policy defaults allow zero experiments. Isolation is required for mutable
experiments; do not treat a temporary directory as permission to touch real services.
No production writes, network transmission, installation, indexing or permission
changes are implicitly authorized. Read-only tools with external effects still obey
applicable approval rules.

Stop a pass when its question is answered or budget exhausted. Negative/partial graph
results are not absence. Failed experiments return evidence and execute only approved
safe cleanup; do not iterate outside limits. If rollback is unsafe or fails, block
and report state. Findings may propose Direct or Planned; execution starts only after
the target mode's scope, authority, risk/review and evidence requirements pass.
Unresolved questions at budget exhaustion -> BLOCKED, not endless investigation.
