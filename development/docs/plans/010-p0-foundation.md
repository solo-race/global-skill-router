# P0 平台地基 — 精细实施计划

Status: done
Date: 2026-08-25
Depends-on: 000-platform-skeleton

> Status 生命周期：`draft → approved → executing → done`。被取代的计划保留状态 `superseded`，永不删除。Status 字段是本文件唯一事实源。

## §1 目标与产出

目标：建立平台控制地基——技能注册表与校验器，使 000 §2 的接入流程（growth loop）可执行。产出三件：

1. `development/skill/manifest.yaml` —— 注册表，5 条目（3 external + 2 planned），模式携带 `version` 与 `composed_of[]`。
2. `development/tools/validate_skills.py` —— stdlib-first 校验器（声明依赖 PyYAML）。
3. `development/tools/test_validate_skills.py` —— 同置 pytest 套件。

非目标：不构建两个平台技能本体（P1/P2 范围）；不改任何参考库。

## §2 `manifest.yaml` 定稿

存储格式 YAML、解析用 PyYAML——经用户确认（备选 JSON / 自写迷你解析器已否决）；Core Rule 5 的同步修订文本见 §6，随校验器代码同一变更落盘。

### (a) 完整文件内容

逐字如下，实施时原样写入 `development/skill/manifest.yaml`：

```yaml
schema_version: 1
skills:
  - name: SpineCodex-skills
    path: references/SpineCodex-skills
    status: external
    scenarios: [win-access-vba, win-android, wsl-python]
    deps: []
    composed_of: []
    version: "2026-08-25"
    description: Upstream 14-skill control architecture library; read-only analysis input.
  - name: recycling-company-investigation
    path: references/customer-research-skills/recycling-company-investigation
    status: external
    scenarios: [wsl-python]
    deps: []
    composed_of: []
    version: "2026-08-25"
    description: Self-built methodology-type research screening skill; read-only analysis input.
  - name: access-vba-dev
    path: references/access-vba-dev
    status: external
    scenarios: [win-access-vba]
    deps: []
    composed_of: []
    version: "2026-08-25"
    description: Self-built engineering-type VBA runtime-operations skill; read-only analysis input.
  - name: research-investigation
    path: development/skill/research-investigation
    status: planned
    scenarios: []
    deps: []
    composed_of: []
    version: "0.1.0"
    description: Domain-neutral research investigation framework (built in P1).
  - name: runtime-ops
    path: development/skill/runtime-ops
    status: planned
    scenarios: []
    deps: []
    composed_of: []
    version: "0.1.0"
    description: Universal runtime operations framework (built in P2).
```

### (b) 字段语义表

| 字段 | 类型 | 语义 |
|---|---|---|
| `name` | string | 全局唯一 slug |
| `path` | string | 相对仓库根 |
| `status` | enum | ∈ `external \| planned \| active` |
| `scenarios` | string[] | ⊆ {`win-access-vba`, `win-android`, `wsl-python`} |
| `deps` | string[] | 运行时依赖技能名 |
| `composed_of` | string[] | 组合边（子技能名） |
| `version` | string | 非空字符串（external 用快照日期，平台技能用 semver） |
| `description` | string | 一句话 |

### (c) status 分层检查语义表

解决 000 内在张力：000 写 "manifest paths exist"，但其 P0 验收要求校验器对当时树 exit 0，而两个 planned 技能目录尚不存在。定稿语义（依据 000 §2 接入流程的 forward registration）：

| 检查 | external | planned | active |
|---|---|---|---|
| path 存在 | 必须 | 可缺席（预登记） | 必须 |
| SKILL.md 存在 | 不适用 | 可缺席 | 必须 |
| frontmatter 检查 F1–F3 | 不适用 | 仅当 SKILL.md 存在时执行 | 必须 |

## §3 `validate_skills.py` 规格

**CLI 契约**：`py development/tools/validate_skills.py [--manifest PATH]`。默认 manifest = `<repo-root>/development/skill/manifest.yaml`；repo root = `Path(__file__).resolve().parents[2]`。退出码：0 全绿；存在违规 → 1；KeyboardInterrupt → 130；argparse 用法错误 → 2（argparse 默认）。

**输出契约**（遵循 repo-conventions 脚本约定）：stdout 单一 JSON 文档 `json.dumps(report, indent=2, sort_keys=True)`，形如 `{"ok": bool, "manifest": "<path>", "skills_checked": <int>, "errors": [{"code", "skill", "message"}]}`；stderr 每违规一行 `CODE skill: message`。

**检查矩阵**（编号即错误码基，全部稳定字面量）：

| # | 检查 | 错误码 |
|---|---|---|
| E1 | manifest 存在且可被 PyYAML 解析为映射 | `MANIFEST_NOT_FOUND` / `MANIFEST_PARSE_ERROR` |
| E2 | `schema_version == 1` | `SCHEMA_VERSION_UNSUPPORTED` |
| E3 | name 全局唯一 | `DUPLICATE_NAME` |
| E4 | 必填字段非空：name/path/status/version/description；scenarios/deps/composed_of 缺省为 `[]` | `MISSING_FIELD` |
| E5 | status ∈ {external, planned, active} | `INVALID_STATUS` |
| E6 | scenarios 每值 ∈ {win-access-vba, win-android, wsl-python} | `INVALID_SCENARIO` |
| E7 | composed_of 引用解析到同 manifest 条目名 | `COMPOSED_OF_UNKNOWN_REF` |
| E8 | external 条目 path 存在 | `EXTERNAL_PATH_MISSING` |
| E9 | planned 条目按 §2(c) 分层；目录与 SKILL.md 在则执行 F1–F3 | （沿用分层对应码） |
| E10 | active 条目：path 存在；SKILL.md 存在；执行 F1–F3；scenarios 非空 | `ACTIVE_PATH_MISSING` / `ACTIVE_SKILL_MD_MISSING` / `ACTIVE_EMPTY_SCENARIOS` |
| F1 | SKILL.md 含 `---` 围栏 frontmatter | `FRONTMATTER_MISSING` |
| F2 | frontmatter `name` == 条目 `name` == 目录 basename | `NAME_MISMATCH` |
| F3 | frontmatter `description` 含 "Use when" | `DESCRIPTION_NO_TRIGGER` |
| U1 | `development/skill/` 每个直接子目录均有条目 | `UNREGISTERED_SKILL` |

**实现约定**（引用 repo-conventions Code Conventions）：shebang `#!/usr/bin/env python3`；模块 docstring 内声明依赖 PyYAML；无类型注解；`parse_args()` 建 argparse；常量 SCREAMING_SNAKE 置顶；`def main()` + `if __name__ == "__main__": raise SystemExit(main())` 收尾。frontmatter 解析只取 `---` 围栏内的平铺 `key: value` 行（repo 约定恰好两字段 name/description），用 PyYAML safe_load 该围栏内容。

## §4 测试规格

`development/tools/test_validate_skills.py`，遵循 repo-conventions Testing & QA：pytest 纯函数、裸 assert、`tmp_path` fixture、`importlib.util.spec_from_file_location(Path(__file__).with_name("validate_skills.py"))` 导入被测模块。14 个测试，各自断言的错误码写在括号内：

1. `test_green_tree_passes` — external + planned(目录缺席) + active(合法 SKILL.md) → ok=True, errors=[]
2. `test_planned_forward_registration_without_dir_ok` — planned 无目录无 SKILL.md → 全绿
3. `test_planned_with_skill_md_checked`（NAME_MISMATCH）— planned 且带错名 SKILL.md → F2 生效
4. `test_active_requires_skill_md`（ACTIVE_SKILL_MD_MISSING）
5. `test_active_empty_scenarios_rejected`（ACTIVE_EMPTY_SCENARIOS）
6. `test_external_missing_path_detected`（EXTERNAL_PATH_MISSING）
7. `test_name_mismatch_detected`（NAME_MISMATCH）
8. `test_missing_use_when_detected`（DESCRIPTION_NO_TRIGGER）
9. `test_missing_frontmatter_detected`（FRONTMATTER_MISSING）
10. `test_unregistered_dir_detected`（UNREGISTERED_SKILL）
11. `test_duplicate_names_rejected`（DUPLICATE_NAME）
12. `test_unknown_composed_of_ref_rejected`（COMPOSED_OF_UNKNOWN_REF）
13. `test_invalid_scenario_value_rejected`（INVALID_SCENARIO）
14. `test_report_shape_and_exit_code` — 直接调 `main()`（patched argv），验证 stdout JSON 形状与退出码 0/1

fixture 工厂风格：helper 函数在 `tmp_path` 下生成假树（写 manifest + SKILL.md），返回 manifest 路径供调用。

## §5 验收运行手册

对应 000 P0 验收标准三条：

0. 前置：`py -m pip install pytest pyyaml`（本机 pyyaml 6.0.3 已装，pytest 缺）。
1. `py development/tools/validate_skills.py` → exit 0；stdout `ok: true`，`skills_checked: 5`。（验收①：当时树全绿）
2. 植入探针 A：建 `development/skill/tmp-probe/`（含任意 SKILL.md，不登记）→ 运行 → exit 1，errors 含 `UNREGISTERED_SKILL tmp-probe`。（演示未注册门禁）
3. 探针 B：把 tmp-probe 登记进 manifest 为 `planned`，其 SKILL.md frontmatter `name: wrong-name` → 运行 → exit 1 且新增 `NAME_MISMATCH wrong-name`（E9 分层检查生效）。随后删除探针目录与其 manifest 条目 → 重跑 exit 0。（验收②：坏 fixture 演示 exit 1 后移除）
4. `py -m pytest development/tools/test_validate_skills.py` 全绿。
5. 接入路径文档化：指向 000 §2 新技能接入流程（验收③已由 000 满足，此处仅引用）。

## §6 文档同步

P0 实施时与校验器代码同一变更落盘；本计划先定稿文本。三处逐字修订：

1. **AGENTS.md Core Rule 5 整行替换为**：

```
5. Helper scripts are Python 3 with colocated pytest suites (`test_<name>.py`). Prefer stdlib-only; any third-party import must be declared here or in `development/docs/repo-conventions.md`. Declared dependencies: PyYAML (`development/tools/validate_skills.py`).
```

2. **`development/docs/repo-conventions.md` Code Conventions 段首粗体句替换为**：

```
**Python scripts** (stdlib-first — third-party imports only where declared in AGENTS.md Core Rule 5; external systems accessed via subprocess/MCP):
```

3. **同文件 Runtime/Tooling Preferences 首条 bullet（Python 3 行）末尾追加**：

```
; declared third-party dependency: PyYAML (YAML parsing for tools/validate_skills.py)
```
