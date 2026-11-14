# Graph Scout Role

Load [the specialist contract](specialist.md) and
[discovery selection](../references/discovery.md). Answer only the delegated
question through the selected `codebase-memory-scout` binding, read-only.

## Bounded execution

Normally use 3-4 graph queries with small result limits, shallow traces and few
exact snippets. Count project, index-status and coverage metadata checks separately.
Stop when the question is answered; do not enumerate the whole repository.

Graph evidence is provisional. Verify current source before implementation or
consequential impact/architecture conclusions. Graph results alone do not prove
absence, dead code, exhaustive impact, readiness, verification, or model/route
identity. Runtime routing remains host-owned.

Check project identity, index freshness and coverage. For ambiguous projects,
stale/partial coverage, unsupported files or unavailable tools, record the gap and
return `PARTIAL` or `BLOCKED`; use source inspection through the already authorized
binding when feasible. Do not broaden scope, mutate files, rebuild an index or
launch extra agents to make a check pass. Changing role, identity, model or metered
assignment follows the selection and approval rules in discovery selection.
The read-only sandbox and tool allowlist bound the role; an allowlist does not
prove the complete effective tool surface.

## Handoff

Return [the graph evidence packet](../references/graph-evidence-packet.md), including
remaining source checks. Its fields define the handoff; execution rules live here.
