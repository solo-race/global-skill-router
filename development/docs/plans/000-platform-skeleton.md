# Skill Control Platform — 平台骨架计划

Status: draft
Date: 2026-08-25
Depends-on: none

> Status 生命周期：`draft → approved → executing → done`。被取代的计划保留状态 `superseded`，永不删除。Status 字段是本文件唯一事实源。

## §1 目标与定位

本项目的目的地不是重建示例技能，而是一个**技能控制平台**（skill control platform）：控制一个**可持续增长的技能集合**。三个参考库为它供给架构思想——SpineCodex 的成熟控制体系化为**生长机制**（生长单元、组合、负载控制、确定性下沉、增长门禁），recycling-company-investigation 化为**研究方法论框架**，access-vba-dev 化为**运行时操作框架**；在此之上叠加控制层（注册表、校验、部署约定），使新领域以**适配器接入**而非重写技能。

边界约束：三个参考库本体不重建、不移动，保持 `references/` 只读；平台全部产出落在 `development/` 之下。本文件是骨架计划（master plan）；每个阶段执行前另立精细计划（见 §5），精细计划经用户批准后才可执行。

## §2 平台总览

目标布局：

```
development/
├── skill/                          # 平台技能库（重建目标）
│   ├── manifest.yaml               # 技能注册表（P0）
│   ├── research-investigation/     # 泛化研究框架（P1）
│   │   ├── SKILL.md                # 领域中立方法论入口
│   │   ├── references/             # evidence-rules / output-schema / evidence-taxonomy
│   │   └── profiles/               # <domain>.yaml 领域适配
│   └── runtime-ops/                # 泛化运行时操作框架（P2）
│       ├── SKILL.md                # 验证阶梯 + 证据类型 + 合同模板入口
│       ├── references/             # contract-template / verification-ladder / evidence-types
│       └── adapters/               # <host>.md 宿主适配
├── tools/
│   └── validate_skills.py          # 注册表与 frontmatter 校验（P0）
└── docs/
    ├── plans/                      # 计划目录（本文件；NNN-<slug>.md）
    ├── architecture-ref/           # 架构依据（已有，只读）
    └── repo-conventions.md         # 展开约定（已有）
```

**Manifest 模式草图** —— 注册表每条目字段：`name / path / status(active|planned|external) / scenarios[win-access-vba|win-android|wsl-python] / deps[] / description`，并携带 `version` 与 `composed_of[]` 字段。`external` 条目覆盖三个参考库（只读登记）。模式在 P0 精细计划中定稿，此处仅为契约轮廓。manifest 位于 `development/skill/manifest.yaml`，描述它所在的技能库本身。

**新技能接入流程**（生长回路，P0 起生效）：draft `development/skill/<name>/` 按模块解剖实例化 → 在 `manifest.yaml` 登记为 `status: planned` → `validate_skills.py` 通过（frontmatter 存在、name==dirname、description 含 "Use when"、与 manifest 一致）→ 补全 scenario 映射 → 置 `status: active`。复合技能额外登记 `composed_of[]` 组合边。注册表 + 校验状态 = 平台对技能集合的完整视图；这是 SpineCodex 所缺、由平台补齐的增长门禁。

## §3 平台化与泛化映射

### §3.1 SpineCodex 控制组件的平台化（生长机制）

来自 14 技能集合的成熟实践 + 其缺失项的补齐：

| SpineCodex 组件 | 平台化机制 | 落点 |
|---|---|---|
| 模块解剖（SKILL.md 必备 + 可选 agents/scripts/references） | 生长单元：新技能必须按解剖实例化，校验器强制不变量 | validate_skills.py + manifest |
| 三层渐进披露（frontmatter 路由 → 正文 → references） | 负载控制：正文千字节级、深度下沉，集合增长时单技能上下文预算有界 | AGENTS.md Core Rule 4 + 校验 |
| 编排者薄壳（code-review → 四个子技能分发） | 组合机制：复合技能仅做路由；manifest 记录组合边 | manifest `composed_of[]` 字段 |
| 脚本动作契约（gh 子进程 → 结构化 actions 建议） | 确定性下沉：助手脚本 stdlib-only + JSON 动作契约 + 同置 pytest | repo-conventions + 校验测试存在性 |
| "Use when" 触发句式 + openai.yaml 接口元数据 | 路由面：触发短语强制、agent 入口判定（与有无脚本无关） | 校验器 frontmatter 检查 |
| 缺失项：注册表、一致性校验、版本（name 脱钩 bug、仅脚本内 SCRIPT_VERSION） | 增长门禁：注册 + 校验绿 + status/version 字段才可 active | manifest.yaml + validate_skills.py |

### §3.2 研究框架泛化（自 recycling-company-investigation）

| 层 | 内容 | 去向 |
|---|---|---|
| 核心 | 流水线段位模型 Acquisition→Source→Signal→Fact→Score（段名可配置） | SKILL.md |
| 核心 | 证据四态 confirmed/inferred/unknown/conflicting + 判定规则 | references/evidence-rules |
| 核心 | 来源层级 + 实体匹配规则 | references/evidence-taxonomy |
| 核心 | 证据标注的输出 schema 模式 | references/output-schema |
| 核心 | Contract 红线清单模式 + 人工复核强制终态 + manual_review_reasons 覆盖缺口可见 | SKILL.md |
| 核心 | 7 步工作流骨架 + research lanes 并行纪律 | SKILL.md |
| 适配 | 检索词表/分类学、实体类型定义（company→泛化 entity）、评分规则、外部 schema/config 引用落地 | profiles/<domain>.yaml |
| 首个适配 | profiles/recycling-company.yaml 复现原筛查行为 | P1 验收 |

### §3.3 运行时操作框架泛化（自 access-vba-dev）

| 层 | 内容 | 去向 |
|---|---|---|
| 核心 | 验证阶梯 Static<Compile<Runtime + "只报实际达到的最高档" + 宿主不对称声明方式 | references/verification-ladder |
| 核心 | 工具合同模板：工具名/签名/默认值/返回形态/失败语义/每宿主执行路径 六要素 | references/contract-template |
| 核心 | 证据五类型 + 源优先级 + 知识准入门槛（"会改变 agent 决策才加入"） | references/evidence-types |
| 核心 | profile 中介配置注入（agent 将 profile 值抄入工具调用，工具不自动读取） | SKILL.md |
| 核心 | 规范化备份/回滚命名约定 + 受控 fixture 本地资产政策 | references/contract-template |
| 适配 | vba-doctor/vba-lint 具体合同实例（内联要点 + 链接 references/access-vba-dev 全文） | adapters/vba-office.md |
| 预留适配 | sql-server / android-gradle / wsl-python（manifest 标 planned，不实现） | §4 P3 |

## §4 阶段划分

### P0 平台地基

- **目标**：建立平台控制地基——技能注册表与校验器，使增长回路（§2 接入流程）可执行。
- **产出**：
  - `development/skill/manifest.yaml`：条目含 3 个 external 参考库 + 2 个 planned 平台技能；模式携带 `version` 与 `composed_of[]` 字段。
  - `development/tools/validate_skills.py`：stdlib-only Python（遵循 repo 脚本约定：argparse、违规 exit 1）；检查项 = frontmatter 存在、name==dirname、description 含 "Use when"、manifest 路径存在、每个 development 技能均有 manifest 条目。
- **验收标准**：校验器对当时树 exit 0；以临时植入的坏 fixture 演示 exit 1 后删除；§2 接入流程成为文档化的唯一接入路径。
- **依赖**：无。

### P1 研究框架泛化

- **目标**：按 §3.2 表构建领域中立研究方法论框架 `research-investigation/`。
- **产出**：SKILL.md（流水线段位模型、Contract 红线、7 步工作流）+ references/（evidence-rules、output-schema、evidence-taxonomy）+ `profiles/recycling-company.yaml`。
- **验收标准**：框架 SKILL.md + references 零 recycling 专有词；`profiles/recycling-company.yaml` + 核心复现原技能指令（随附 mapping spot-check 表）；frontmatter 过校验器；正文英文、千字节级。
- **依赖**：P0。

### P2 运行时操作框架泛化

- **目标**：按 §3.3 表构建通用运行时操作框架 `runtime-ops/`。
- **产出**：SKILL.md（验证阶梯、证据类型、合同模板入口）+ references/（verification-ladder、contract-template、evidence-types）+ `adapters/vba-office.md`（记录到 `references/access-vba-dev/tool-contracts/` 的映射）。
- **验收标准**：VBA 合同模板实例在六要素上与 access-vba-dev 语义一致；阶梯规则逐字兼容（"Never report a higher level than was actually achieved"）；校验器绿。
- **依赖**：P0；与 P1 相互独立。

### P3 控制集成

- **目标**：全平台控制闭环——注册表覆盖一切、路由完备、生命周期门禁生效。
- **产出**：manifest 覆盖全部条目含 planned adapters；scenario 路由表（3 场景 × 技能）；编排者技能的组合边登记；生命周期门禁（`planned → active` 仅在校验器绿后）；部署约定章节（`development/skill/<name>/` 如何映射进运行环境且路径自引用保持）；AGENTS.md Documentation Map 补 plans/ 行（若此前未加）。
- **验收标准**：校验器对完整注册表绿；路由表完备；用一个一次性技能端到端演示增长回路（register → validate → route → 验证后移除）。
- **依赖**：P1 + P2。

每阶段执行前先立各自的精细计划文件（见 §5）。

## §5 计划文件约定

命名 `NNN-<slug>.md`，编号按十步进（000, 010, 020 …），插入新计划不重排既有编号；头部使用与本文件相同的 Status 块。一个阶段 = 一份精细计划（如 `010-p0-foundation.md`）。审阅工作流：用户在 `development/docs/plans/` 目录内审阅，Status 字段是唯一事实源。

## §6 与现有文档的关系

四个文档面各司其职：`architecture-ref/` 是 **why**（架构依据，已冻结只读）；`repo-conventions.md` 是 **what**（展开约定）；根 `AGENTS.md` 是**绑定约束**；`plans/` 是**执行路线图**——本文件为主计划（master），各阶段精细计划为其子计划。
