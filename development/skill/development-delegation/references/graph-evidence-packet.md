# Graph Evidence Packet

The `codebase-memory-scout` role returns this packet to the supervisor. It is a
bounded handoff for one discovery question, not a repository report. Graph
evidence is provisional: it locates candidate symbols, files and relationships,
and it never substitutes for reading the current source.

## Selecting a graph pass

`SKILL.md` "Discovery selection" is the single selection authority; this packet
does not restate the criteria. A graph packet is reused rather than re-derived,
and one discovery question is not run through both an ordinary scout and a graph
scout by default.

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
- graph_queries: <count; normally 3-4>

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

## Bounded pass

Normally 3-4 graph queries, small result limits, shallow traces and only a small
number of exact snippets. Count metadata checks (project resolution, index
status, coverage) separately from graph queries. Stop when the question is
answered; do not expand into whole-repository enumeration.

## What graph evidence cannot support

- Absence ("not found means absent"), dead-code, exhaustive impact, or readiness
  and verification claims.
- Impact or architecture conclusions that do not check the current source at the
  cited paths.
- Model or route identity. A successful graph query does not establish either;
  runtime routing remains host-owned and is not a graph-scout acceptance signal.

## Fallback

- Ambiguous project, stale or partial coverage, unsupported files, or unavailable
  tools: report the gap in `coverage` and `blockers_or_scope_notes` and keep
  `status` at `PARTIAL` or `BLOCKED`.
- Continue with source inspection through the selected authorized role when
  feasible.
- Switching to a different registered role or model follows the existing
  selection and approval policy; never silently incur different quota.
- Never rebuild the index or launch extra agents merely to make a graph check
  pass.

The read-only sandbox and the tool allowlist bound this role. An allowlist is not
proof of the complete effective tool surface.
