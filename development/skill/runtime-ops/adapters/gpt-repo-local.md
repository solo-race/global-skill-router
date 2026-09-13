---
adapter_schema_version: 1
adapter: gpt-repo-local
environments: [win-access-vba, win-android, wsl-python]
capabilities: [repository.discover, repository.read, repository.git-status, repository.validate, repository.review]
task_modes:
  closed: false
  modes: [inspect, review, validate]
verification_model_kind: independent_checks
mutation_support: none
---

# GPT Repo Local Adapter

## Identity and compatibility

Use the installed `gpt-repo-local` executable resolved from the active environment's PATH. When provider identity or compatibility needs confirmation, run `gpt-repo-local --version` and `gpt-repo-local catalog`; require `protocol_version: 1`. An observed package version or catalog tool count is not a permanent compatibility invariant. Follow runtime-ops' current task/session load/reuse rules; an unchanged valid contract does not require a fresh document or catalog read for each operation.

The local executable and live catalog are the runtime authority for provider identity, protocol compatibility, tool availability, and the registered tool set. The catalog is not an invocation-schema source: it reports each tool's name, title, package, tier, annotations, and required capabilities, and nothing more. Signatures for admitted tools are therefore inlined below; result interpretation, safety boundaries, and failure semantics stay in this document, while full output shapes are not copied. Canonical registered implementation contracts remain the development and maintenance reference of record, but a source checkout is never a deployment or runtime dependency; reuse it only while its compatibility and context remain valid. If the executable or a compatible catalog is unavailable, stop the affected operation and report the missing capability. Do not infer runtime availability from a source checkout or assumed installation path.

## Capabilities and admitted tools

Catalog discovery is not permission. Only the tools in this allowlist are admitted, within their mapped capability and repository policy:

| Capability | Admitted tools |
| --- | --- |
| repository.discover | `repo_list_roots` |
| repository.read | `repo_policy_explain`, `repo_search`, `repo_fetch_file`, `repo_read_many` |
| repository.git-status | `repo_git_status`, `repo_git_diff` |
| repository.validate | `repo_validate` |
| repository.review | `repo_git_review`, `repo_ship_review` |

Tools absent from this allowlist must not be invoked even if the catalog exposes them. Only invocation inputs are restated below; result shapes are read from the returned envelope, not from a schema copy.

## Operations and transport

Discover with `gpt-repo-local catalog`; call an admitted tool with `gpt-repo-local invoke <tool-name>`. Invoke consumes one UTF-8 JSON object on stdin and emits one JSON result envelope on stdout; stderr may contain diagnostics or audit output. Use `structuredContent`, when present, as the machine-authoritative result. Preserve exit status, the structured error envelope, and original failure text; transport completion alone does not establish operation success.

Select `repo_id` from `repo_list_roots`, never a guessed ID or root. Use repository-relative POSIX paths inside the approved root. Effective `repo_policy_explain` policy governs allowed roots/globs, read policy, default excludes, secret guards, containment, nested-repository boundaries, validation profiles, Git-operation policy, and applicable expected-HEAD/stale-state checks. A read result proves access only to its returned scope. Preserve policy denial and incomplete/bounded results rather than bypassing them.

### Invocation signatures

Inputs only, one JSON object per call. Omitted optional fields take the registered tool's own defaults; `?` marks optional and `positive integer` means >= 1. Result shapes are not reproduced here.

```text
repo_list_roots      {}
repo_policy_explain  { repo_id: string, path?: string, operation?: "read" | "write" | "cleanup" | "validation" }
repo_search          { repo_id: string, query: string, mode?: "literal" | "regex", include_globs?: string[], exclude_globs?: string[], context_lines?: integer, max_results?: positive integer, cursor?: string }
repo_fetch_file      { repo_id: string, path: string, start_line?: positive integer, end_line?: positive integer, max_bytes?: positive integer, override_default_excludes?: boolean }
repo_read_many       { repo_id: string, paths?: string[], include_globs?: string[], exclude_globs?: string[], max_files?: positive integer, max_bytes_per_file?: positive integer, max_total_bytes?: positive integer, cursor?: string }
repo_git_status      { repo_id: string }
repo_git_diff        { repo_id: string, base?: string, compare?: string, staged?: boolean, unstaged?: boolean, paths?: string[], max_bytes?: positive integer, max_files?: positive integer, context_lines?: integer }
repo_validate        { repo_id: string, profile: "test" | "build" | "lint" | "typecheck" | "smoke" | "all", test_paths?: string[], dry_run?: boolean, timeout_ms?: positive integer }
repo_git_review      { repo_id: string, mode?: "review" | "commit_plan", detail?: "compact" | "full", paths?: string[], max_files?: positive integer }
repo_ship_review     { repo_id: string, paths?: string[], categories?: ("public_contract" | "api_schema" | "migration" | "authorization" | "configuration" | "async_error" | "test_gap")[], max_findings?: positive integer, max_files?: positive integer, run_id?: string, detail?: "compact" | "full" }
```

Constraints a signature does not carry:

- `repo_read_many`: at least one of `paths` or `include_globs` must be non-empty.
- `cursor` is opaque and reusable only in the operation/filter scope that produced it.
- `repo_search`: context_lines 0..5.
- `repo_git_diff`: context_lines 0..20; pass `repo_id` alone first for the raw diff, and use the other fields to scope it explicitly or refine a second pass.
- `repo_validate`: timeout_ms maximum 300000; only repository-approved runners/profiles are selectable.
- `repo_ship_review`: paths maximum 100 items, categories maximum 7 items, max_findings maximum 100, max_files maximum 500.
- `repo_git_review` and `repo_ship_review`: returned mutation payloads are recommendations only and authorize nothing.

## Failure preservation and mutation boundary

Preserve the exact operation, relevant inputs, returned status, failure text, and unresolved scope. `repo_validate` failed/skipped results remain failed/skipped; a plan is not an executed check, and neither transport success nor a successful read establishes validation success.

`mutation_support: none`. No `repo_write_*`, stage/commit, restore/recovery, patchset apply, delegation writes, or cleanup mutation is authorized. Mutation payloads returned by `repo_git_review` or `repo_ship_review` are recommendations only, never adapter mutation authorization. Do not invoke unlisted tools or use an arbitrary shell substitute for a denied, unavailable, or unsupported operation.

`repo_validate` may execute only a repository-approved validation profile; its declared control-plane side effects do not authorize repository-content mutation. This adapter declares no mutation or rollback path. On failure preserve evidence and stop the affected operation; do not attempt undeclared recovery.

## Verification model

The model is `independent_checks`, with no implication relations and no declared unsupported states. Report each state independently as achieved or unverified; success in one does not upgrade another. Evidence must include the corresponding result envelope with `structuredContent`:

| State | Required evidence and meaning | Does not prove |
| --- | --- | --- |
| `read_observed` | Successful `repo_list_roots`, `repo_policy_explain`, `repo_search`, `repo_fetch_file`, or `repo_read_many` observation | Git cleanliness, validation, semantic correctness, ship readiness, or access beyond returned scope |
| `git_observed` | Current `repo_git_status` or `repo_git_diff` observation | Source correctness, validation success, semantic safety, or ship readiness |
| `validation_observed` | `repo_validate` selected profile's planning/execution status and counts | Unselected checks, semantic correctness, Git cleanliness, or ship readiness |
| `review_observed` | `repo_git_review` bounded change, policy, risk, and recommendation evidence | Suggested mutation executed, validation passed, or correctness/readiness outside returned fields |
| `ship_review_observed` | `repo_ship_review` bounded Git, semantic, validation, and readiness evidence | Universal correctness, mutation executed, or behavior beyond reviewed scope |

Observing validation status does not imply it passed. Retain failed, skipped, unexecuted, stale, and unverified qualifications in reports.

## Environment and configuration

Supported environments are `win-access-vba`, `win-android`, and `wsl-python`. Resolve the executable through that environment's PATH, without hardcoded npm-global or checkout paths. Pass each repository/profile value explicitly; tools do not read skill configuration automatically. Preserve UTF-8 JSON framing.

## Task routing

- `inspect`: discover approved roots, inspect effective policy, then choose the narrowest admitted read operation.
- `review`: obtain `repo_git_status` or an initially unfiltered `repo_git_diff`, then use `repo_git_review` or `repo_ship_review` as needed.
- `validate`: select the repository-approved `repo_validate` profile and report its actual status/counts; use its evidence in later review when relevant.

Task modes are open (`closed: false`); unmatched intent returns to the runtime-ops core lifecycle without expanding this allowlist.

## Provenance

Contract structure follows `../references/contract-template.md` and `../references/verification-ladder.md`. The live `gpt-repo-local catalog` is the runtime authority for provider identity, protocol compatibility, tool availability, and the registered tool set — not an invocation-schema source. The minimal invocation signatures inlined above are the invocation contract a deployed adapter forms calls from. Canonical registered handlers/services in `gpt-repo-mcp` are the development and maintenance reference of record for cross-checking those signatures, their defaults/constraints, and result interpretation semantics. A `gpt-repo-mcp` checkout is read-only design input, never a deployment or runtime dependency. A deployed adapter operates through the installed local executable and its live catalog; no MCP server, ChatGPT app, or connector is required by this transport.

