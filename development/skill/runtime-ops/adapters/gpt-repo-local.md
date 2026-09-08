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

# gpt-repo-local Adapter

## 1. Identity, version, and source of truth

The provider is the installed gpt-repo-local executable. When capability identity matters, run gpt-repo-local --version and gpt-repo-local catalog; require a catalog with the currently supported protocol_version: 1. Do not treat the observed package version or catalog tool count as a permanent compatibility invariant.

The live gpt-repo-local catalog and the registered handlers/services in gpt-repo-mcp are the source of truth for names, schemas, and result shapes. The gpt-repo-mcp checkout may be consulted read-only while maintaining this contract, but it is never a deployment or runtime dependency. Runtime availability is established by the executable and catalog checks, not by a source path or an assumed installation location.

The transport framing is:

~~~text
gpt-repo-local catalog
gpt-repo-local invoke <tool-name>
~~~

invoke reads exactly one UTF-8 JSON object from standard input and writes one JSON result envelope to standard output. Diagnostics and audit records may appear on standard error. Preserve the process exit status, the complete structured error envelope, and its failure text. When structuredContent is present, it is the machine-authoritative result; surrounding human-readable text never overrides it.

## 2. Capabilities

| Stable capability | Registered tools admitted by this adapter |
|---|---|
| repository.discover | repo_list_roots |
| repository.read | repo_policy_explain, repo_search, repo_fetch_file, repo_read_many |
| repository.git-status | repo_git_status, repo_git_diff |
| repository.validate | repo_validate |
| repository.review | repo_git_review, repo_ship_review |

The catalog currently contains additional tools, but names not explicitly admitted in this table are outside this adapter revision and must not be invoked through it. In particular, catalog discovery is not permission to use a tool: load this contract and select one of the admitted capabilities first.

## 3. Operations

All inputs below are the single JSON object supplied on stdin after invoke <tool-name>. repo_id must be an approved, stable id returned by repo_list_roots; paths are repository-relative POSIX paths. Omitted optional fields retain the registered implementation's defaults.

### repo_list_roots

Input: {}. It returns {repos: [{repo_id: string, display_name: string, root: string}]} and does not read repository contents. Use it before selecting a repository; never invent a root or id.

### repo_policy_explain

Input: {repo_id: string, path?: string, operation?: "read" | "write" | "cleanup" | "validation"}. The result is {ok: true, repo_id, path?, requested_operation?, summary, read, write, cleanup, validation, operations, effective_policy, guidance}. Each policy decision (read, write, cleanup, validation) contains {allowed, code, reason, matched_globs, notes}. operations contains {enabled, git_stage_enabled, git_commit_enabled, validation_enabled, cleanup_enabled, max_paths_per_operation}; effective_policy contains {write_enabled, write_allowed_globs, write_denied_globs, max_bytes_per_write, default_read_excludes, cleanup_allowed_globs}. Use this operation to inspect effective policy instead of guessing why a call is blocked.

### repo_search

Input: {repo_id: string, query: string, mode?: "literal" | "regex", include_globs?: string[], exclude_globs?: string[], context_lines?: integer (0..5), max_results?: positive integer, cursor?: string}. mode defaults to literal; cursor is opaque and may be reused only with the same search scope. The result is {results: [{path, line, column, text, before: string[], after: string[]}], matched_count, returned_count, truncated, next_cursor?, warnings: string[]}.

### repo_fetch_file

Input: {repo_id: string, path: string, start_line?: positive integer, end_line?: positive integer, max_bytes?: positive integer, override_default_excludes?: boolean}. The result is {path, language?, size_bytes, sha256, total_lines, start_line, end_line, truncated, text, warnings: string[]}. The path remains subject to repository read policy and default excludes; an override is explicit and does not bypass secret or containment policy.

### repo_read_many

Input: {repo_id: string, paths?: string[], include_globs?: string[], exclude_globs?: string[], max_files?: positive integer, max_bytes_per_file?: positive integer, max_total_bytes?: positive integer, cursor?: string}. At least one non-empty paths or include_globs is required. The result is {files: [FileContent], skipped: [{path, reason}], matched_count, returned_count, truncated, next_cursor?}, where each FileContent has the repo_fetch_file fields. This is a bounded read, not an entire-repository shortcut.

### repo_git_status

Input: {repo_id: string}. The result is {branch, head_sha, clean, counts: {[status: string]: nonnegative integer}, files: [{path, original_path?, index, worktree}]}. It reports the configured repository's current Git observation only.

### repo_git_diff

Input: {repo_id: string, base?: string, compare?: string, staged?: boolean, unstaged?: boolean, paths?: string[], max_bytes?: positive integer, max_files?: positive integer, context_lines?: integer (0..20)}. The first raw-diff call should pass only repo_id; the other fields are second-pass refinements or explicit scope. The result is {base?, compare?, staged?, unstaged?, files: [{path, original_path?, status?, hunks: string[]}], total_file_count, truncation_reason?: "max_files" | "max_bytes" | "max_files+max_bytes", truncated, warnings: string[]}.

### repo_validate

Input: {repo_id: string, profile: "test" | "build" | "lint" | "typecheck" | "smoke" | "all", test_paths?: string[], dry_run?: boolean, timeout_ms?: positive integer (maximum 300000)}. Validation uses the repository's allowlisted runner policy; it is not a generic shell interface. The result is {ok: true, repo_id, validation_id?, profile, focused?, test_paths?, dry_run, status: "passed" | "failed" | "skipped", commands: [{profile, script, command, runtime?: {name: "node", version, source}, status, exit_code?, duration_ms?, stdout_tail?, stderr_tail?}], counts: {total, passed, failed, skipped}, warnings: string[], validation_artifact?: {path}}. A returned failed/skipped status remains a validation result, not success; preserve all bounded output tails and failure text.

### repo_git_review

Input: {repo_id: string, mode?: "review" | "commit_plan", detail?: "compact" | "full", paths?: string[], max_files?: positive integer}. detail defaults to compact; paths scopes recommendations to exact changed paths. The successful result contains {ok: true, detail, branch, head_sha, clean, changed_paths: [{path, original_path?, index, worktree, status: "modified" | "added" | "deleted" | "renamed" | "untracked" | "unknown", staged, unstaged}], diff_summary: {file_count, truncated, files: [{path, status?, hunk_count, summary}]}, recommendation: {ready_to_stage, recommended_stage_paths, excluded_paths: [{path, reason}], suggested_commit_message, risk_level: "low" | "medium" | "high", warnings, recovery_guidance?}, delegation_gate, ship_readiness: {validation: {status: "missing" | "passed" | "failed" | "stale", ...}}, next_tool_payloads}. Any payloads for mutation tools are review output only and are not authorized by this adapter.

### repo_ship_review

Input: {repo_id: string, paths?: string[] (maximum 100), categories?: ("public_contract" | "api_schema" | "migration" | "authorization" | "configuration" | "async_error" | "test_gap")[] (maximum 7), max_findings?: positive integer (maximum 100), max_files?: positive integer (maximum 500), run_id?: string, detail?: "compact" | "full"}. detail defaults to compact; run_id is an optional Delegation v3 identity. The result combines {ok: true, detail, repo_id, run_id?, git_review, delegation_gate?, semantic_review, failure_diagnosis?, ship_readiness: {status: "ready" | "review_required", reasons: [...], validation_status: "missing" | "passed" | "failed" | "stale", blocking_finding_ids, diagnosis_included}, next_tool_payloads: {repo_validate?: {repo_id, profile: "all"}, repo_write_stage_commit?, repo_write_commit?, repo_write_commit_dry_run?}, review_loop?, truncated, warnings}. Treat semantic findings, Git evidence, validation status, and readiness as the scopes returned; never promote one into another. Do not invoke any mutation payload returned here.

## 4. Preconditions and failures

The executable must be on the current environment's PATH and must pass the identity/catalog check when identity matters. The selected repo_id must appear in repo_list_roots; GPT Repo configuration remains authoritative for its root, allowed paths, default excludes, secret guards, nested-repository boundaries, validation profiles, Git-operation policy, and any expected-HEAD or stale-state checks. Never bypass those controls by substituting a filesystem path, another repository id, an arbitrary command, or a generic shell.

Calls may fail because the executable is unavailable, the catalog/protocol is unsupported, the repository id or path is not approved, policy blocks access, validation is disallowed, Git state is stale, or a registered handler returns an error. Preserve the actual nonzero exit status, stderr diagnostics, structured error envelope, and failure text verbatim. Never reinterpret a tool error, a blocked policy decision, a failed validation status, or a truncated result as success.

## 5. Mutation model

This revision authorizes no GPT Repo mutation operation. repo_validate may execute only the repository-approved validation profile and may emit a redacted validation artifact; that control-plane side effect is not a repository-content mutation surface. Do not expose or invoke repo_write_*, stage/commit/restore/recovery tools, patchset application, delegation writes, cleanup mutation, or any generic shell substitute through this adapter. Ordinary Codex source editing continues through the native Codex harness edit/patch/shell workflow; use this adapter for repository observation, control, review, and validation.

## 6. Verification model

The adapter uses independent checks. Each check proves only the returned scope and never implies another check.

~~~yaml
verification_model:
  kind: independent_checks
  states:
    - id: read_observed
      meaning: An admitted repository discovery or read operation returned structured content successfully.
      required_evidence: [repo_list_roots, repo_policy_explain, repo_search, repo_fetch_file, or repo_read_many result envelope with structuredContent]
      does_not_prove: [Git cleanliness, validation outcome, semantic correctness, ship readiness, or access beyond the returned scope]
    - id: git_observed
      meaning: An admitted Git status or diff operation returned a current repository observation.
      required_evidence: [repo_git_status or repo_git_diff result envelope with structuredContent]
      does_not_prove: [source correctness, validation success, semantic safety, or ship readiness]
    - id: validation_observed
      meaning: The requested allowlisted validation profile returned its selected planning or execution status.
      required_evidence: [repo_validate result envelope with structuredContent and its status/counts]
      does_not_prove: [unselected checks, semantic correctness, Git cleanliness, or ship readiness]
    - id: review_observed
      meaning: Git review returned its bounded change, policy, risk, and recommendation evidence.
      required_evidence: [repo_git_review result envelope with structuredContent]
      does_not_prove: [that any suggested mutation was executed, validation passed, semantic correctness, or ship readiness outside its returned fields]
    - id: ship_review_observed
      meaning: Combined ship review returned its bounded Git, semantic, validation, and readiness evidence.
      required_evidence: [repo_ship_review result envelope with structuredContent]
      does_not_prove: [that the repository is universally correct, that a mutation payload was executed, or behavior beyond the reviewed scope]
  relations: []
  unsupported: []
~~~

Report each state independently as achieved or unverified. A successful read, Git observation, validation, review, or ship review never upgrades another state.

## 7. Recovery model

No adapter mutation exists in this revision, so no rollback operation is defined. If a validation command or read/control call fails, preserve its original result and failure text; do not attempt an undeclared GPT Repo write or recovery tool. Any native Codex edit has its own harness and repository workflow outside this adapter contract.

## 8. Environment and configuration

The adapter is routed for win-access-vba, win-android, and wsl-python. In each environment, resolve gpt-repo-local from the active PATH; do not depend on the developer's npm-global path or on a checked-out gpt-repo-mcp tree. Use UTF-8 JSON framing, pass every repository/profile value explicitly in the invoke object, and retain opaque cursors only for the operation and filters that produced them. The CLI may be unavailable in a particular host session; in that case stop the affected adapter operation and report the missing capability rather than guessing a substitute.

## 9. Task routing

inspect covers approved-root discovery, policy inspection, targeted search, and bounded reads: start with repo_list_roots, then use the narrowest admitted read operation. review covers current Git observation and change/readiness review: use repo_git_status or the first unfiltered repo_git_diff, then repo_git_review or repo_ship_review as the requested evidence requires. validate covers an allowlisted repo_validate profile and may feed its returned evidence into a later review. task_modes.closed is false; unmatched intents fall back to the Runtime Operations core lifecycle rather than being forced into one of these modes.

## 10. Provenance

This contract follows runtime-ops/references/contract-template.md and runtime-ops/references/verification-ladder.md. Tool names, schemas, defaults, and result fields were checked against the live gpt-repo-local catalog and the registered implementation contracts in gpt-repo-mcp during development. Those references are read-only design inputs only; a deployed runtime-ops skill must operate solely through the installed gpt-repo-local executable and its live catalog.

