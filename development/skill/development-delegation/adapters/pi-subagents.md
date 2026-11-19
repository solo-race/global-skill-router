---
adapter_schema_version: 1
adapter: pi-subagents
adapter_scope: host-execution
host_package: pi-subagents
bindings: routing/pi-bindings.yaml
package_filter: references/pi-package-filter.json
filter_tool: scripts/apply_pi_filter.py
---

# Pi Execution Adapter

Maps the abstract delegation roles onto concrete Pi execution identities. This is a
host-execution binding, not a scenario runtime adapter: it declares no `environments`,
carries no route-shard entry, and is loaded with its owner module. The role module
stays authoritative for behavior; the binding chooses who executes it and grants no
tools, model route or authority.

## Role mapping

| Delegation role | Pi identity | Binding | Notes |
|---|---|---|---|
| `scout` | `scout` | package builtin | Read-only recon; returns compressed context for handoff. |
| `planner` | `planner` | custom agent, else authorized generic | No builtin planner. Needs a registered read-only planner profile, or a generic agent whose actual capabilities fit. |
| `implementer` | `worker` | package builtin | Single writer; honors only the brief's scope and authority. |
| `tester` | `tester` | custom agent | No builtin tester. Needs a registered agent; execution is the default, authoring needs owned test paths. |
| `reviewer` | `reviewer` | package builtin | Fresh context; the independent-review requirement is unchanged. |
| `specialist` | none fixed | dynamic per task | Select a registered specialist identity, else an authorized generic agent that fits the selected specialty's capabilities. |

The machine-readable form is [routing/pi-bindings.yaml](../routing/pi-bindings.yaml).
Availability comes from the live host catalog, not from this table: a missing custom
`planner`/`tester` identity blocks that assignment. Substituting a generic agent needs
authorization plus a real capability fit; never relabel a different identity to make
the table look complete.

## Capability injection

A Pi child receives only the tools named in its agent definition. Builtin allowlists do
not inherit the parent's skills, MCP servers, or ambient extension tools, so an identity
mapping alone does not establish executable capability. Every binding therefore declares
the tool surface and the capability it satisfies; a surface that misses a required tool
makes the assignment `BLOCKED`, never a degraded success.

| Role | Required capability | Injection |
|---|---|---|
| `scout` | read-only local discovery | Builtin `scout` allowlist. It writes only its bound output artifact and never source. |
| `scout.graph` | Codebase Memory graph discovery | [agents/pi/codebase-memory-scout.md](../agents/pi/codebase-memory-scout.md): read tools, inspection `bash`, and read-only `mcp:codebase-memory-mcp/*` selectors. |
| `planner` | read evidence, decide, no mutation | [agents/pi/planner.md](../agents/pi/planner.md): `read`, `grep`, `find`, `ls`, `contact_supervisor` only. |
| `implementer` | bounded source mutation and checks | Builtin `worker` allowlist (`read`, `grep`, `find`, `ls`, `bash`, `edit`, `write`). |
| `tester` | execute approved checks | [agents/pi/tester.md](../agents/pi/tester.md): `bash` plus `edit`/`write` for explicitly owned test-author paths only. |
| `reviewer` | independent read-only review | Builtin `reviewer` allowlist: no `edit`, no `write`, no `bash`. |
| `specialist` | task-selected | The assignment must name an installed identity whose allowlist covers the specialty; otherwise `BLOCKED`. |

Injection rules:

- MCP tools are selected with `mcp:<server>/<tool>` entries in the agent's `tools`
  allowlist. The child connects the `mcp.json` servers and receives only those direct
  tools; naming a server does not load an unrelated extension. Selectors resolved
  through an ambient MCP adapter need a background child (`async: true`), which every
  shipped MCP profile sets.
- Shipped profiles live under [agents/pi/planner.md](../agents/pi/planner.md) and its
  siblings (`tester.md`, `codebase-memory-scout.md`) inside this module. Copy them
  into the host agent directory (`host.agent_install_root`, normally
  `~/.pi/agent/agents`) to register them; the copy is deployment-owned and this module
  hardcodes no install path.
- `inheritSkills: false` means role knowledge is not inherited. The assignment names
  the role module path under the loaded delegation skill root, and each shipped profile
  instructs the child to read it.
- The builtin `worker` lists no MCP selectors. When an authorized scope needs MCP tools,
  bind a deployment-local writer profile that adds the exact `mcp:` selectors and launch
  it in the background. Without that profile the assignment is `BLOCKED`; do not widen
  the builtin by guessing tool names.

Verify declarations against the host before delegating:

```bash
pi mcp list --json > /tmp/pi-mcp.json
uv run python scripts/verify_pi_capabilities.py --mcp-catalog /tmp/pi-mcp.json
```

It checks role capability coverage, shipped-profile allowlists, the installed identity
directory, and every `mcp:` selector against the live catalog. A non-zero exit names the
blocked identities; treat each one as unavailable rather than substituting a route.

| Acceptance check | Passes when |
|---|---|
| Scout | The graph variant declares the Codebase Memory selectors, the live catalog exposes them, and the profile is installed. |
| Planner | The installed planner profile exposes only read tools and cannot modify files. |
| Worker | The bound writer allowlist covers the authorized work, or its MCP augmentation exists and the assignment is `BLOCKED` otherwise. |
| Tester | The installed tester profile can run the approved checks through `bash`. |
| Reviewer | The bound reviewer surface has no mutation tools and the launch keeps fresh context. |
| Failure handling | A missing identity or tool is reported as `BLOCKED`, both by the contract and by the verifier. |

## Launch interface

- `subagent({ agent, task, ... })` runs one child and is async by default. Block
  (`async: false`) only when this task needs the result before continuing; final
  reviews and gates stay async.
- Independent children use `subagent({ workflow: "parallel", args: { tasks: [...] } })`.
  Dependent steps, keyed aggregation and resume use one ```js workflow block``` in the
  same reply, launched with `subagent({ workflow: true })`; a script file is
  `workflow: "./lane.js"` relative to the request cwd.
- If only `subagents_enable` is exposed, call it once; `subagent` arrives on the next
  request. Manager actions are `status`, `resume`, `steer`, `interrupt`, `stop`, `list`;
  resume needs the latest run id and excludes `agent`.
- Bind deliverables with `output` and return `outputReference`/`artifactPaths`; a
  filename inside task prose routes nothing. Keep reports out of the repository root
  and delete scratch briefs and scripts when the task ends.
- One writer per cwd or worktree. Isolate parallel mutation with `worktree: true` from a
  clean checkout; for Pi extension repositories keep worktrees outside the managed
  skill root.
- Children do not spawn subagents unless this brief delegated fanout and the resolved
  tool set includes `subagent`.

Every child starts cold: the brief carries goal, cwd/ref, authority and edit boundary,
relevant files and evidence, success criteria, validation, expected output, and when to
stop or ask. Use `context: "fork"` only when the child needs the parent history and the
parent session is persisted; otherwise prefer fresh context, which reviewers require.

## Duplicate-functionality filter

The host package ships capabilities that overlap managed router contracts. The
canonical filter is [references/pi-package-filter.json](../references/pi-package-filter.json);
[scripts/apply_pi_filter.py](../scripts/apply_pi_filter.py) reports or applies it to a
Pi settings file. It drops the package skills `pi-subagents` and `council-mode` (this
adapter and the router carry the delegation contract), disables the builtin agents
`delegate`, `oracle`, `researcher` and `evidence-auditor` (covered by `worker`
implementation, independent review, and the `research-investigation` module), and loads
no package prompt templates.

Never invoke a filtered identity and never re-add a filtered skill to fill a missing
contract. Report the gap or ask for an explicit change. When the filter is not in
effect, report that before delegating and treat those identities as unavailable.

## Failure boundary

A failed launch, workflow, child tool setup or extension load stops the affected
assignment: report the exact failure plus run/worktree state, verify a clean worktree
or capture the partial diff, and retry the same way once. Do not switch CLI, model or
route around the failure without an explicit decision. Child claims are evidence for
review, never acceptance.
