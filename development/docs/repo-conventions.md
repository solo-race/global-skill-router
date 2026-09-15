# Repository Conventions (Expanded Reference)

Expanded repository reference. Binding constraints live in the root `AGENTS.md`; this file holds the full detail those constraints summarize. Read on demand, not by default.

Derived from three architecture reviews archived under [`architecture-ref/`](architecture-ref/README.md).

## Project Overview

Content repository building a global SKILL control platform ("Global Skill 结构构建") for the local Codex development environment. The platform has a manifest/validator control plane, a single active router Skill, and two active framework modules (`development/skill/research-investigation/` and `development/skill/runtime-ops/`), with read-only design references under `references/` and planned host adapters registered for future scenarios. Per `README.md` (Chinese), the mandated workflow is to analyze those structures and keep the deployed architecture under `development/skill/`. Target dev scenarios: Windows-native work (SQL databases, Access frontends, Access/Excel VBA), Android apps on Windows, and WSL Python filtering projects.

There is no application source or build system here. Deliverables are Markdown skill modules plus Python helper scripts; `development/tools/deploy_skills.py` assembles the routed runtime payload (prefer stdlib-only; third-party imports only where declared, see **Python scripts** below).

## Architecture & Data Flow

Two-layer design:

1. **Reference layer** — `references/`: three skill collections copied/built as analysis input. Read-only; do not modify.
2. **Development layer** — `development/skill/` (managed Skills and manifest), `development/skill-repos/` (independent Skill development repositories), and `development/docs/` (project docs incl. `architecture-ref/`).

Intra-module data flow (SpineCodex pattern): `SKILL.md` instructs the agent → agent invokes `scripts/<name>.py` → script shells out to the `gh` CLI via `subprocess.run` → emits JSON (or JSONL in watch mode) on stdout → agent interprets output against rules in `references/*.md`.

Skill module anatomy (the pattern to replicate):

```
<skill-name>/                  # kebab-case slug
├── SKILL.md                   # required: YAML frontmatter + instructions
├── agents/openai.yaml         # optional: interface metadata
├── scripts/<name>.py          # optional helper (+ sibling test_<name>.py)
└── references/*.md            # optional per-skill deep notes
```

For heavier skills, extend toward the five-layer stack reviewed in `architecture-ref/01-layering.md` (workflows/, tool-contracts/, profiles/).

## Key Directories

- `references/SpineCodex-skills/` — 14 upstream skills: `update-v8-version`, `test-tui`, `remote-tests`, `pushing-ci-changes`, `path-types`, `codex-pr-body`, `codex-issue-digest`, `codex-bug`, `code-review`, `code-review-testing`, `code-review-context`, `code-review-change-size`, `code-review-breaking-changes`, `babysit-pr`.
- `references/SpineCodex-skills/babysit-pr/` — most complete module (16.7KB SKILL.md, watcher script, tests, references/); canonical template.
- `references/customer-research-skills/recycling-company-investigation/` — self-built methodology-type skill (three-layer lifecycle bucketing).
- `references/access-vba-dev/` — self-built engineering-type skill (five-layer stack + repo meta layer).
- `development/skill/` — platform skill library: `manifest.yaml` registry plus rebuilt skills (staging target for the rebuild).
- `development/skill-repos/` — independent Git source libraries, each retaining its own `.git`; local checkouts are ignored by the enclosing repository and registered in the manifest's `sources[]`.
- `development/docs/` — project documentation (`architecture-ref/` module reviews, this file, [`plans/`](plans/) execution roadmap, and the derived [`scenario-routing.md`](scenario-routing.md)).
- `.github/`, `.codex/` — exist but empty; purpose not yet defined.

## Code Conventions & Common Patterns

**SKILL.md format** (all English; only root README.md is Chinese):

- Frontmatter: exactly two fields, `name` and `description`; `name` must equal the directory slug. Description is one sentence ending with a "Use when …" trigger phrase for discovery matching.
- Body scales with complexity: minimal skills are frontmatter + prose bullets; larger ones use H1 title, numbered workflow steps, fenced ```bash command blocks, Stop Conditions, References.
- Orchestrator pattern: `code-review/SKILL.md` delegates to the `code-review-*` sub-modules.

**agents/openai.yaml**: single `interface:` mapping with `display_name`, `short_description`, `default_prompt`; `default_prompt` embeds the `$<skill-name>` trigger. Only for agent-facing entry skills.

**Python scripts** (stdlib-first — third-party imports only where declared in AGENTS.md Core Rule 5; external systems accessed via subprocess/MCP):

- Shebang `#!/usr/bin/env python3` + module docstring; no type annotations; conservative Python 3.8+ compatibility.
- `parse_args()` builds argparse; flag conflicts validated post-parse via `parser.error(...)`.
- Subprocess failures wrapped in a custom error class carrying formatted stdout/stderr.
- Output contract: one JSON document via `sys.stdout.write(json.dumps(..., indent=2, sort_keys=True))`; long-running modes stream JSONL with explicit `flush()`. Errors → stderr, exit 1; `KeyboardInterrupt` → exit 130.
- Entry point: `def main()` guarded by `if __name__ == "__main__": raise SystemExit(main())`.
- Module constants SCREAMING_SNAKE at top; persistent state written atomically (`tempfile.mkstemp` + `os.replace`).
- One script per skill named after its function.

## Important Files

- `README.md` — project mandate (Chinese).
- `references/SpineCodex-skills/babysit-pr/SKILL.md` — canonical full-scale skill template.
- `references/SpineCodex-skills/path-types/SKILL.md` — minimal rules-style example.
- `references/SpineCodex-skills/babysit-pr/scripts/gh_pr_watch.py` — reference implementation of the script style above.
- `references/access-vba-dev/` — most advanced structural model (layering, verification ladder, evidence-typed knowledge).
- Known inconsistency: `code-review-breaking-changes/SKILL.md` frontmatter says `name: code-breaking-changes` (mismatches directory name). Do not copy that mistake — `name` must equal the directory slug.

## Runtime/Tooling Preferences

- Python 3 (scripts assume ≥3.8 APIs; no version pin file exists). `gh` CLI required by the two scripted reference skills; declared third-party dependency: PyYAML (manifest/frontmatter parsing for `tools/validate_skills.py` and route generation for `tools/deploy_skills.py`).
- No git history/config, no package manager, no formatter/linter config — do not introduce tooling speculatively; keep the repo minimal.
- Command paths inside reference SKILL.md files address the upstream Codex checkout (`.codex/skills/…`); substitute `references/SpineCodex-skills/` locally. Some referenced validation targets do not exist in this repo — they belong upstream.

## Deployment and Runtime Mapping

- **Source of truth:** `development/skill/<name>/` is the source root for a managed Skill. Only
  entries whose `skills[].status` is `active` in `development/skill/manifest.yaml` are eligible
  for deployment. The manifest must pass `validate_skills.py` before a payload is built.
- **Independent source libraries:** register each repository in `sources[]` with
  `kind: development-repository`, a repo-relative POSIX `path` below
  `development/skill-repos/`, its canonical `origin`, a non-empty `pinned_ref`, and
  `required: false`. The validator accepts absent optional checkouts and validates
  managed Skills under `development/skill/` separately. Source registration neither
  activates a Skill nor adds source-repository files or routes to the deployed payload.
- **Routed payload boundary:** `deploy_skills.py` installs one managed top-level directory,
  `global-skill-router/`. The router source is copied to the payload root; active
  `deployment_role: module` Skills are copied below `global-skill-router/library/<name>/`.
  Existing `agents/`, `references/`, `profiles/`, `adapters/`, and `scripts/` directories
  travel with their owning Skill. `development/tools/`, plans, and read-only source references
  never enter the payload.
- **Routing rule:** active modules default to `routing_scope: scenario` and are projected only
  into their declared `scenarios[]` shards. A cross-scenario task-intent module may instead
  declare `routing_scope: global`, a short `routing_selector`, and `scenarios: []`; active global
  routes are embedded in the route index and are checked before any scenario shard. A global hit
  therefore costs the index read plus the selected module read, not three scenario-shard reads.
- **Owner rule:** adapters and profiles are owner-contained extensions. An adapter is deployed
  with its owner Skill and is not installed as a separate top-level Skill.
- **Dependency rule:** before deploying an active Skill, its `deps[]` and active
  `composed_of[]` targets must be available in the target environment as represented by the
  manifest.
- **Path rule:** Skill files use paths relative to their own Skill root. At runtime the router
  root is the directory containing the loaded `global-skill-router/SKILL.md`; `_platform/...`
  and `library/...` paths resolve only from that root, never from process CWD or a source-repo
  root. The eventual target may be a user-level or project-level skill root; the Skill must not
  assume `.codex/skills/` or `.agents/skills/`.
- **Self-containment:** an active Skill must retain all runtime decision-making material inside
  its own root. Optional `sources[]` references may be absent after deployment.
- **Planned exclusion:** planned Skills and adapters are registration records, not runtime
  capabilities, even if a development directory happens to exist. Planned entries never enter
  route shards or `library/`.
- **Managed operations:** the standard commands are `py -3 development/tools/deploy_skills.py`
  (read-only plan), `--apply`, `--verify`, and `--rollback`; pass `--target-root PATH` for a
  controlled user/project skill root. Apply stages a complete payload, keeps at most one
  tool-owned previous snapshot beside the target root, verifies hashes/layout/routes, and
  restores the previous managed router if replacement or verification fails.
- **Drift and coexistence:** `--verify` reports missing, extra, or changed managed files without
  overwriting them. The manager only owns `<target-root>/global-skill-router` and its dedicated
  snapshot; legacy or unrelated Skills such as `vba-skill` are left byte-for-byte untouched.

## Testing & QA

- Framework: pytest — plain `test_*` functions, bare `assert`s, `monkeypatch`/`tmp_path` fixtures; no `unittest.TestCase`, no mock library.
- Tests are colocated: `scripts/test_<script_name>.py` beside the covered script, loaded via `importlib.util.spec_from_file_location(Path(__file__).with_name(...))` so they run from any cwd without package setup.
- Fixture style: helper factories returning sample payloads plus call-recording lists asserted after invocation.
- Scope: pure-function unit tests rather than subprocess integration; no coverage configuration or thresholds.
