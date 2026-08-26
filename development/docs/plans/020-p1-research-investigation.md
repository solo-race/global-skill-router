# P1 研究框架泛化 — 精细实施计划

Status: done
Date: 2026-08-25
Depends-on: 000-platform-skeleton, 010-p0-foundation

> Status 生命周期：`draft → approved → executing → done`。被取代的计划保留状态 `superseded`，永不删除。Status 字段是本文件唯一事实源。

## §1 目标、抽象边界与产出

目标：从 `references/customer-research-skills/recycling-company-investigation/` 提取可迁移的**证据调查控制面**，重建为 `development/skill/research-investigation/`。本阶段不把原技能的行业词汇、公司运营维度或 customer_screening 项目接口提升为全局本体；核心只负责“如何从可访问外部来源重建可审阅主张”，领域问题模型由 profile 提供，消费项目接口由 project binding 提供。

本框架的真实适用域是：需要从公开或授权可访问资料中重建身份、属性、关系、状态或变化，并要求证据可追溯与人工复核的**外部实体、设施、组织或项目调查**。它不是“任意对象研究器”，也不承担通用学术研究、自由写作、数值评分或自动决策。

架构分三层：

```text
Research Core
  ├─ evidence admissibility / evidence states / conflict & coverage discipline
  ├─ bounded discovery / subject-claim matching / review packet contract
  └─ no domain vocabulary, no project schema path, no scoring policy
        ↓
Profile Contract
  ├─ subject model / investigation dimensions / vocabulary / query examples
  ├─ optional packet extensions / relevance vocabulary
  └─ versioned extension surface
        ↓
Domain Profile + optional Project Binding
  ├─ recycling-company.yaml
  └─ consuming-project-owned schema/config/source identifiers when present
```

计划产出：

1. `development/skill/research-investigation/SKILL.md` —— 调查入口、Contract、通用工作流、profile 加载纪律。
2. `development/skill/research-investigation/references/evidence-rules.md` —— 四态证据模型、来源可采纳性、冲突与覆盖纪律。
3. `development/skill/research-investigation/references/evidence-taxonomy.md` —— 来源层级、subject/claim matching、bounded discovery 机制。
4. `development/skill/research-investigation/references/output-schema.md` —— 稳定 review-packet 核心结构与扩展规则。
5. `development/skill/research-investigation/references/profile-contract.md` —— profile 字段、所有权、兼容与缺失语义。
6. `development/skill/research-investigation/profiles/recycling-company.yaml` —— 首个正式 profile，保持原调查能力但不成为 Core 定义来源。

非目标：不建 `agents/` 目录（agent 路由归 P3）；不复制 customer_screening 代码或 schema；不实现第二个正式业务 profile；不在本阶段实现工具层；不把项目外部路径伪装成框架自有资源；本计划本身也不实施上述文件。

验收必须同时回答两件不同的事：recycling profile 是否忠实保留原生 skill 的有效方法，以及换一个异质 profile 时 Core 是否仍无需修改。只验证前者不足以证明 framework 抽象成立。

## §2 泛化原则 G1–G7

### G1 — 抽原则，不抽实例形状

原 skill 中可提升为 Core 的是：发现材料与证据分离、四态证据词汇、来源可采纳性、subject/claim matching、冲突保留、覆盖缺口可见、禁止由失败检索推出业务负面、人工复核终态。公司专用 lanes、物料/工艺链、设备相关性、供应商关系、customer_screening 标识符全部不是 Core。

### G2 — Core 不拥有领域问题模型

Core 不固定 `Inputs / Operations / Outputs / Resources / Scale` 等研究 lane。Core 只要求 profile 声明 `investigation_dimensions`；运行时仅加载与当前问题相关的维度。`recycling-company` profile 可继续实例化原六类调查面，但另一个 profile 可以完全不同。

### G3 — Pipeline 边界是可映射语义，不是硬编码项目拓扑

原 `Acquisition → Source → Signal → Fact → Score` 保留为首个 profile/project binding 的参考模型，而不是全局唯一流水线。Core 只声明：discovery material 不能自动晋升为 canonical fact；若消费项目存在 staged pipeline，binding 必须声明本技能允许读取、产出和禁止跨越的阶段；若无外部 pipeline，则默认产出 human-review packet，不发明 canonical IDs。

因此 Core 不要求所有未来消费项目都存在名为 Acquisition/Source/Signal/Fact/Score 的五段。

### G4 — Profile 是正式扩展接口，不是自由 YAML

`profiles/<domain>.yaml` 是 framework ABI 的一部分，必须携带 `profile_schema_version`，并遵循 `references/profile-contract.md`。未知承重语义不得被静默忽略；可选扩展必须有明确命名空间。profile 至少覆盖：

- `domain` / `subject_type`；
- `investigation_dimensions`；
- `concept_groups` / `query_examples`；
- 可选 `relevance` 与 packet extension；
- 可选 `pipeline_binding`；
- 可选 `project_bindings`，且必须声明所有权和缺失时的行为。

P1 是否同时扩展平台 validator，由实施时根据 P0 校验器职责边界决定；本计划的硬要求是 profile contract 必须可机械校验，不能只靠散文约定。若不在 P1 扩 validator，则该校验必须在 P3 lifecycle gate 前补齐，P1 不得把“未校验 profile”描述为完整扩展 ABI。

### G5 — 外部契约必须显式拥有者与缺失语义

`SourceRecord`、`source_id`、`EvidenceLink`、`config/search_terms.yaml`、`schemas/company_result.schema.json`、`customer_screening.evidence` 不再作为框架自有资源。若 recycling profile 需要保留这些映射，只能放入 `project_bindings`，并明确：

```yaml
owner: consuming_project
required: false
when_unavailable: review_packet_only
```

只有调用方显式选择 canonical mode 时，某些 binding 才可变为调用前置条件。框架不负责解析、创建或验证这些外部对象本体。这样 standalone skill 仍可完整运行到 review-packet 层，不再因外部项目不存在而结构失效。

### G6 — Progressive disclosure 保持轻量

`SKILL.md` 只放路由、Contract、工作流和加载索引；证据细则、输出合同、profile ABI 下沉 references。每个文件保持 kilobyte-scale；`≤8192` 字节作为体量 guardrail，而不是语义目标。不能为了过体量检查删除承重契约。

### G7 — 验收必须跨实例

用 recycling profile 验证**迁移忠实度**，用一次性异质 synthetic profile 验证**抽象正交性**。后者不是第二个正式 profile，也不进入 manifest；它只是架构 probe。

## §3 SKILL.md 内容规格

### (a) frontmatter

```yaml
---
name: research-investigation
description: Evidence-first framework for reconstructing reviewable claims about externally documented entities, facilities, organizations, or projects from bounded accessible sources. Use when a task requires source admissibility, explicit confirmed/inferred/unknown/conflicting states, visible coverage gaps, conflict preservation, and a profile-defined investigation model before human review.
---
```

### (b) 章节骨架

英文正文，目标 ≤8192 字节。标题序：`# Research Investigation` → `## Scope` → `## Contract` → `## Workflow` → `## Evidence handling` → `## Profiles` → `## Output boundary` → `## Prohibited behaviors`。

**Scope**：明确本技能是 evidence reconstruction / investigation framework，不是评分器、推荐器或任意对象通用研究器。默认终态是 human-review packet；canonical pipeline 模式仅在调用方提供合法 binding 时启用。

**Contract** 至少固定以下不可配置规则：

1. Search result、snippet、candidate profile、model output、provider score 等均为 discovery context，不是事实摘录。
2. Material claim 必须绑定 accessible original/authoritative source body 或文档；无法访问时只能形成 gap/review reason。
3. 不发明 source/fact/resource/evidence identifiers；仅复制调用方已提供且 binding 声明可用的 canonical ID。
4. `unknown`、partial coverage、blocked page、failed retrieval 不得转写成实体负面事实。
5. 冲突不得静默裁决；保留 incompatible observations 与来源。
6. 不绕过 login、CAPTCHA、robots、paywall、rate limit 等访问控制；失败端点停止重复尝试。
7. 默认不产出 numeric score、automatic exclusion、entity deletion、final recommendation；profile 可定义待人工复核的相关性标签，但不得改变上述终态。
8. 覆盖缺口、语言缺口、推断、冲突、subject match 未决必须保留在 `manual_review_reasons`。

**Workflow** 改为真正 profile-neutral 的七步：

1. Define the material question —— 确认 subject、jurisdiction/context、会改变复核结论的问题。
2. Load the profile —— 读取 subject model、investigation dimensions、approved vocabulary、可选 project binding；profile 不满足 contract 时不得自行猜测缺失语义。
3. Resolve the subject —— 收集 profile 要求的 identity keys、aliases、sites/scope；同名对象不无证据合并。
4. Plan bounded discovery —— 从当前问题涉及的 dimensions 与 concept groups 生成最小查询集；语言扩展遵循 profile 的批准规则。
5. Acquire admissible sources —— 优先可访问原始/权威来源；记录 URL、title、dates、source kind、retrieval status、bounded excerpt、locator、subject match。
6. Reconstruct findings —— 按 profile-defined dimensions 组织 claim，不假定必须是 `input → operation → output`。
7. Assign evidence state and prepare packet —— 按 evidence-rules/output-schema 输出 review candidates；canonical mode 仅复制调用方提供的合法 IDs，永不自行晋升阶段。

**Evidence handling**：正文只摘要四态并链接 references，不重复全部裁决细则。

**Profiles**：声明 profile 是 agent guidance，不由环境工具自动读取；Core 依赖 contract，不依赖 recycling profile 的具体维度名称。只加载当前 domain profile。

**Output boundary**：默认 review packet；若 `pipeline_binding.mode` 允许 canonical candidates 且调用方提供所需 canonical sources，则可生成候选，但不得自动写入项目事实库或评分阶段。

**Prohibited behaviors**：集中列出 discovery→fact 越权、缺证据负面、伪造 ID、领域词汇硬编码进 Core、把 profile 缺失当默认值继续、把项目 schema 路径当框架自有资源等。

## §4 references/ 内容规格

### (a) `references/evidence-rules.md`

保留原 skill 中领域无关且承重的认识论控制：四态 `confirmed / inferred / unknown / conflicting`；禁用平行状态；accessible/partial/failed retrieval 语义；bounded excerpt；direct/indirect/ambiguous subject match；failed/partial 只解释 gap，不支持负面；冲突 preserve-all；`manual_review_reasons` 强制触发器。

`confirmed` 的实体措辞泛化为 subject/site/project context，不出现 recycling 专用条件。

### (b) `references/evidence-taxonomy.md`

保留机制而非行业词表：source hierarchy；source strength 与 claim relevance 分离；subject/claim scope matching；bounded discovery；search result 只负责发现 URL；localized aliases 经过 domain/profile 的批准、翻译复核和测试后才成为 executable vocabulary；language gap 进入 review reason。

具体 concept groups 与 query examples 全部移入 profile。

### (c) `references/output-schema.md`

定义稳定 core packet，而不是公司专用 packet：

```yaml
review_packet:
  subject:
    type: ""
    name: ""
    identifiers: {}
    locations: []
  metadata:
    investigated_at: "YYYY-MM-DD"
    languages_used: []
    coverage_summary: ""
    manual_review_reasons: []
  sources: []
  findings: []
  evidence_gaps: []
  profile_extensions: {}
```

`sources[]` 固定记录 URL、source_kind、retrieval_status、title、dates、excerpt、locator、subject_match、discovery_only；`findings[]` 固定记录 `fact_type/claim/evidence_state/source_urls/reasoning/review_required`。行业相关性、工艺链、设备分类等进入 `profile_extensions`，由 profile contract 命名和解释。

Canonical Fact candidate 仅在 caller supplies canonical source records 时启用；ID 只能复制，不能计算或生成。Core 不声明 customer_screening schema 名称。

### (d) `references/profile-contract.md`

这是 P1 新增的承重架构文件。目标字段：

```yaml
profile_schema_version: 1
domain: <kebab-case>
subject_type: <string>
investigation_dimensions:
  - id: <stable-id>
    purpose: <why this dimension changes review>
concept_groups: {}
query_examples: []
vocabulary_authority: null | <binding>
relevance: null | {...}
packet_extensions: {}
pipeline_binding: null | {...}
project_bindings: {}
display: {}
```

规则：`investigation_dimensions` 非空，Core 不认识具体 dimension 名称；`concept_groups/query_examples` 可为空但类型固定；`project_bindings` 每项必须声明 owner/required/when_unavailable，禁止裸路径承担隐式契约；`pipeline_binding` 声明 mode 与 consumes/produces 边界，缺失时默认 `review_packet_only`；`packet_extensions` 只能扩展 `profile_extensions`，不得重定义 evidence states、sources 或 `manual_review_reasons`；未知 schema version 停止，不猜测。

## §5 `profiles/recycling-company.yaml` 实例化规则

该 profile 的目标是复现原 skill 的**调查能力**，不是逐字段复制其项目耦合。应迁入：`subject_type: company`；原六类 research lanes 作为 `investigation_dimensions`；原 5 组 concept groups 与 7 个 query examples；recycling/plastics/WEEE/ELV relevance 作为 profile extension；原 `input → internal operation → output` 作为该 profile 的可选 domain model；English-first 与 localized alias 三门规则。

原外部接口改写为显式 project binding，例如：

```yaml
project_bindings:
  vocabulary_authority:
    owner: consuming_project
    reference: config/search_terms.yaml
    required: false
    when_unavailable: use_profile_vocabulary_only
  canonical_result_schema:
    owner: consuming_project
    reference: schemas/company_result.schema.json
    required: false
    when_unavailable: review_packet_only
  evidence_store:
    owner: consuming_project
    reference: customer_screening.evidence
    required: false
    when_unavailable: review_packet_only
pipeline_binding:
  mode: canonical_candidates_when_supplied
  reference_stages: [Acquisition, Source, Signal, Fact, Score]
  consumes: [Source, Signal]
  produces: [Fact-candidate]
  never_promotes_to: [Score]
```

`SourceRecord/source_id/EvidenceLink/ev_*` 等只作为 consuming-project binding 的术语映射；没有 caller-supplied canonical source 时不得生成 ID。

## §6 验收运行手册

1. **基线**：实施前运行现有平台校验器，确认 P0 基线仍为绿；本计划修改本身不执行任何功能实现。
2. **Core purity**：未来实现的 `SKILL.md` 与 Core references 不得出现 recycling/WEEE/ELV/具体聚合物/设备词，也不得出现 `customer_screening.evidence`、`schemas/company_result.schema.json`、`config/search_terms.yaml`、`SourceRecord` 等 consuming-project 专名；这些只允许存在于 recycling profile 的实例/binding 中。
3. **Recycling fidelity**：沿原 skill 抽查至少 8 个机制锚点，覆盖四态、source kinds、source hierarchy、subject match、coverage triggers、query discipline、concept groups、relevance，确认均能在 Core + recycling profile 中找到对应落点。
4. **Standalone check**：设想 recycling profile 的全部 `project_bindings` 不可用，框架仍必须完整降级为 `review_packet_only`；若外部项目不存在会使 Core 无法工作，则架构失败。
5. **Orthogonality probe**：一次性设计一个不使用公司运营链的 synthetic profile，例如 `software-project`，dimensions 为 `identity / ownership / release-status / dependency-relationship`，无 Inputs/Operations/Outputs、无 equipment relevance、无五段 customer pipeline。要求不修改 Core 即能表达其调查过程。probe 验证后不进入正式 skill/manifest。
6. **Profile contract check**：必须能机械判定 schema version、必填字段、dimension 唯一性、binding ownership/缺失语义；具体落在 P1 validator 扩展还是 P3 lifecycle gate，可在实施前根据 P0 职责边界决定，但不得取消该 gate。
7. **体量**：SKILL.md 与单个 reference 目标 ≤8192 字节；contract 完整性与体量冲突时，以完整性优先并记录原因。
8. **生长闸门**：仅在上述架构与实现验收均通过后，才允许 manifest 将 `research-investigation` 从 `planned` 翻为 `active`。

失败条件：若 synthetic profile 需要修改 Core 才能表达，说明仍把 recycling 实例形状提升成了框架本体；若 project binding 缺失会使技能无法产生 review packet，也说明悬空外部契约没有真正解决。两者任一成立，P1 不得标 `done`。

## §7 与主计划的解释优先级

`000-platform-skeleton.md §3.2/§4 P1` 中的五段 pipeline、research lanes 与 recycling profile 描述，视为**首个来源实例与最低迁移要求**；本精细计划进一步明确其泛化边界：Core 保留证据调查纪律，具体 pipeline、domain dimensions 与 consuming-project bindings 留在 profile/adapter 层。实施时以本文件的抽象边界为准，同时必须保留主计划要求的 recycling 实例行为。

## §8 文档同步

P1 实施后若 profile contract 或其机械 gate 改变 `repo-conventions.md` 对平台校验覆盖面的描述，则同阶段同步对应段；除此之外不复制 profile contract 到 AGENTS.md。AGENTS.md 继续只保留绑定级规则与条件阅读入口。
