# P2 运行时操作框架泛化 — 精细实施计划

Status: done
Date: 2026-08-25
Depends-on: 000-platform-skeleton, 010-p0-foundation

> Status 生命周期：`draft → approved → executing → done`。被取代的计划保留状态 `superseded`，永不删除。Status 字段是本文件唯一事实源。

## §1 目标、抽象边界与产出

目标：从 `references/access-vba-dev/` 提取可跨宿主迁移的**运行时操作控制面**，重建为 `development/skill/runtime-ops/`。本阶段不把 Access/VBA 的任务分类、Office 工具拓扑、`Static < Compile < Runtime` 三档、文件备份命名或 fixture 形状提升为通用本体；这些仅作为 `vba-office` adapter 的首个实例。

框架职责是回答五类问题：当前 adapter 实际声明了什么 capability、什么没有；操作调用前有什么 precondition、失败语义如何保真；mutation 如何保持可恢复、何时必须停止；一个“验证完成”的声明需要什么证据、哪些证据不能互相替代；宿主与工具差异如何留在 adapter 内而不迫使修改 Core。

目标结构：

```text
Runtime Operations Core
  ├─ capability-before-action
  ├─ evidence honesty / failure preservation
  ├─ mutation safety / stop conditions / recoverability requirement
  ├─ adapter-defined verification semantics
  └─ knowledge evidence classification
        ↓
Adapter Contract
  ├─ identity/version/source-of-truth
  ├─ capabilities & operations
  ├─ preconditions/failures
  ├─ verification model
  ├─ recovery model
  ├─ environment requirements
  └─ optional task routing
        ↓
Host/Tool Adapter
  └─ vba-office.md: vba-doctor + vba-lint + Office-specific rules
```

计划产出：

1. `development/skill/runtime-ops/SKILL.md` —— Core 控制原则、adapter 加载流程、通用操作生命周期、报告纪律。
2. `development/skill/runtime-ops/references/verification-ladder.md` —— 文件名沿用主计划，但内容改为 adapter-defined verification model contract，不再把三档写成全局本体。
3. `development/skill/runtime-ops/references/contract-template.md` —— adapter contract 的稳定接口，包括 capability、failure、verification、recovery、environment。
4. `development/skill/runtime-ops/references/evidence-types.md` —— 五类知识证据、来源优先级、准入门槛。
5. `development/skill/runtime-ops/adapters/vba-office.md` —— 首个正式实例：在 adapter 内实例化 Diagnose/Review/Modify/Test、Static/Compile/Runtime、vba-doctor/vba-lint、Office fixture 与文件备份恢复策略。

非目标：不提前实现 sql-server/android-gradle/wsl-python 正式 adapter；不复制外部 MCP server 实现；不把参考库路径作为部署后的 runtime dependency；不建立通用构建系统或运行器；本计划修改本身不实施任何 runtime-ops 功能。

本阶段的关键验收不是“VBA adapter 与原 skill 一致”本身，而是：一个验证模型、恢复模型和任务分类明显不同的 synthetic adapter，是否仍能在不修改 Core 的情况下接入。

## §2 抽象原则 R1–R8

### R1 — 通用的是能力必须由合同声明，不是具体工具名

Core 固定：调用外部工具前必须加载匹配 adapter；不得因为工作流提到某动作就假定 capability 存在；工具返回的真实 failure/status 必须保留。`vba_doctor`、`vba_parse` 等名称只存在于 `vba-office` adapter。

保留原 skill 的承重原则：

> Never assume a capability exists merely because a workflow describes it; follow the exact contract and preserve actual errors.

### R2 — 通用的是验证证据不可越级推断，不是 Static/Compile/Runtime 三个名称

`Static < Compile < Runtime` 是 VBA adapter 的有效实例，不是 universal ladder。Core 定义的是：adapter 必须声明 verification states、每个 state 的 required evidence、状态间关系以及 unsupported state；agent 只能报告实际有证据满足的 state，不得用一种证据冒充另一种。

全局铁律改为：

> Never report a higher or stronger verification state than the evidence actually achieved.

对于线性 ladder，可报告 highest achieved level；对于非线性或独立检查模型，应逐项报告 achieved/unverified，不能强行压成一个“最高档”。

### R3 — 通用的是 recoverability requirement，不是文件备份目录

Core 要求所有高破坏性 mutation 在执行前声明 recovery model；该机制可以是 file backup、Git restore、transaction rollback、migration down/restore point、recreate-from-source 等。Core 不固定 `backups/<host>/...` 路径。

adapter 必须声明：mutation granularity、pre-mutation evidence、recovery mechanism、recovery preconditions、rollback verification，以及 irreversible/partially reversible 时的 stop condition。

`vba-office` 再实例化 repo-local text backup + same-tool restore。

### R4 — Diagnose/Review/Modify/Test 是 VBA 路由实例，不是 Core 闭合集

原 access-vba-dev 的四模有实际价值，但架构审阅已经指出其封闭性缺口：build-new、migration、refactor 等无法自然归类。因此 Core 只要求“操作前确定 intent 和 adapter route”；adapter 可以声明 `task_modes`，但必须同时声明 `closed: true|false` 与 fallback 行为。

`vba-office` 可继续声明四模，且应为 `closed: false`。未命中时回退到 Core generic operation lifecycle，而不是为了套分类而错误归类。

### R5 — 工具合同是 Adapter Interface，不是固定六项散文模板

原 access-vba-dev 的六要素合同设计继续作为重要来源，但全局稳定接口扩大为：

```text
identity/version/source-of-truth
supported environments
capabilities
operations/signatures
semantics beyond signatures
preconditions
failure preservation
mutation model
verification model
recovery model
optional task routing
source/provenance
```

原六要素可以完整映射进该接口，但“六”本身不是不可变架构事实。

### R6 — Adapter 必须部署自足

正式 `adapters/vba-office.md` 可以记录参考来源 provenance，但运行所需语义不得依赖 `references/access-vba-dev/...` 在部署环境中存在。开发仓的参考库是只读设计输入，不是安装后 dependency。

因此 adapter 内必须保留 agent 正确选择工具、形成调用、判断结果、报告验证等级、执行恢复所需的最小合同事实；若某段全文合同对运行必需，应重建到 `runtime-ops` 自己的 references 下，而不是跨出 skill 根目录引用。所有运行时相对路径继续从本 skill 目录解析。

### R7 — Profile-mediated configuration 只保留机制

Core 可规定“配置文件是 agent guidance，工具不会自动读取；调用时显式传值”，但大小写、默认值、`hostLibraries` 等具体值属于 adapter。不能把 Office profile 的 casing 特性变成通用规则。

### R8 — 回归测试错误决策，而不只测试文档存在

从 access-vba-dev 保留“测试错误 agent decision、正负案例并重”的质量哲学。P2 本身主要是 Markdown framework，机械 gate 负责 adapter contract 结构；各 adapter 的行为回归由 adapter 或消费项目承担。不能把“文件存在 + frontmatter 正确”当成 framework 行为已经成立。

## §3 SKILL.md 内容规格

### (a) frontmatter

```yaml
---
name: runtime-ops
description: Host-neutral control framework for operating registered external tools through explicit adapters with capability checks, preserved failure semantics, recoverable mutation, and evidence-bounded verification claims. Use when a task can read, inspect, modify, execute, migrate, test, or otherwise affect a host environment and the agent must load the adapter contract before acting.
---
```

### (b) 章节骨架

英文正文，目标 ≤8192 字节。标题序：`# Runtime Operations` → `## Scope` → `## Core contract` → `## Operation lifecycle` → `## Adapter routing` → `## Verification discipline` → `## Mutation and recovery` → `## Evidence discipline` → `## Prohibited behaviors`。

**Scope**：框架面向存在明确外部工具/宿主合同的工程操作；不负责定义具体语言、数据库、构建系统或 Office 语义。

**Core contract** 固定：

1. Load adapter before tool call；没有 adapter 或 capability 未声明，则停止相关操作或降级为不依赖该 capability 的分析。
2. Preserve exact operation identity、relevant inputs、returned status 与 failure message；不得把实际失败改写成“成功但有限”。
3. Distinguish observation, mutation and verification；成功写入不等于行为正确。
4. Mutation 必须满足 adapter recovery contract；不满足则不得执行高破坏性写入。
5. Verification claim 只能来自 adapter 对该 state 明确要求的证据。
6. Environment/profile values 必须显式传给工具；不得假定 server 自动读取 skill 文件。
7. Project convention 不得覆盖 adapter 的高优先级宿主/工具事实，冲突须报告。

**Operation lifecycle** 使用通用序列，不绑定四模：

1. classify intent and blast radius；
2. select adapter and environment；
3. load declared capabilities and preconditions；
4. inspect/read current state required for the intended operation；
5. if mutating, prepare and verify recovery path；
6. execute the smallest scoped operation；
7. reread/reobserve changed state where applicable；
8. run adapter-declared targeted verification；
9. recover when required by failure policy；
10. report achieved verification states、failures 与 remaining uncertainty。

Adapter 可在此生命周期之上提供 Diagnose/Review/Modify/Test、Deploy/Migrate 等 mode-specific workflow，但不能改变 Core safety invariants。

**Adapter routing**：只加载当前 host/tool adapter；缺 adapter 时不从相似宿主猜合同。

**Verification discipline**：摘要 `verification-ladder.md` 的 generic contract；不出现“所有宿主必须 compile”。

**Mutation and recovery**：摘要 recoverability contract；不写具体 backup path。

**Evidence discipline**：保留五 evidence type 与“会改变 agent 决策才加入”的准入门槛。

**Prohibited behaviors**：至少包括假定 capability、用低强度证据冒充更强验证、无 recovery mutation、修改 fixture 制造通过、把某 adapter 的工具名或 host-specific rule 编进 Core、部署时跨 skill 根目录依赖 reference repo、静默吞掉实际错误。

## §4 `references/verification-ladder.md`

文件名沿用主计划，但其概念定义改为 **Verification Model Contract**。建议章节：Model / States / Evidence requirements / Relations / Unsupported states / Reporting / Adapter examples。

每个 adapter 必须能表达：

```yaml
verification_model:
  kind: linear | partial_order | independent_checks
  states:
    - id: <stable-id>
      meaning: <what this state proves>
      required_evidence: [<observable evidence>]
      does_not_prove: [<explicit non-claims>]
  relations: []
  unsupported: []
```

规则：只有 `linear` 才允许使用 highest-achieved wording；`partial_order`/`independent_checks` 必须分别报告状态；unsupported state 必须显式报告；一种证据只证明 adapter 声明的范围；成功 mutation 本身不构成更强验证；precondition/permission failure 触发 adapter 指定的 downgrade 或 unverified 状态，并保留失败原文。

VBA 只作为 adapter example：`vba-office` 采用 linear，states 为 Static / Compile / Runtime；Access 的 Compile 标为 unsupported through registered vba-doctor API，Excel 则可达到 Compile。具体表放在 `adapters/vba-office.md`，不复制成 Core 定义。

## §5 `references/contract-template.md`

该文件成为 Adapter Contract 规范，而不是 VBA 工具文档模板。建议章节：Required metadata / Capabilities and operations / Preconditions and failures / Mutation model / Verification model / Recovery model / Environment and configuration / Task routing / Provenance。

Adapter 建议使用 Markdown + YAML frontmatter，最低元数据：

```yaml
---
adapter_schema_version: 1
adapter: <kebab-case>
environments: [<scenario-or-host>]
capabilities: [<stable-capability-id>]
task_modes:
  closed: false
  modes: []
verification_model_kind: linear | partial_order | independent_checks
mutation_support: none | bounded | high-impact
---
```

正文必须回答：

1. **Identity/version/source-of-truth**：真实 provider/tool/server 身份、版本获取方式、权威实现来源。
2. **Capabilities**：稳定 capability id；具体工具映射到 capability，Core 不依赖工具名。
3. **Operations**：真实注册名、签名、默认值、返回形态、宿主适用性、承重语义。
4. **Preconditions/failures**：权限、打开状态、环境依赖；实际 failure 必须保真。
5. **Mutation model**：哪些操作改变状态、粒度、blast radius。
6. **Verification model**：状态、required evidence、relations、unsupported states。
7. **Recovery model**：机制、准备步骤、恢复步骤、恢复验证、不可恢复条件。
8. **Environment/configuration**：宿主版本、平台、profile/config 注入规则、本地资产供给。
9. **Task routing**：可选；若声明 modes，必须写 `closed` 与 fallback。
10. **Provenance**：adapter 自足，但记录设计参考源与外部实现来源。

具体 capability vocabulary 不在 P2 过度标准化；首版只需保证同一 adapter 内稳定、可解释。跨 adapter capability registry 若实际出现复用需求，再由 P3 控制层决定是否提升为平台级枚举，避免预先发明 taxonomy。

## §6 `references/evidence-types.md`

保留 access-vba-dev 的五类知识证据，因为这是可跨宿主迁移的认识论层：

- `documented_fact`；
- `evidence_based_inference`；
- `verified_empirical_behavior`；
- `project_convention`；
- `community_guidance`。

每条知识主张恰好一个类型。来源优先级不硬编码 Microsoft/DAO/VBA，而使用通用模板：primary authority → adjacent authority when applicable → controlled experiment → generic static/tool evidence → community discovery；adapter 可以实例化更具体的 source ladder。

保留：

> A lower-priority source never overrides a higher-priority one for the same claim.

以及：

> Add information only when it is likely to change an agent's decision.

受控实验记录环境、版本、fixture、精确 tool inputs/outputs、观察结果与适用边界；不得从单个实验无界泛化。

## §7 `adapters/vba-office.md` 首个实例

该 adapter 负责承载所有 Office/VBA 特有形状，Core 不重复。

建议 frontmatter：

```yaml
---
adapter_schema_version: 1
adapter: vba-office
environments: [win-access-vba]
capabilities: [source.read, source.write, source.static-analyze, project.compile, runtime.execute, ui.dialog-control]
task_modes:
  closed: false
  modes: [diagnose, review, modify, test]
verification_model_kind: linear
mutation_support: high-impact
---
```

adapter 内容要求：

1. **Task routing instance**：Diagnose/Review/Modify/Test 保留为 Office 首选模式，但 `closed: false`。未命中时回到 Core lifecycle；不得把 build-new/refactor/migration 强塞进四模。
2. **Verification instance**：VBA 使用 `Static → Compile → Runtime` 线性模型。Access Compile unsupported through registered vba-doctor；Excel Compile 由 `compile_vba_project`。成功 source write / clean lint 不等于 compile/runtime evidence。
3. **vba-doctor capability mapping**：记录 open/read/write/module/compile/run/dialog 等真实工具与签名；执行所需语义内联到 adapter。开发 provenance 可引用 `references/access-vba-dev/...`，但部署后不得要求该路径存在。
4. **vba-lint capability mapping**：记录 `vba_parse` / `vba_inspect` / `vba_inspect_workspace` / `vba_list_inspections` 的真实签名、hostLibraries casing、静态证据边界与已知限制；live catalog 优先于硬编码数量。
5. **Configuration**：Access `["access"]`、Excel `["Excel"]` 等值只存在 adapter；明确 agent 显式传参，MCP 不读取 skill profile。
6. **Recovery instance**：对 `set_vba_code` / Ribbon XML 等整体替换操作，实例化 repo-local text backup；可沿用 `backups/<host>/<file-stem>/<artifact>.<yyyyMMdd-HHmmss>.<ext>`；确认写出后才 mutation，恢复走同一工具并 reread 验证。该目录约定不外溢到 Core。
7. **Fixture instance**：`.accdb/.xlsm` 受控本地资产、gitignored；缺失时停止 fixture-backed verification，绝不替换成生产文件；temporary smoke code 用后移除。
8. **Source priority instance**：Microsoft object model / DAO / VBA language / controlled fixture / vba-lint / community 的具体优先级留在 adapter。

### 部署自足要求

`vba-office.md` 不得以“完整合同请见 `references/access-vba-dev/...`”作为运行必要步骤。可以在 `## Provenance` 记录这些开发参考路径，但所有 agent 作出正确 tool call、verification claim、recovery decision 所需的承重信息必须位于 runtime-ops skill 自己目录内。

## §8 Adapter Contract 的机械 Gate

adapter 已成为 framework extension ABI，因此必须存在最小机械 gate，但本计划不强制它一定在 P2 还是 P3 编码；实施时按 P0/P3 职责边界落点。最终 active 前至少应能机械判断：

- `adapter_schema_version` 受支持；
- adapter id 与文件身份一致；
- environments 非空；
- capabilities 非空且去重；
- `task_modes.closed` 明确存在；
- `verification_model_kind` 属于允许集合；
- `mutation_support` 属于允许集合；
- 高影响 mutation 存在 Recovery model；
- 不机械验证具体 MCP 是否在线，availability 属运行时检查。

该 gate 若延后至 P3，则 P2 的完成状态只能表示“framework 与 adapter contract 内容完成”，不能提前声称平台 lifecycle 已对 adapter 实施自动强制。

## §9 验收运行手册

1. **基线**：实施前确认 P0 平台校验基线为绿；本计划修改本身不执行功能实现。
2. **Core purity**：未来 Core SKILL + references 不得出现 `vba_doctor`、`vba_parse`、Access、Excel、`hostLibraries`、`.accdb/.xlsm`、`compile_vba_project`、固定 backup path；这些只允许出现在 `vba-office` adapter 或明确标注的 example 中。
3. **VBA fidelity**：抽查至少 10 个源锚点，覆盖真实工具名/签名、hostLibraries casing、Access compile unsupported、Access Eval smoke、Excel compile、dialog handling、whole-module replacement、failure preservation、backup/restore、fixture integrity。要求 adapter 语义与 `references/access-vba-dev` 当前合同一致。
4. **Deployment self-containment**：模拟 `references/access-vba-dev/` 不可见，只阅读 `development/skill/runtime-ops/`；仍应足以决定 VBA 关键工具调用、验证状态与恢复动作。若必须回读参考库才能正确操作，则失败。
5. **Orthogonality probe**：一次性设计 `synthetic-transactional` adapter，故意与 VBA 不同：task modes 为 `[inspect, migrate, verify]` 或为空；verification model 使用 `independent_checks`，例如 `schema_valid / transaction_applied / postcondition_observed`，不存在 Compile；recovery model 为 transaction rollback，不存在文件 backup；capabilities 不含 VBA/Office 工具。要求不修改 Core 即能被 contract 与 Core lifecycle 合理解释。probe 不进入正式 manifest。
6. **反向约束**：若 synthetic adapter 迫使把 `Compile`、四模或 backup path 加入 Core，说明抽象失败，P2 不得标 `done`。
7. **Adapter gate**：必须能机械识别 schema、capabilities、task-mode closure、verification kind 与 high-impact recovery requirement；具体编码阶段可由 §8 决定，但 active 前不得缺失。
8. **体量**：SKILL.md 与单个 reference/adapter 目标 ≤8192 字节；完整 contract 优先于机械缩短。
9. **生长闸门**：仅在 Core、`vba-office` 实例、self-containment、orthogonality probe 与 adapter gate 均成立后，才允许 manifest 将 `runtime-ops` 从 `planned` 翻为 `active`。

## §10 与主计划的解释优先级

`000-platform-skeleton.md §3.3/§4 P2` 中的 `Static<Compile<Runtime`、规范化备份命名和 Access/VBA 合同描述，视为**来源实例与最低迁移要求**；本精细计划将其架构语义进一步收敛为 adapter-defined verification / recoverability / capability contract。实施时以本文件的泛化边界为准，同时必须在 `vba-office` adapter 中完整保留主计划要求的 VBA 实例行为。

这不是取消主计划验收，而是避免把首个实例的偶然形状错误提升为全局 framework 本体。

## §11 文档同步

P2 实施后若 adapter contract 或“verification model 不必线性”的规则使 `repo-conventions.md` 现有描述失准，则同步对应段。AGENTS.md 只保留高 blast-radius mutation 必须有 Contract / Stop Conditions / recoverability 这一绑定级规则，不放 VBA 实例细节。
