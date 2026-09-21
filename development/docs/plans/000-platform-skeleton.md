# Skill Control Platform — 平台骨架计划

Status: executing
Date: 2026-08-25
Depends-on: none

> Status 生命周期：`draft → approved → executing → done`。被取代的计划保留状态 `superseded`，永不删除。Status 字段是本文件唯一事实源。

## §1 目标与定位

本项目的目的地不是重建示例技能，而是一个**技能控制平台**（skill control platform）：控制一个**可持续增长且不会随技能数量线性膨胀 Codex 初始技能上下文的技能集合**。三个参考库为它供给架构思想——SpineCodex 的成熟控制体系化为**生长机制**（生长单元、组合、负载控制、确定性下沉、增长门禁），recycling-company-investigation 化为**证据调查框架**，access-vba-dev 化为**运行时操作框架**；在此之上叠加控制层（注册表、校验、选择性发现、受管部署），使新领域以 **profile / adapter / module 接入**而非重写技能，并使 Codex 常态只看到一个轻量路由入口，具体 framework/worker 在命中后才按需加载。

边界约束：三个参考库本体不重建、不移动，保持 `references/` 只读；平台全部产出落在 `development/` 之下。本文件是骨架计划（master plan）；每个阶段执行前另立精细计划（见 §5），精细计划经用户批准后才可执行。

## §2 平台总览

目标布局：

```
development/
├── skill/                          # 平台技能源码库
│   ├── manifest.yaml               # 注册表 / 生命周期 / 部署角色
│   ├── global-skill-router/        # 唯一平台级 Codex 可见入口（P4）
│   │   ├── SKILL.md                # 薄路由合同：选场景 → 选模块 → 按需读取
│   │   └── agents/openai.yaml      # 顶层 discovery metadata
│   ├── research-investigation/     # 证据调查框架（P1；P4 部署为 router library module）
│   │   ├── SKILL.md
│   │   ├── references/
│   │   └── profiles/
│   └── runtime-ops/                # 运行时操作框架（P2；P4 部署为 router library module）
│       ├── SKILL.md
│       ├── references/
│       └── adapters/
├── tools/
│   ├── validate_skills.py          # 注册表、contract、route/deployment-role 校验
│   ├── deploy_skills.py            # P4：构建/更新/验证 routed deployment
│   └── run_tests.py                # repo-local pytest runner
└── docs/
    ├── plans/                      # 计划目录（本文件；NNN-<slug>.md）
    ├── architecture-ref/           # 架构依据（已有，只读）
    └── repo-conventions.md         # 展开约定（已有）
```

P4 的运行时安装形状与源码形状不同：`development/skill/` 继续保存完整、可独立测试的标准 Skill 源码；部署器只把 `global-skill-router` 暴露为 Codex 顶层 Skill，并把命中的 framework/worker 源码作为其私有 `library/` payload。嵌套 module 不依赖 Codex 将其再次注册为顶层 Skill，而由 router 按相对路径读取其 `SKILL.md`。

**Manifest 当前/目标模式** —— P3 已将注册表升级为 schema v2，顶层分离 `sources / skills / adapters`；只读 reference 不再占 Skill 身份，Skill lifecycle 为 `planned|active`，adapter 归 owner Skill。P4 在此基础上引入负载承重的 deployment-role contract，并将 manifest 版本演进为 v3：每个正式 Skill 额外声明 `deployment_role: router|module`。平台必须恰有一个 active router；active module 不直接安装到 Codex 顶层 discovery root，而由 router 的组合边和部署索引覆盖。`entrypoint` 继续表示逻辑上可被路由选择并具有 agent metadata，`deployment_role` 单独决定物理 catalog 暴露，二者不得混用。

**新技能接入流程**（生长回路）：draft `development/skill/<name>/` 按模块解剖实例化 → 在 manifest 登记 `planned` + scenario + deployment role → validator 通过 → 补全逻辑入口/组合边 → 置 `active` → deploy manager 构建 routed payload → 验证只有 router 进入平台管理的顶层 Codex catalog、module 位于 router 私有 library。复合技能额外登记 `composed_of[]`；新增 module 不得通过“直接复制到 `~/.codex/skills/<name>`”绕过选择性发现层。

## §3 平台化与泛化映射

### §3.1 SpineCodex 控制组件的平台化（生长机制）

来自 14 技能集合的成熟实践 + 其缺失项的补齐：

| SpineCodex 组件 | 平台化机制 | 落点 |
|---|---|---|
| 模块解剖（SKILL.md 必备 + 可选 agents/scripts/references） | 生长单元：新技能必须按解剖实例化，校验器强制不变量 | validate_skills.py + manifest |
| 三层渐进披露（frontmatter 路由 → 正文 → references） | 负载控制：正文千字节级、深度下沉，集合增长时单技能上下文预算有界 | AGENTS.md Core Rule 4 + 校验 |
| 编排者薄壳（code-review → 四个子技能分发） | 组合机制：复合技能仅做路由；manifest 记录组合边 | manifest `composed_of[]` 字段 |
| 脚本动作契约（gh 子进程 → 结构化 actions 建议） | 确定性下沉：助手脚本 stdlib-first（第三方导入须已声明）+ JSON 动作契约 + 同置 pytest | repo-conventions + 校验测试存在性 |
| "Use when" 触发句式 + openai.yaml 接口元数据 | 路由面：触发短语强制、agent 入口判定（与有无脚本无关） | 校验器 frontmatter 检查 |
| 缺失项：注册表、一致性校验、版本（name 脱钩 bug、仅脚本内 SCRIPT_VERSION） | 增长门禁：注册 + 校验绿 + status/version 字段才可 active | manifest.yaml + validate_skills.py |

### §3.2 研究框架泛化（自 recycling-company-investigation）

| 层 | 内容 | 去向 |
|---|---|---|
| 核心 | evidence-first 调查控制面：discovery ≠ evidence、四态 confirmed/inferred/unknown/conflicting、冲突保留、覆盖缺口可见、人工复核终态 | SKILL.md + references/evidence-rules |
| 核心 | 来源层级 + subject/claim matching + bounded discovery + language-gap 纪律 | references/evidence-taxonomy |
| 核心 | profile-neutral review packet + canonical candidate 边界；无 caller-supplied canonical source 时不发明 ID | references/output-schema |
| 核心 | 通用调查生命周期；Core 不固定公司运营 lanes、`input→operation→output` 或 Acquisition→Source→Signal→Fact→Score 五段拓扑 | SKILL.md |
| 扩展合同 | versioned Profile Contract：subject type、investigation dimensions、vocabulary、packet extension、可选 pipeline/project binding 与缺失语义 | references/profile-contract |
| 领域适配 | 检索词表、具体 research dimensions、领域 relevance/domain model 等实例语义 | profiles/<domain>.yaml |
| 项目绑定 | 外部 schema/config/source identifiers 仅作为 consuming-project-owned 可选 binding；standalone 缺失时降级为 review_packet_only | profiles/<domain>.yaml |
| 首个适配 | profiles/recycling-company.yaml 保留原调查能力，但不作为 Core 定义来源 | P1 fidelity + orthogonality 验收 |

### §3.3 运行时操作框架泛化（自 access-vba-dev）

| 层 | 内容 | 去向 |
|---|---|---|
| 核心 | capability-before-action、真实 failure/status 保真、observation/mutation/verification 分离 | SKILL.md |
| 核心 | adapter-defined verification model；Core 只强制证据不可越级，允许 linear / partial-order / independent-checks，不固定 Static<Compile<Runtime | references/verification-ladder |
| 核心 | recoverability requirement + stop conditions；恢复机制由 adapter 声明，不固定文件 backup 目录 | SKILL.md + references/contract-template |
| 核心 | 证据五类型 + 源优先级 + 知识准入门槛（"会改变 agent 决策才加入"） | references/evidence-types |
| 核心 | 配置由 agent 显式注入工具调用；具体 casing/default 属 adapter，工具不自动读取 skill 文件 | SKILL.md |
| 扩展合同 | Adapter Contract：identity/version、capabilities、operations/signatures、preconditions/failures、mutation、verification、recovery、environment、可选 task routing、provenance | references/contract-template |
| 首个适配 | vba-office 实例承载 Diagnose/Review/Modify/Test、Static→Compile→Runtime、vba-doctor/vba-lint、Office fixture 与文件备份策略；运行时语义必须自足，参考库只作 provenance | adapters/vba-office.md |
| 预留适配 | sql-server / android-gradle / wsl-python（manifest 标 planned，不实现） | §4 P3 |

### §3.4 选择性发现与受管部署层（P4）

| 问题 | 平台机制 | 落点 |
|---|---|---|
| Codex 会把顶层 Skill catalog 的 name/description 暴露给模型并受 context budget 约束 | 单一平台入口：只把 `global-skill-router` 安装为本平台顶层 Skill | `development/skill/global-skill-router/` + deploy manager |
| 技能数量增长会使直接安装模式的初始 discovery 面扩大 | 物理 catalog 与逻辑 registry 分离：framework/worker 保持标准 Skill 源码，但部署为 router 私有 module | manifest v3 `deployment_role` |
| Router 若扫描全部 module，同样会把增长成本转移到每次任务 | 分层路由索引：先读固定小型 scenario index，只在命中后读对应 route shard，再读取所选 module `MODULE.md` | deploy-generated routing index |
| Codex 没有要求嵌套 module 必须再次注册成原生 Skill | Router 通过相对路径加载部署后的 module `MODULE.md`；module 仍复用原有 profile/adapter progressive disclosure | router contract + private `library/` |
| 手工复制无法可靠更新、验证或回滚 | repo-owned deploy manager：validate → build staging payload → diff/plan → atomic-ish replace with recovery → verify/drift report | `development/tools/deploy_skills.py` |
| 新增大量 module 后是否真的不增加顶层技能负载缺少证据 | 结构回归 + Alpha 黑盒测试：增加 synthetic modules 后平台管理的顶层 Skill 数仍为 1，未命中 module 不被读取 | P4 tests + live smoke |

P4 的关键区分是：**逻辑 Skill 数量可以增长，Codex 顶层可见 Skill 数量不随之增长**。这不是把所有内容塞进一个巨型 SKILL.md；router 必须保持薄，路由元数据按场景分片，module 正文和深层 references 仍在命中后才加载。

## §4 阶段划分

### P0 平台地基

- **目标**：建立平台控制地基——技能注册表与校验器，使增长回路（§2 接入流程）可执行。
- **产出**：
  - `development/skill/manifest.yaml`：条目含 3 个 external 参考库 + 2 个 planned 平台技能；模式携带 `version` 与 `composed_of[]` 字段。
  - `development/tools/validate_skills.py`：Python 校验器（遵循 repo 脚本约定：argparse、违规 exit 1），声明依赖 PyYAML（Core Rule 5 修订后为允许已声明第三方导入的 stdlib-first 约定）；检查项 = frontmatter 存在、name==dirname、description 含 "Use when"、path 存在按 status 分层检查（external/active 必须，planned 可预登记缺席）、每个 development 技能均有 manifest 条目——检查矩阵与分层语义定稿以 `010-p0-foundation.md` 为准。
- **验收标准**：校验器对当时树 exit 0；以临时植入的坏 fixture 演示 exit 1 后删除；§2 接入流程成为文档化的唯一接入路径。
- **依赖**：无。

### P1 研究框架泛化

- **目标**：按 §3.2 表构建 evidence-first 外部实体/设施/组织/项目调查框架 `research-investigation/`；Core 只保留证据调查纪律，领域问题模型由 profile 定义，消费项目接口由可选 binding 定义。
- **产出**：SKILL.md（Contract、通用调查生命周期、profile/output 边界）+ references/（evidence-rules、output-schema、evidence-taxonomy、profile-contract）+ `profiles/recycling-company.yaml`。
- **验收标准**：Core 零 recycling/customer_screening 专有语义；recycling profile 保留原 skill 的有效调查能力；缺少 consuming-project binding 时仍可完整降级为 review packet；用一个异质 synthetic profile 证明无需改 Core 即可替换 investigation dimensions/pipeline；profile contract 具备可机械校验语义，active 前相应 gate 必须存在；正文英文、千字节级。
- **依赖**：P0。

### P2 运行时操作框架泛化

- **目标**：按 §3.3 表构建宿主中立运行时操作框架 `runtime-ops/`；Core 只定义 capability、failure preservation、verification honesty、recoverability 与证据纪律，宿主/工具形状由 adapter 实例化。
- **产出**：SKILL.md（Core contract + generic operation lifecycle）+ references/（verification-ladder 作为 Verification Model Contract、contract-template 作为 Adapter Contract、evidence-types）+ `adapters/vba-office.md`（自足承载 VBA/Office 具体合同与恢复/验证实例）。
- **验收标准**：vba-office 与 access-vba-dev 的承重语义一致且部署时不依赖参考库全文；Static/Compile/Runtime、四任务模式与文件 backup 不进入 Core；用一个非线性验证 + transaction rollback 的 synthetic adapter 证明无需改 Core 即可接入；adapter contract 具备可机械校验语义，active 前相应 gate 必须存在；只报告实际证据达到的 verification state。
- **依赖**：P0；与 P1 相互独立。

### P3 控制集成

- **目标**：全平台控制闭环——注册表覆盖一切、路由完备、生命周期门禁生效。
- **产出**：manifest 覆盖全部条目含 planned adapters；scenario 路由表（3 场景 × 技能）；编排者技能的组合边登记；生命周期门禁（`planned → active` 仅在校验器绿后）；部署约定章节（`development/skill/<name>/` 如何映射进运行环境且路径自引用保持）；AGENTS.md Documentation Map 补 plans/ 行（若此前未加）。
- **验收标准**：校验器对完整注册表绿；路由表完备；用一个一次性技能端到端演示增长回路（register → validate → route → 验证后移除）。
- **依赖**：P1 + P2。

### P4 选择性发现与受管部署

- **目标**：把 P3 的逻辑控制面转成可实际安装的低负载运行时拓扑：Codex 常态只发现一个平台 router；active framework/worker 作为 router 私有 module 按需加载；更新由 repo-owned deploy manager 完成。
- **产出**：`global-skill-router` 薄入口；manifest v3 deployment-role contract；分层 route index 生成规则；`deploy_skills.py` 的 dry-run/apply/verify/rollback-or-auto-recovery；routed payload 布局与 deployment state/hash；结构与黑盒 Alpha 测试。
- **验收标准**：平台管理的用户级 Codex 顶层目录只有 router；`research-investigation`、`runtime-ops` 可由 router 正确按需选择但不作为顶层 Skill 暴露；未命中 module 不读取；增加大量 synthetic module 不增加平台顶层 Skill 数，固定入口正文不随 module 数膨胀；重复部署可无损更新并能检测 drift/失败后恢复；旧 `vba-skill` 与项目级 recycling skill 在 Alpha 期间不被删除或覆盖。
- **依赖**：P3。
- **精细计划**：`050-p4-selective-discovery-deployment.md`。

每阶段执行前先立各自的精细计划文件（见 §5）。

## §5 计划文件约定

命名 `NNN-<slug>.md`，编号按十步进（000, 010, 020 …），插入新计划不重排既有编号；头部使用与本文件相同的 Status 块。一个阶段 = 一份精细计划（如 `010-p0-foundation.md`）。审阅工作流：用户在 `development/docs/plans/` 目录内审阅，Status 字段是唯一事实源。

## §6 与现有文档的关系

四个文档面各司其职：`architecture-ref/` 是 **why**（架构依据，已冻结只读）；`repo-conventions.md` 是 **what**（展开约定）；根 `AGENTS.md` 是**绑定约束**；`plans/` 是**执行路线图**——本文件为主计划（master），各阶段精细计划为其子计划。
