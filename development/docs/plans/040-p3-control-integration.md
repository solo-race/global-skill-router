# P3 控制集成 — 精细实施计划

Status: draft
Date: 2026-09-05
Depends-on: 000-platform-skeleton, 010-p0-foundation, 020-p1-research-investigation, 030-p2-runtime-ops

> Status 生命周期：`draft → approved → executing → done`。被取代的计划保留状态 `superseded`，永不删除。Status 字段是本文件唯一事实源。

## §1 目标、基线与完成边界

P3 的目标严格继承 `000-platform-skeleton.md §4 P3`：把 P0 的注册/校验地基、P1 的 Research Profile ABI、P2 的 Runtime Adapter ABI 收束成一个可验证的技能控制面，使注册表覆盖平台的正式技能、扩展实例和只读设计来源；scenario 路由能够解释当前三类本机开发场景；`planned → active` 的状态不再只是人工约定，而由 active-state 校验门禁机械约束；部署位置与 skill 内相对路径的关系有单一约定；并用一次性 probe 演示完整 growth loop。

当前基线已经满足以下前置事实：P0/P1/P2 计划均为 `done`；`research-investigation` 与 `runtime-ops` 已存在并在 manifest v1 中标 `active`；Research Profile Contract 已由 `validate_skills.py` 机械校验；`runtime-ops/adapters/vba-office.md` 已具备 P2 定义的 Adapter Contract 内容，但 Adapter Contract 尚无机械 gate；manifest v1 仍把三个只读 reference 以 `status: external` 混在 `skills` 中，且没有 adapter 注册面；两个 active skill 尚无 P3 负责的 agent-facing routing metadata。

P3 完成后平台应满足四个可观察条件：一是“什么是正式 Skill、什么是 adapter、什么只是设计 reference”在 manifest 中身份分离；二是每个 active extension 都经过其 ABI gate，不能靠文件存在即被视为可用；三是三种 scenario 都能得到明确的 active/planned/no-capability 路由解释，不把 planned adapter 伪装成可执行能力；四是一个 skill 目录可以脱离 `references/` 独立映射到运行环境而保持自引用有效。

本阶段不实现新的业务 Skill，不实现 `sql-server`、`android-gradle`、`wsl-python` adapter 本体，不把现有 `access-vba-dev` 或 `recycling-company-investigation` 旧 Skill 迁入运行环境，不编写自动 install/update/remove/rollback 管理器，也不建立 CI/build system。P3 只闭合 skeleton 已规定的控制集成、路由、生命周期 gate 与部署约定；正式安装管理器和旧 Skill 迁移属于 P3 完成后的试用/迁移工作面，除非后续另立计划。

## §2 P3 架构决策 C1–C9

### C1 — Manifest v2 分离 `sources / skills / adapters`

manifest v1 把只读设计来源和可部署 Skill 放在同一个 `skills` 数组中，并以 `status: external` 区分。该结构在 P3 已经产生两个实际问题：reference 目录被 `.gitignore` 排除、fresh clone 不应依赖它们存在；同时 `access-vba-dev`、`recycling-company-investigation` 等 reference 名称会占用未来正式受管 Skill 的全局名称。因此 P3 将 manifest schema 升为 v2，顶层分成：

```yaml
schema_version: 2
sources: []
skills: []
adapters: []
```

`skills` 只描述可部署平台 Skill；`adapters` 描述 framework-owned extension instance；`sources` 只记录开发期 provenance/reference 位置。三个命名域分别唯一，不要求跨域唯一，因此 source id 不再抢占 future skill name。但为降低歧义，正式 source id 仍统一采用 `*-reference` / `*-upstream` 一类明确后缀。

P0 的 Skill lifecycle 语义保留：Skill status 仍只使用 `planned | active`；`planned` 可 forward-register，`active` 必须路径和 contract 均完整。`external` 从 Skill status 集合移除，因为外部设计输入已经进入 `sources` 命名域。这个 schema v2 是 P3 对 P0 v1 的向前演进，不回改或重写 `010-p0-foundation.md` 的历史事实。

### C2 — Reference source 是可选设计输入，不是部署依赖

`sources[]` 最低字段：`id / path / kind / required / version / description`。P3 基线中的三个来源登记为 `required: false`：

- `spinecodex-skills-upstream` → `references/SpineCodex-skills`；
- `recycling-company-investigation-reference` → `references/customer-research-skills/recycling-company-investigation`；
- `access-vba-dev-reference` → `references/access-vba-dev`。

`required: false` 的 source 路径不存在时不导致平台 validator 失败；若路径存在，只做安全路径/类型层面的轻校验，不把 reference 自己的 frontmatter、tests 或内部结构纳入平台 activation gate。这样 `.gitignore` 可以继续忽略 `references/**`，reference 可按需在开发机提供，而已部署 Skill 不依赖它们。任何运行必要语义必须已经进入 `development/skill/<name>/` 自己目录，这是 P1/P2 的 self-containment 约束在 P3 的平台化表达。

### C3 — Adapter 是独立 registry entry，但归属于 owner Skill

`adapters[]` 最低字段：

```yaml
- name: vba-office
  path: development/skill/runtime-ops/adapters/vba-office.md
  status: active
  owner_skill: runtime-ops
  environments: [win-access-vba]
  version: "0.1.0"
  description: Microsoft Office VBA runtime adapter.
```

正式基线登记一个 active adapter `vba-office`，并 forward-register skeleton 指定的三个 planned adapter：`sql-server`、`android-gradle`、`wsl-python`。planned adapter 路径可缺席；一旦文件存在即执行其 contract structural gate。active adapter 必须路径存在、owner_skill 存在且 active、frontmatter/manifest 身份一致、环境至少一个且均属于平台 scenario vocabulary。

三个 planned adapter 仅表示扩展位已经登记，不表示任何 capability 可用。当前 scenario vocabulary 仍严格沿用 P0 的 `{win-access-vba, win-android, wsl-python}`；P3 不新增 `win-sql` 等第四场景。`sql-server` 暂登记在 Windows-native 现有桶 `win-access-vba` 下，这只是当前三场景模型内的 route placement，不把 SQL 语义并入 VBA Core；若以后发现该 scenario 名已经妨碍正确路由，应另立 schema migration，而不是在 P3 偷改上位场景模型。

### C4 — P2 Adapter Contract gate 在 P3 正式落地

P3 扩展 `validate_skills.py`，新增 `adapter_errors()` 并接入 manifest-level validation。对 active adapter 必须机械判断：`adapter_schema_version == 1`；frontmatter `adapter` == manifest name == 文件 stem；`environments` 非空、去重且与 manifest environments 完全一致；`capabilities` 非空且去重；`task_modes` 为 mapping、`closed` 为显式 bool、`modes` 为 list 且去重；`verification_model_kind ∈ {linear, partial_order, independent_checks}`；`mutation_support ∈ {none, bounded, high-impact}`；当 mutation_support != `none` 时正文必须存在非空 Recovery model section；active adapter 的 owner_skill 必须 active。

该 gate 的边界与 P2 保持一致：它验证 ABI 结构与 activation precondition，不探测 MCP/server 是否在线，不对 operation 实现做 live calls，不根据正文推测未声明 capability，也不把 VBA 的 Static/Compile/Runtime 固定成全局规则。`vba-office` 必须在不改变其 P2 语义的前提下通过该 gate。planned adapter 文件缺席合法；文件出现后即按同一结构 gate 校验，但 owner_skill 只要求存在，直到 adapter 置 active 时才要求 owner active。

### C5 — `deps` 与 `composed_of` 成为真正 lifecycle edge

P0 已定义两个字段但仅机械校验了 `composed_of` 引用存在。P3 补全语义：`deps[]` 表示当前 Skill 运行时必须可用的其他 Skill；`composed_of[]` 表示 orchestrator/aggregate Skill 明确编排的子 Skill。两类引用均只允许指向 `skills[]`，不得指向 source 或 adapter。

active Skill 的每个 dependency 必须解析到 active Skill；planned Skill 可以依赖 planned 或 active Skill。active orchestrator 的每个 `composed_of` 目标必须 active；planned orchestrator 可引用 planned/active。两种 edge 均禁止 self-reference 与 cycle。dependency cycle 和 composition cycle 分开检测并报告，不把两种语义混成一张图。

当前两个正式 Skill 相互独立，`deps: []`、`composed_of: []` 保持为空。P3 不为满足“必须出现组合边”而凭空创造永久 orchestrator；这会违反 AGENTS.md 的“信息/工具只有改变 agent 决策才加入”原则。skeleton 要求的编排者组合边由一次性 growth-loop probe 演示：临时 `probe-orchestrator` 通过 `composed_of` 指向临时 `probe-worker`，验证后整个 probe 从临时树移除，不进入正式 manifest。

### C6 — Agent-facing entrypoint 用 manifest 声明并由 metadata gate 约束

manifest v2 的 Skill entry 新增 `entrypoint: bool`。`entrypoint: true` 表示该 Skill 应被 agent discovery/routing 直接发现；active entrypoint 必须存在 `agents/openai.yaml`。P3 为当前两个 active Skill 新增：

- `development/skill/research-investigation/agents/openai.yaml`；
- `development/skill/runtime-ops/agents/openai.yaml`。

metadata 最低结构沿用 repo-conventions：单一 `interface` mapping，包含非空 `display_name / short_description / default_prompt`，且 `default_prompt` 必须含 `$<skill-name>`。metadata 只负责入口可发现性和默认触发提示，不复制 SKILL.md 的 contract、profile 内容或 adapter operation 表。

未来薄 orchestrator 可以 `entrypoint: true`；内部 worker/sub-skill 可设 `entrypoint: false`，此时不强制 `agents/openai.yaml`。planned entrypoint 若目录或 metadata 尚不存在允许 forward registration；一旦 metadata 存在即执行 schema gate。

### C7 — Scenario route 是 manifest 的投影，不建立第二个权威 registry

P3 必须产出 skeleton 要求的“三场景 × 技能”路由表，但不能制造第二份可独立漂移的配置。因此权威数据仍来自 manifest：Skill 的 `scenarios[]` 描述该 Skill 适用的高层场景；Adapter 的 `environments[]` 描述 runtime-ops 在哪些场景具有具体 host/tool extension。P3 新增 `development/docs/scenario-routing.md` 作为 operator/agent 可读的**派生说明**，并明确 manifest 是 authority。

路由不是“一个 scenario 唯一对应一个 Skill”。同一场景可按 intent 分到不同控制面：例如 `wsl-python` 的 evidence investigation 可由 `research-investigation` active 处理，而 runtime mutation 若只有 planned `wsl-python` adapter，则必须明确报告该 runtime route 尚未 active，不能因为 `runtime-ops` Core 存在就假定 capability。`win-android` 同理，在 `android-gradle` planned 期间只能说明扩展位已登记；不能宣称 Gradle runtime operations 已受 adapter contract 覆盖。

validator 对 route completeness 的机械定义是：三个合法 scenario 必须至少出现在一个 Skill scenario 或 Adapter environment 中；每个 active adapter 必须能回溯到 active owner Skill；每个 active entrypoint 必须至少有一个 scenario。该 gate 证明“平台知道该场景如何解释”，不证明所有任务已经有 active implementation。

### C8 — Lifecycle gate 通过 active-state validity 实现，不新增状态修改器

P3 不引入 `activate_skill.py` 或自动修改 manifest 的工具。生命周期门禁继续采用 declarative validation：任何条目可以被人工改成 `active`，但只要其 active-state prerequisites 不全，`validate_skills.py` 必须失败，因此无法形成绿色平台状态。对 Skill、Profile、Adapter、entrypoint metadata、deps/composition 和 route completeness 的所有强约束都汇入同一个 validator report。

这满足 skeleton 的“`planned → active` 仅在校验器绿后”要求，同时保持 repo minimal，不创造一个只能包装 YAML 编辑的命令层。以后若部署管理器需要事务式 activate/deactivate，可在独立计划中建立，不属于 P3。

### C9 — 部署约定只规定映射和自足性，不实现安装器

`development/skill/<name>/` 是受管 Skill 的唯一源码根。部署时只允许复制/同步一个 `status: active` Skill 的完整目录；其 adapter/profile/reference/script 均随 owner skill 根一起部署，adapter 不单独安装。Skill 内所有相对路径继续以自身目录为根，正文不得硬编码 `.codex/skills/...`、`.agents/skills/...` 等具体安装位置。

部署目标由消费环境决定，例如用户级 Codex skill root 或项目级 agent skill root；P3 文档只说明映射关系，不选择某一种物理机制作为平台真理。copy、受控同步或未来的 deploy tool 均可实现该约定，只要部署后目录结构与 source skill root 保持语义等价，且运行不需要 `references/`。planned Skill/Adapter、source reference、开发计划和 validation tools 均不进入 runtime skill payload。

P3 不使用 junction/symlink 作为规范要求，也不规定 backup/rollback 的具体实现；这些是未来 deploy manager 的 operation contract。当前阶段只定义：部署来源、允许部署的 lifecycle state、dependency 一并满足、owner-contained adapter/profile 规则，以及部署后 self-reference 必须仍有效。

## §3 Manifest v2 定稿目标

实施时将 `development/skill/manifest.yaml` 升为 schema v2。目标形状如下；具体 description 可在不改变语义的前提下微调，但字段与状态关系不得弱化：

```yaml
schema_version: 2

sources:
  - id: spinecodex-skills-upstream
    path: references/SpineCodex-skills
    kind: upstream-snapshot
    required: false
    version: "2026-08-25"
    description: Read-only architecture reference from the upstream Codex skill set.
  - id: recycling-company-investigation-reference
    path: references/customer-research-skills/recycling-company-investigation
    kind: local-reference
    required: false
    version: "2026-08-25"
    description: Read-only source skill used to derive research-investigation.
  - id: access-vba-dev-reference
    path: references/access-vba-dev
    kind: local-reference
    required: false
    version: "2026-08-25"
    description: Read-only source skill used to derive runtime-ops and vba-office.

skills:
  - name: research-investigation
    path: development/skill/research-investigation
    status: active
    scenarios: [wsl-python]
    deps: []
    composed_of: []
    entrypoint: true
    version: "0.1.0"
    description: Domain-neutral research investigation framework.
  - name: runtime-ops
    path: development/skill/runtime-ops
    status: active
    scenarios: [win-access-vba]
    deps: []
    composed_of: []
    entrypoint: true
    version: "0.1.0"
    description: Host-neutral runtime operations framework.

adapters:
  - name: vba-office
    path: development/skill/runtime-ops/adapters/vba-office.md
    status: active
    owner_skill: runtime-ops
    environments: [win-access-vba]
    version: "0.1.0"
    description: Microsoft Office VBA runtime adapter.
  - name: sql-server
    path: development/skill/runtime-ops/adapters/sql-server.md
    status: planned
    owner_skill: runtime-ops
    environments: [win-access-vba]
    version: "0.1.0"
    description: Planned SQL Server runtime adapter.
  - name: android-gradle
    path: development/skill/runtime-ops/adapters/android-gradle.md
    status: planned
    owner_skill: runtime-ops
    environments: [win-android]
    version: "0.1.0"
    description: Planned Android and Gradle runtime adapter.
  - name: wsl-python
    path: development/skill/runtime-ops/adapters/wsl-python.md
    status: planned
    owner_skill: runtime-ops
    environments: [wsl-python]
    version: "0.1.0"
    description: Planned WSL Python runtime adapter.
```

`source.kind` 首版允许 `{upstream-snapshot, local-reference}`；P3 不为未来来源类型预造复杂 taxonomy。`required: true` 语义保留给未来确实必须存在的设计/生成输入，但当前三个 reference 均为 false。sources path 只允许 repo-relative、不得逃逸 repo root；optional source 不存在时不报错，存在但不是目录时失败。

## §4 `validate_skills.py` 扩展规格

P3 保留当前 CLI 主入口 `py development/tools/validate_skills.py [--manifest PATH]`、exit code 与 JSON/stdout + stderr 约定。report 在不删除旧字段的基础上增加 `sources_checked`、`adapters_checked`、`routes`，使 existing consumers 仍可读取 `ok / manifest / skills_checked / errors`。schema v1 不再作为当前 repo manifest 的合法版本；是否保留纯函数层面对 v1 fixture 的兼容不是目标，测试应迁移到 v2。

新增/调整 gate 至少覆盖以下稳定错误类别；具体内部函数拆分可由实施者选择，但错误语义不得模糊：

| 范围 | 必须检测 | 建议错误码 |
| --- | --- | --- |
| Manifest | schema != 2；sources/skills/adapters 类型错误 | `SCHEMA_VERSION_UNSUPPORTED`, `MANIFEST_SECTION_TYPE` |
| Sources | duplicate id；非法/逃逸 path；required source 缺失；存在但非目录 | `DUPLICATE_SOURCE_ID`, `SOURCE_PATH_INVALID`, `SOURCE_PATH_MISSING`, `SOURCE_NOT_DIRECTORY` |
| Skill refs | unknown deps/composed_of；active target 非 active；self-edge/cycle | `DEP_UNKNOWN_REF`, `DEP_NOT_ACTIVE`, `DEP_CYCLE`, `COMPOSED_OF_UNKNOWN_REF`, `COMPOSED_OF_NOT_ACTIVE`, `COMPOSED_OF_CYCLE` |
| Entrypoint | active entrypoint metadata 缺失/非法；prompt 无 `$name` | `ENTRYPOINT_METADATA_MISSING`, `ENTRYPOINT_METADATA_INVALID`, `ENTRYPOINT_PROMPT_NO_TRIGGER` |
| Adapter registry | owner unknown；active owner 非 active；active path missing | `ADAPTER_OWNER_UNKNOWN`, `ADAPTER_OWNER_NOT_ACTIVE`, `ACTIVE_ADAPTER_PATH_MISSING` |
| Adapter ABI | schema/id/env/capability/task_modes/verification/mutation/recovery 不合法 | `ADAPTER_SCHEMA_VERSION_UNSUPPORTED`, `ADAPTER_ID_MISMATCH`, `ADAPTER_ENVIRONMENTS_INVALID`, `ADAPTER_CAPABILITIES_INVALID`, `ADAPTER_CAPABILITY_DUPLICATE`, `ADAPTER_TASK_MODES_INVALID`, `ADAPTER_VERIFICATION_KIND_INVALID`, `ADAPTER_MUTATION_SUPPORT_INVALID`, `ADAPTER_RECOVERY_SECTION_MISSING` |
| Routing | manifest environment 与 adapter frontmatter 不一致；scenario 无任何登记 | `ADAPTER_ENVIRONMENT_MISMATCH`, `SCENARIO_UNROUTED` |

现有 Research Profile gate 原样保留其 ownership 边界：只对 `research-investigation` 的 `profiles/*.yaml` 执行，不泛化到所有含 `profiles/` 的 Skill。P3 不能因 manifest 重构破坏 P1 的 closed ABI、unknown routing、binding ownership 等回归。

Adapter frontmatter 解析可以复用现有 YAML frontmatter 基础设施，但必须支持 nested `task_modes` mapping；不能沿用只理解平铺 Skill frontmatter 的简化解析假设。Recovery section 的机械检查只确认非空结构段存在，例如匹配 `## 7. Recovery model` 或语义等价 heading；它不能证明 recovery 方法真的可用。真实可恢复性仍由 adapter 内容审阅和运行时证据负责。

`routes` report 至少对三个 scenario 给出 active/planned targets，区分 Skill 和 Adapter，避免调用方把 planned 当 active。例如结构可为：

```json
{
  "win-access-vba": {
    "skills": [{"name": "runtime-ops", "status": "active"}],
    "adapters": [
      {"name": "vba-office", "status": "active", "owner_skill": "runtime-ops"},
      {"name": "sql-server", "status": "planned", "owner_skill": "runtime-ops"}
    ]
  }
}
```

report 的 exact ordering 应确定性排序，保证测试与人工 diff 稳定。

## §5 Agent metadata 与路由文档

### §5.1 `agents/openai.yaml`

两个 active entrypoint 均新增 metadata，形状：

```yaml
interface:
  display_name: <human-readable name>
  short_description: <bounded description>
  default_prompt: <prompt containing $skill-name>
```

`research-investigation` 的 default_prompt 只负责提示加载 `$research-investigation` 并选择适用 profile，不内联 recycling 业务词。`runtime-ops` 的 default_prompt 只负责提示加载 `$runtime-ops`、选择 matching adapter、按 capability/verification/recovery contract 行事，不把 `vba-office` 当默认宿主。这样 agent routing 与 P1/P2 Core purity 保持一致。

### §5.2 `development/docs/scenario-routing.md`

该文档只解释当前 route projection，不成为配置源。至少包含以下决策：

| Scenario | Intent / control plane | Current route | State |
|---|---|---|---|
| `win-access-vba` | host/tool mutation, inspect, test | `runtime-ops` + `vba-office` | active |
| `win-access-vba` | SQL Server runtime operations | `runtime-ops` + `sql-server` | planned; no adapter capability yet |
| `win-android` | Android/Gradle runtime operations | `runtime-ops` + `android-gradle` | planned; no adapter capability yet |
| `wsl-python` | evidence-first external investigation | `research-investigation` + selected profile | active |
| `wsl-python` | WSL/Python runtime operations | `runtime-ops` + `wsl-python` | planned; no adapter capability yet |

文档必须明确 scenario 不是自动选择器：真实任务还要按 intent、profile/adapter applicability、live tool availability 决策。planned route 只表示注册计划，不授权 tool call。

## §6 部署约定章节

P3 在 `development/docs/repo-conventions.md` 增加 `Deployment and Runtime Mapping` 章节，避免新建第二份部署规范。内容至少固定：

1. Source of truth：`development/skill/<name>/`；只有 manifest `skills[].status: active` 可部署。
2. Payload boundary：部署整个 Skill 根目录；其 `agents/`, `references/`, `profiles/`, `adapters/`, `scripts/` 按实际存在随根一起进入 payload；平台 `development/tools/`、plans、source references 不进入。
3. Owner rule：adapter 永远随 owner Skill 部署，不成为顶层独立 Skill；profile 同理归 owner Skill。
4. Dependency rule：部署一个 active Skill 前，其 `deps[]` 必须已处 active 且一并满足目标环境；`composed_of[]` 的 active child 也必须可发现。
5. Path rule：Skill 内只使用相对自身目录的路径；具体 target root 可以是用户级或项目级，由外部部署动作选择。Skill 本体不得知道自己最终位于 `.codex/skills` 还是 `.agents/skills`。
6. Self-containment：目标环境不存在 `references/` 时，active Skill 仍必须具有作出正确运行决策所需内容；source provenance 可缺席。
7. Planned exclusion：planned Skill/Adapter 不进入正常 runtime payload，也不得因目录偶然存在而被称为 active。
8. P3 limit：本阶段不定义 copy/symlink/junction/atomic replacement/rollback 的具体实现；这些属于未来 deploy manager contract。

`repo-conventions.md` 当前仍称项目为 “scaffolding stage”，P3 实施后该表述会失准，必须同步改为能忠实反映 P0-P3 已形成 control platform 的描述。根 `README.md` 当前“项目刚刚开始，还未确定架构”也将在 P3 实施后失真，因此 implementation commit 必须同步更新其 Current Status，但只写稳定现状，不复制本计划细节。

AGENTS.md Documentation Map 已经存在 `plans/` 行，因此 skeleton 所写“若此前未加”条件已经满足，不需机械重复添加。同阶段新增 `scenario-routing.md` 后，若它成为 agent 正确路由所需的稳定入口，则在 Documentation Map 增一行；否则保持 `repo-conventions.md` 为条件阅读入口，避免 AGENTS 膨胀。实施时以“是否会改变 agent 路由决策”为准。

## §7 测试计划

P3 继续使用 pytest，不引入新测试框架。至少扩展 `development/tools/test_validate_skills.py` 并新增一份控制集成回归 `development/tools/test_control_integration_p3.py`；若实现者能在不降低可读性的前提下合并，文件名可调整，但下列行为必须被锁定。

### §7.1 Manifest v2 / source tests

- real manifest v2 全绿；
- optional source 缺席仍绿；
- required source 缺席失败；
- source path 逃逸 repo root 失败；
- duplicate source id 失败；
- reference id 与 future skill name 不共享命名域，二者可并存且不触发 duplicate skill name。

### §7.2 Dependency / composition tests

- unknown dep / composed_of 均失败；
- active skill 依赖 planned skill 失败；
- planned skill 依赖 planned skill 合法；
- self-dependency/self-composition 失败；
- dependency cycle 与 composition cycle 分别失败；
- disposable orchestrator 的 `composed_of` 正常解析 active worker。

### §7.3 Agent metadata tests

- active `entrypoint: true` 无 `agents/openai.yaml` 失败；
- interface 字段缺失或非字符串失败；
- default_prompt 不含 `$<name>` 失败；
- `entrypoint: false` 不要求 metadata；
- 两个 real active Skill 的 metadata gate 全绿。

### §7.4 Adapter gate tests

- real `vba-office.md` 通过；
- schema version 错、adapter/file stem 不一致、environments 空、capability 重复、task_modes.closed 缺失、verification kind 非法、mutation_support 非法分别失败；
- manifest environments 与 frontmatter 不一致失败；
- mutating adapter 缺 Recovery model section 失败；
- `mutation_support: none` 不强制 Recovery model；
- planned adapter 文件不存在合法；planned adapter 文件一旦存在则执行 gate；
- active adapter owner planned/unknown 失败；
- synthetic `independent_checks` + transaction rollback adapter 能在不改 Core gate 的情况下通过，继续兑现 P2 orthogonality。

### §7.5 Routing tests

- `{win-access-vba, win-android, wsl-python}` 三场景全部有 registry coverage；
- route projection 对 active/planned 状态不混淆；
- `win-android` 在 `android-gradle` planned 时不得出现 active adapter；
- `wsl-python` 同时可存在 active research Skill 与 planned runtime adapter，projection 保留两者而不强制唯一 route；
- route 输出排序稳定。

### §7.6 P1/P2 preservation

现有 `test_research_investigation_p1.py` 全部继续通过；Profile gate 仍只约束 `research-investigation`；P1 Core purity 与 unknown placement 不变；P2 `vba-office` 工具/verification/recovery 语义不因 registry 重构被改写。P3 只给它们加控制层，不借机重写 Core。

## §8 一次性 Growth-loop E2E probe

对应 skeleton 的 `register → validate → route → 验证后移除` 验收，P3 不在真实 `development/skill/` 留临时目录，而在 pytest `tmp_path` 构造一次性平台树。probe 至少含 `probe-worker` 与 `probe-orchestrator` 两个 Skill：worker 为 active entrypoint false；orchestrator 为 active entrypoint true，`composed_of: [probe-worker]`，携带合法 `agents/openai.yaml`；二者映射到一个现有 scenario。步骤固定为：

1. register：把 probe Skill 写入临时 manifest v2；
2. validate：完整 validator 返回 green；
3. route：route projection 中能找到 orchestrator/worker 的预期 scenario 和 active 状态；
4. composition：orchestrator 的 composed_of edge 解析到 active worker，无 cycle；
5. negative activation：把 worker 改 planned、orchestrator 仍 active，validator 必须因 `COMPOSED_OF_NOT_ACTIVE` 失败；
6. restore/remove：恢复合法状态后删除 probe entries/directories，再次验证临时基础树 green。

该 probe 既证明 growth loop，又满足 skeleton 的 orchestrator composition 要求，不向正式 catalog 增加没有实际用户任务的永久 Skill。

## §9 实施顺序

P3 实施按依赖顺序进行，避免同时改变 schema、validator、docs 后无法定位回归：

1. Baseline：确认当前 HEAD、cleanliness，运行现有 validator 与 pytest，记录 P0-P2 绿色基线。
2. Manifest v2 parser：先扩 validator 支持 v2 sections 与 source/skill 基础结构，再迁 real manifest；迁移过程中不改变两个 active Skill 的业务 contract。
3. Source split：把原三个 external skill entry 迁到 `sources[]`，设置 optional，确认 reference 缺席 fixture 仍 green。
4. Adapter registry + gate：登记 `vba-office` active 与三个 planned adapter，实施 `adapter_errors()`、owner/environment/recovery gate；real VBA adapter 必须通过。
5. Lifecycle edges：补 deps/composed_of active-state、self-edge 与 cycle gate。
6. Entrypoint routing：为两个 active Skill加 `entrypoint: true` 和 `agents/openai.yaml`，实施 metadata gate。
7. Route projection：实现三场景 coverage/projection 与 deterministic report，补 scenario tests。
8. E2E probe：加入 disposable worker/orchestrator growth-loop regression。
9. Docs sync：新增 `scenario-routing.md`，更新 `repo-conventions.md` deployment/runtime mapping 与已过期 scaffolding 描述；同步 README Current Status；AGENTS.md 仅在确有路由阅读价值时增加文档入口。
10. Final validation：运行 validator、P3 targeted tests、现有 P1/P2 tests、全 pytest；审查 Git diff 确认没有 reference 内容、planned adapter stub、deploy manager 或旧 Skill 迁移混入。

任何一步出现必须修改 P1 evidence semantics、P2 verification/recovery semantics、扩大 scenario enum、实现新 host adapter 或编写安装器才能继续的情况，应停止 P3 扩张并记录为后续计划，不在本阶段顺手解决。

## §10 验收标准

P3 只有在以下条件同时满足时才可从 `executing` 改为 `done`：

1. `manifest.yaml` 已为 schema v2，`sources / skills / adapters` 三个身份面分离；三个 ignored reference 即使不在 fresh clone 中，也不会使 validator 失败。
2. 两个正式 Skill 仍为 active，P1/P2 contract 与回归保持；两个 active entrypoint 的 `agents/openai.yaml` 通过 metadata gate。
3. `vba-office` 已登记 active，并通过机械 Adapter Contract gate；三个 skeleton planned adapter 已登记但没有伪造实现文件或 capability。
4. active Skill 的 deps/composed_of 必须解析 active target，cycle/self-edge 可机械拒绝；正式 catalog 不因演示目的增加无实际需求 orchestrator。
5. 三个 scenario 的 route projection 完备并明确 active/planned；planned adapter 不被报告成 active runtime capability。
6. `repo-conventions.md` 明确 deployment/runtime mapping：只部署 active Skill 根、owner-contained extension、self-relative path、reference-independent；本阶段未实现自动 deploy manager。
7. disposable growth-loop probe 完成 register → validate → route → composition/activation negative gate → remove，并在移除后恢复 green。
8. `py development/tools/validate_skills.py` exit 0；P3 targeted tests 全绿；现有 P1/P2 regressions 全绿；全仓 pytest 全绿。
9. README/repo-conventions 不再把已进入 P3 的平台描述成“刚开始/架构未确定/scaffolding only”；文档不声称尚未实现的安装管理、SQL/Android/WSL adapter 已可用。
10. Git diff 只包含 P3 控制集成所需平台文件；`references/**` 保持 read-only 且不因 P3 被纳入版本内容。

失败条件：若 optional reference 缺失仍会阻塞平台 validation；若 active adapter 能绕过 contract gate；若 planned adapter 被 route 成 active；若 Skill 部署后仍需回读 `references/`；若为了 route completeness 必须虚构 permanent Skill/adapter；若 P3 引入 install/update/rollback runtime 而无独立 operation/recovery contract；上述任一成立，P3 不得标 `done`。

## §11 与旧 Skill 迁移及试用阶段的关系

P3 完成是“平台级受控试用”的前置门槛，但不等于旧 Skill 已迁移。当前已安装的 `access-vba-dev`/`vba-skill` 与项目内 `recycling-company-investigation` 仍应保持原状，直到另立迁移计划完成 capability/knowledge parity、部署目标、共存/退役和 rollback 方案。P3 的 source/skill 身份分离专门为后续迁移解除名称冲突：reference 可继续以 `*-reference` 身份存在，而未来正式受管 Skill 可以使用真正的 runtime 名称。

P3 结束后可开始 Alpha：先把 `research-investigation` 与 `runtime-ops` 作为平台 source-of-truth 做非破坏性部署试验，与旧 Skill 并存；观察 discovery、上下文负载、route 选择和 contract 行为。只有在后续迁移计划证明功能没有回退后，才退役旧安装目录。自动安装、更新、drift detection、rollback snapshot 若确认有长期价值，应单独形成 P4/后续计划，不在 P3 预实现。

## §12 与上位计划的解释优先级

`000-platform-skeleton.md §4 P3` 是范围上位约束，本计划只细化其“manifest 覆盖全部条目含 planned adapters、scenario 路由、组合边、lifecycle gate、部署约定、E2E growth loop”。其中 manifest v2 的 `sources / skills / adapters` 分离，是为兑现 skeleton 的“注册表覆盖一切”且解决 P0 v1 在 P3 已暴露的身份冲突，并不改变 P1/P2 framework ABI。

若本计划与 P0 的 manifest v1 字段布局存在差异，以 P3 schema v2 作为当前实施目标；P0 文件继续记录其阶段历史，不回写成 v2。若本计划与 P1/P2 的领域 contract、evidence semantics、adapter semantics 冲突，则 P1/P2 精细计划和已通过的 contract tests 优先，P3 只能调整控制层实现，不能借 schema 升级重定义下层语义。
