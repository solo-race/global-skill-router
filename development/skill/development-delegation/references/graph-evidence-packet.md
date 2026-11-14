# Graph Evidence Packet

A bounded handoff for one `codebase-memory-scout` discovery question, not a repository
report. Load only for a selected graph assignment. [Discovery selection](discovery.md)
owns dispatch; [the graph-scout role](../roles/graph-scout.md) owns execution, evidence
limits and fallback. This document owns only the output shape.

## Packet shape

```text
GRAPH_EVIDENCE_PACKET

unit:
role: CODEBASE_MEMORY_SCOUT
status: COMPLETE | PARTIAL | BLOCKED

pass:
- project: <graph project/worktree identity>
- index: <index identity>
- freshness: <indexed revision or time versus the current worktree>
- metadata_checks: <count; reported separately from graph queries>
- graph_queries: <count>

observed:
- <path | symbol | relation> -> <fact, with the query or document that produced it>

relationships:
- <caller/callee | import | dependency | entrypoint> from <symbol/path> to <symbol/path> (how obtained)

coverage:
- <included, excluded, stale, partial or skipped areas; unsupported file types>

source_checks_still_required:
- <what must be read in the current source before implementation or an impact decision>

inference:
- <optional; keep separate from observed facts>

blockers_or_scope_notes:
- <none, or the gap that stopped a graph answer>
```
