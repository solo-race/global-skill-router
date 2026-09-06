# Repository Guidelines

## Purpose

Build a global SKILL system for the local Codex development environment ("Global Skill 结构构建"). Mandated workflow: analyze the reference skill libraries under `references/`, then rebuild the architecture under `development/skill/`. Target scenarios: Windows-native (SQL/Access/VBA), Android on Windows, WSL Python filtering.

Deliverables are Markdown skill modules plus Python helper scripts (prefer stdlib-only; third-party imports only where declared, per Core Rule 5) — no application runtime, no build system.

## Required Reading

Always apply this file. Read further documentation only when relevant:

- Adding or changing skills → module reviews in [`development/docs/architecture-ref/`](development/docs/architecture-ref/README.md) (index maps each architecture concern to a doc).
- Repo layout, script style, testing detail → [`development/docs/repo-conventions.md`](development/docs/repo-conventions.md).

Do not load all documentation by default.

## Core Rules

1. Treat everything under `references/` as read-only analysis input. Never modify it.
2. New skills go under `development/skill/<kebab-case-name>/`. Mandatory `SKILL.md` with YAML frontmatter: `name` == directory slug; `description` ends with a "Use when …" trigger phrase.
3. All paths inside a skill resolve against the skill's own directory. Never hardcode deployment paths (`.codex/skills/…`).
4. SKILL.md bodies are English, kilobyte-scale; deep material goes into the skill's own `references/`.
5. Helper scripts are Python 3 with colocated pytest suites (`test_<name>.py`). Prefer stdlib-only; any third-party import must be declared here or in `development/docs/repo-conventions.md`. Declared dependency: PyYAML (`development/tools/validate_skills.py` and `development/tools/deploy_skills.py`).
6. High-blast-radius automation (database writes, VBA project changes) must carry Contract / Stop Conditions / backup-rollback conventions.
7. Do not introduce tooling speculatively — no build systems, linters, or CI unless required.
8. Before adding material anywhere ask: will this change an agent's decision? If not, leave it out.

## Commands

```bash
py -3 development/tools/run_tests.py [pytest args...]   # run tests
py -3 development/tools/deploy_skills.py [--target-root PATH]          # read-only deployment plan
py -3 development/tools/deploy_skills.py --verify [--target-root PATH]  # verify managed payload
```

## Documentation Map

| Doc | Responsibility |
|-----|----------------|
| [`architecture-ref/README.md`](development/docs/architecture-ref/README.md) | Index of three architecture reviews split into 7 concern modules |
| [`repo-conventions.md`](development/docs/repo-conventions.md) | Expanded repo conventions moved out of this file |
| [`plans/`](development/docs/plans/000-platform-skeleton.md) | Execution roadmap: platform skeleton + per-phase plans |
| [`scenario-routing.md`](development/docs/scenario-routing.md) | Derived scenario route projection; manifest remains authoritative |
