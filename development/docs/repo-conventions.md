# Repository Conventions (Expanded Reference)

Expanded repository reference. Binding constraints live in the root `AGENTS.md`; this file holds the full detail those constraints summarize. Read on demand, not by default.

Derived from three architecture reviews archived under [`architecture-ref/`](architecture-ref/README.md).

## Project Overview

Content repository building a global SKILL system ("Global Skill 结构构建") for the local Codex development environment. Currently at scaffolding stage: a mature 14-skill reference library lives under `references/SpineCodex-skills/`, plus two self-built skills (`references/cusomer-research-skills/recycling-company-investigation/`, methodology-type; `references/access-vba-dev/`, engineering-type). Per `README.md` (Chinese), the mandated workflow is to analyze those structures and rebuild the architecture under `development/skill/`. Target dev scenarios: Windows-native work (SQL databases, Access frontends, Access/Excel VBA), Android apps on Windows, and WSL Python filtering projects.

There is no application source, build system, or deployable runtime here — deliverables are Markdown skill modules plus stdlib-only Python helper scripts.

## Architecture & Data Flow

Two-layer design:

1. **Reference layer** — `references/`: three skill collections copied/built as analysis input. Read-only; do not modify.
2. **Development layer** — `development/skill/` (rebuild target, mirrors reference layout) and `development/docs/` (project docs incl. `architecture-ref/`).

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
- `references/cusomer-research-skills/recycling-company-investigation/` — self-built methodology-type skill (three-layer lifecycle bucketing).
- `references/access-vba-dev/` — self-built engineering-type skill (five-layer stack + repo meta layer).
- `development/skill/` — empty staging target for the rebuild.
- `development/docs/` — project documentation (`architecture-ref/` module reviews, this file, and [`plans/`](plans/) execution roadmap with `000-platform-skeleton.md` master plan).
- `.github/`, `.codex/` — exist but empty; purpose not yet defined.

## Code Conventions & Common Patterns

**SKILL.md format** (all English; only root README.md is Chinese):
- Frontmatter: exactly two fields, `name` and `description`; `name` must equal the directory slug. Description is one sentence ending with a "Use when …" trigger phrase for discovery matching.
- Body scales with complexity: minimal skills are frontmatter + prose bullets; larger ones use H1 title, numbered workflow steps, fenced ```bash command blocks, Stop Conditions, References.
- Orchestrator pattern: `code-review/SKILL.md` delegates to the `code-review-*` sub-modules.

**agents/openai.yaml**: single `interface:` mapping with `display_name`, `short_description`, `default_prompt`; `default_prompt` embeds the `$<skill-name>` trigger. Only for agent-facing entry skills.

**Python scripts** (stdlib only — zero third-party imports; external systems accessed via subprocess/MCP):
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
- Naming note: `cusomer-research-skills` contains a spelling slip (customer); fix before any global registry adopts it.

## Runtime/Tooling Preferences

- Python 3 (scripts assume ≥3.8 APIs; no version pin file exists). `gh` CLI required by the two scripted reference skills.
- No git history/config, no package manager, no formatter/linter config — do not introduce tooling speculatively; keep the repo minimal.
- Command paths inside reference SKILL.md files address the upstream Codex checkout (`.codex/skills/…`); substitute `references/SpineCodex-skills/` locally. Some referenced validation targets do not exist in this repo — they belong upstream.

## Testing & QA

- Framework: pytest — plain `test_*` functions, bare `assert`s, `monkeypatch`/`tmp_path` fixtures; no `unittest.TestCase`, no mock library.
- Tests are colocated: `scripts/test_<script_name>.py` beside the covered script, loaded via `importlib.util.spec_from_file_location(Path(__file__).with_name(...))` so they run from any cwd without package setup.
- Fixture style: helper factories returning sample payloads plus call-recording lists asserted after invocation.
- Scope: pure-function unit tests rather than subprocess integration; no coverage configuration or thresholds.
