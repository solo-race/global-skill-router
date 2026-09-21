# P5 Gradle / Kotlin Runtime Integration 与路由架构修复 — 精细实施计划

Status: done
Date: 2026-09-20
Depends-on: 000-platform-skeleton, 030-p2-runtime-ops, 040-p3-control-integration, 050-p4-selective-discovery-deployment

> Status 生命周期：`draft → approved → executing → done`。被取代的计划保留状态 `superseded`，永不删除。Status 字段是本文件唯一事实源。

## §1 目标、当前基线与完成边界

本阶段解决两个相互关联的问题。

第一，`win-android` 已在 manifest 中预留 `runtime-ops + android-gradle` 扩展位，但 `android-gradle` 仍为 planned，Codex 在实际 Gradle/Kotlin 项目中只能临时拼接 wrapper、task、测试、诊断与依赖命令。该路径重复消耗上下文，容易猜错 task path、wrapper、Gradle/Kotlin 版本和失败解释。本阶段要把成熟的 Gradle MCP/Agent Skill 设计吸收进正式 runtime adapter，并把 Kotlin 官方 Agent Skills 中与当前场景有关的知识提炼为独立 managed module。

第二，P4 的部署路由只把 `skills[]` 写进 scenario shard；validator 虽已持有 `scenario → adapters[]` 关系，运行时 payload 却丢失 adapter 映射。当前只有一个 active adapter 时问题不明显，但一旦 `android-gradle` 激活，`runtime-ops` Core 将要求 agent “选择正确 adapter”，部署后的 route 却不给权威候选路径，迫使模型扫描目录或猜测。P5 必须同时修复该架构缺口。

P5 完成后应满足：

1. Codex 在实施开始时自行从 GitHub 拉取两个设计来源到 `development/skill-repos/`，以本地 checkout 为分析输入，而不是依赖聊天摘要：
   - `https://github.com/rnett/gradle-mcp.git`
   - `https://github.com/Kotlin/kotlin-agent-skills.git`
2. 两个 checkout 均登记为 optional `development-repository` source，记录真实 origin 与实施时观测到的精确 `pinned_ref`；source checkout 不进入部署 payload。
3. `runtime-ops/adapters/android-gradle.md` 从 planned 变成 active，工具名、签名、失败语义和调用规则必须由本地 `gradle-mcp` checkout 与 live provider catalog 取证，不凭经验猜测。
4. `runtime-ops` 正式覆盖 `win-android`；Gradle 具体规则留在 adapter，Core 不吸收构建系统细节。
5. route payload 能把 active adapter 的 owner、selector/description 与 `adapter_path` 一并送到运行时，使 router/Core 不需要扫描 `adapters/`。
6. Kotlin 官方仓库只作为来源。选择性重建一个轻量 managed Kotlin module，负责 Kotlin tooling/toolchain/migration 等语义；不整仓复制，不把第三方 plugin marketplace 当作本平台部署依赖。
7. 部署后即使 `development/skill-repos/` 整体不存在，managed router + modules 仍完全可运行。
8. 现有 VBA 路由、deployment plan/apply/verify/rollback 与全量测试保持通过。

非目标：

- 不修改 Gradle、Kotlin、Codex 上游源码。
- 不把 `gradle-mcp` server 源码 vendoring 到 managed Skill。
- 不把 `Kotlin/kotlin-agent-skills` 整仓部署到 `global-skill-router/library/`。
- 不新增第四个 generic JVM scenario；P5 继续使用既有固定 vocabulary `{win-access-vba, win-android, wsl-python}`。若未来要覆盖非 Android JVM/Gradle 项目，另立 scenario/schema migration。
- 不把 publish/release/upload/deploy 等高影响 Gradle task 因“能执行 task”而自动视为安全。
- 不要求 shell fallback 在 MCP 不可用时伪装成 MCP 等价能力；任何 fallback 必须在 adapter 中明确声明边界。
- 不在本计划阶段直接部署到用户级 Codex skill root；实施完成后先在受控 target root 验证。

## §2 架构决策 G1–G12

### G1 — Source-first：先本地化上游，再写正式合同

P5 的第一项实施动作必须是由执行 Codex 自己完成 Git checkout。禁止只根据本计划、聊天记录或 GitHub 搜索摘要直接编写 `android-gradle.md` 或 Kotlin module。

目标目录固定为：

```text
development/skill-repos/
├── development-delegation-loop-repo/
├── gradle-mcp/
└── kotlin-agent-skills/
```

`development/skill-repos/*` 已由根 `.gitignore` 排除，仅 `.gitkeep` 纳入主仓；因此两个上游 checkout 保持独立 Git 边界，与现有 development-delegation source-library 模式一致。

### G2 — Checkout 必须验证 identity，不能“目录存在即信任”

首次获取使用上游 canonical URL。若目录已存在，执行者不得删除、覆盖或直接 `git pull`；必须先验证：

- `git remote get-url origin` 与预期 canonical origin 一致；
- `git rev-parse HEAD` 可解析；
- worktree 没有无法解释的本地修改；
- 当前 checkout 足以读取所需 Skill/server/documentation 文件。

推荐首次流程：

```powershell
git clone https://github.com/rnett/gradle-mcp.git development/skill-repos/gradle-mcp
git clone https://github.com/Kotlin/kotlin-agent-skills.git development/skill-repos/kotlin-agent-skills

git -C development/skill-repos/gradle-mcp remote get-url origin
git -C development/skill-repos/gradle-mcp rev-parse HEAD

git -C development/skill-repos/kotlin-agent-skills remote get-url origin
git -C development/skill-repos/kotlin-agent-skills rev-parse HEAD
```

如果仓库已存在且 identity 正确，可先 `git fetch --prune origin`；是否更新到上游新 commit 必须是显式实施决策。正式分析开始后，将实际使用的 commit SHA 记入 manifest `pinned_ref`，并保持该分析批次稳定，不在中途静默跟随 upstream。

如果 origin 不匹配、checkout 脏且来源不明、fetch 失败或 GitHub 不可达，停止 source-dependent 实施并报告 blocker；不得拿另一个相似仓库顶替。

### G3 — 两个来源的职责严格分离

`rnett/gradle-mcp` 是 Gradle runtime/tool-contract 设计来源，回答“怎样发现、调用、诊断和解释真实 Gradle build”。

`Kotlin/kotlin-agent-skills` 是 Kotlin 语义/工作流设计来源，回答“怎样处理 Kotlin tooling、toolchain、migration 等 Kotlin-specific 决策”。

边界：

```text
global-skill-router
  ├─ runtime-ops
  │    └─ android-gradle adapter
  │          └─ Gradle MCP / bounded wrapper fallback
  └─ kotlin-tooling
       └─ selected Kotlin-specific guidance
```

Kotlin module 不复制 Gradle 执行 ABI；Gradle adapter 不承担 Kotlin 语言知识库职责。一个任务确实同时需要运行时执行与 Kotlin 专项判断时，router 才加载两者。

### G4 — 激活已有 android-gradle 扩展位，不新造顶层 gradle-runtime Skill

现有架构已经在 manifest 中登记：

```text
runtime-ops/adapters/android-gradle.md
status: planned
owner_skill: runtime-ops
environments: [win-android]
```

P5 必须沿用这一 ABI。禁止新增另一个顶层 `gradle-runtime` Skill 与 `runtime-ops` 平行竞争。

激活时同步把 `runtime-ops.scenarios` 从：

```yaml
scenarios: [win-access-vba]
```

改为：

```yaml
scenarios: [win-access-vba, win-android]
```

否则 deploy route generator 不会把 `runtime-ops` 投影到 `win-android`。

### G5 — 修复 route payload：adapter 成为 scenario shard 的一等映射

P4 当前 route shard 只持有 skill candidate：

```yaml
scenario: win-android
skills: []
```

P5 将 route payload contract 升级，使每个 module candidate 可携带该 scenario 下属于它的 active adapters：

```yaml
scenario: win-android
skills:
  - name: runtime-ops
    description: <bounded module description>
    skill_path: library/runtime-ops/MODULE.md
    status: active
    adapters:
      - name: android-gradle
        description: <bounded adapter selector>
        adapter_path: library/runtime-ops/adapters/android-gradle.md
        status: active
```

规则：

- 只投影 `status: active` adapter；
- adapter 必须属于当前 skill owner 且 environment 包含当前 scenario；
- `adapter_path` 必须位于 owner module 的 `adapters/` 下；
- planned adapter 不进入可执行映射；
- adapter 排序确定性；
- route shard 不复制 adapter body、工具签名或 operation 列表；
- 同一 scenario/owner 出现多个 active adapter 时，agent 只根据 bounded description + 当前任务证据选择；仍不允许扫描目录；
- 无唯一匹配时报告 route/adapter ambiguity，不猜。

这不是第二份 registry：route shard 仍由 manifest 派生，manifest 是 authority。

### G6 — Route contract 升级必须显式版本化并保留旧安装可诊断性

由于 shard 结构是 deployment runtime contract，P5 应把当前 route index schema 从 v2 升到 v3，而不是无版本改变地扩字段。

实施要求：

- deploy 只生成 v3；
- route validator 严格验证 v3 的 nested adapter shape、path、owner closure、status 与文件存在性；
- 旧 v1/v2 payload 仍可被识别为 legacy，用于 verify/rollback/升级诊断，不把旧 shard 误按 v3 解释；
- 安装新 payload 后，deployment-state hash 应自然反映 route 文件变化；
- 同一 manifest 必须产生字节稳定 route 输出。

### G7 — Router 与 runtime-ops 只消费派生映射，不扫描 source/library

`global-skill-router/SKILL.md` 增补最小规则：

1. scenario 已解析后只读一个 shard；
2. 选择 module 后，如果 candidate 带 adapter mapping，保留该 bounded mapping 作为 module adapter selection evidence；
3. 加载 `library/<module>/MODULE.md`；
4. 对 runtime-ops，只加载 route mapping 指向的匹配 adapter；
5. 不扫描 `library/` 或 `adapters/`，不回读 manifest/source repo。

`runtime-ops/SKILL.md` 的 Adapter routing 同步明确：在 managed routed payload 中，优先使用 router 提供的 manifest-derived adapter path；不得通过文件存在猜 adapter。非 routed standalone 使用时仍必须通过显式任务/环境证据建立 adapter identity。

### G8 — Gradle adapter 采用 MCP-first、wrapper-bounded-fallback

正式 `android-gradle.md` 的 provider 主路径是从本地 `gradle-mcp` checkout 取证得到的真实 MCP surface。MCP 在线时：

- 优先使用结构化 project/task discovery；
- 优先使用结构化 execution/test/problem/dependency 结果；
- 不为同一信息重复跑裸 `gradlew tasks`、grep console 或手写长 shell pipeline；
- 不猜 task path、module、Gradle version、Kotlin version；
- version-sensitive 事实优先从 wrapper/project/provider 查询得到。

如果目标 Codex 环境没有 Gradle MCP，而本地 project wrapper 可执行，可在 adapter 中定义一个**短、固定、wrapper-only** fallback protocol，但只能在源分析后落地。fallback 至少满足：

- 使用项目自己的 `gradlew.bat` / wrapper，不使用全局 Gradle 代替；
- 先获取最小必要 task/project evidence，再执行目标 task；
- 不生成无关的“雷霆参数串”；
- 保留原始 exit code 与关键失败输出；
- shell fallback 的证据强度不得伪装成 provider structured diagnostics；
- provider unavailable 时明确报告 degraded mode。

如果实施时确认无法写出稳定、短且可验证的 fallback，则宁可不声明该 capability，也不得凭经验补齐。

### G9 — Gradle task execution 不等于低风险 mutation

Gradle task 可以由项目任意定义；`build`、`test` 常见但并不证明所有 task 无外部副作用。adapter 必须对 task execution 设 safety boundary。

默认可自动运行的 task 类型只限可由项目语义合理判定为本地 build/test/check/compile/inspection 的范围。以下意图默认需要显式用户授权和额外 precondition：

- publish / upload / release；
- deploy / install 到外部设备或远端；
- signing / credential-dependent distribution；
- production migration；
- 删除或覆盖项目外部状态的自定义 task；
- 任何 provider 报告或项目文档表明具有高 blast radius 的 task。

未知自定义 task 不因名字看起来 harmless 就自动执行。无法判定 side effect 时先做 discovery/analysis。

### G10 — Gradle adapter 的 verification model 必须反映构建事实，而非沿用 VBA 三档

P5 不复制 `Static < Compile < Runtime`。目标模型优先考虑 `partial_order` 或 `independent_checks`，最终形状由 source inspection 后确定。

最低需要区分：

- project/configuration resolved；
- requested build/task succeeded；
- requested tests passed；
- target runtime/preview/repl exercised（仅 provider 真有对应能力时）。

不得从“build succeeded”推导“tests passed”，也不得从“tests passed”推导 UI/runtime 行为正确。每个 state 的 required evidence 必须来自 provider result、wrapper result 或明确 observation。

### G11 — Kotlin 官方 Skills 选择性重建为 managed module

预期新增：

```text
development/skill/kotlin-tooling/
├── SKILL.md
├── agents/openai.yaml
└── references/
    └── <only selected decision-changing material>
```

最终名称若 source inspection 证明另一个 slug 更准确，可在实施时调整，但必须保持单一职责：Kotlin tooling/toolchain/migration 等 Kotlin-specific 决策。

manifest 预期属性：

```yaml
status: active
deployment_role: module
routing_scope: scenario
scenarios: [win-android]
entrypoint: true
```

并加入 `global-skill-router.composed_of[]`。

禁止整仓复制；只移植真正改变 agent decision 的内容。上游已有 Skill 若只是原生 Codex plugin packaging、安装说明或与本平台 routing 重复，则不复制。所有引用内容需先检查 source license；若 license/attribution 不支持直接复制文本，则只重建抽象规则并记录 provenance。

### G12 — Source repo 只服务开发，部署必须自足

两个 `development-repository` source 均 `required: false`。正式 managed adapter/module 完成后，验证必须包含一个 source-independence 检查：在不读取 `development/skill-repos/*` 的条件下，validator、payload build 和 controlled deploy 仍成功。

任何运行时必要事实若只存在 source repo 而未进入 managed artifact，视为 P5 未完成。

## §3 Phase A — 上游获取、固定与分析

### A1. Clone / fetch 两个来源

由执行 Codex 自己运行 Git 操作，不要求用户手工下载。

完成条件：

- `development/skill-repos/gradle-mcp/.git` 存在；
- `development/skill-repos/kotlin-agent-skills/.git` 存在；
- origin 与 canonical URL 一致；
- 记录每个 checkout 的 HEAD SHA；
- 主仓 `git status` 不因 nested checkout 内容出现大量 tracked 文件。

### A2. 将 source identity 写入 manifest

新增两条 `sources[]`，格式沿用 `development-delegation-loop-reference`：

```yaml
- id: gradle-mcp-reference
  path: development/skill-repos/gradle-mcp
  kind: development-repository
  required: false
  origin: https://github.com/rnett/gradle-mcp
  pinned_ref: <observed full commit SHA>
  version: "<implementation date or upstream release if authoritative>"
  description: Local source repository for Gradle MCP runtime and Agent Skill design.

- id: kotlin-agent-skills-reference
  path: development/skill-repos/kotlin-agent-skills
  kind: development-repository
  required: false
  origin: https://github.com/Kotlin/kotlin-agent-skills
  pinned_ref: <observed full commit SHA>
  version: "<implementation date or upstream release if authoritative>"
  description: Local source repository for Kotlin official Agent Skill design.
```

不得在计划里预填猜测 SHA；实施时写真实值。

### A3. Gradle source evidence packet

至少检查并记录：

- README / install/configuration；
- MCP server 的 tool registration/source-of-truth；
- `using-gradle`、`authoring-gradle-builds`、dependency/runtime 相关 Skills；
- wrapper/version/task discovery 规则；
- execution/test result shape；
- structured problems/failures；
- dependency graph / conflict / update semantics；
- Kotlin REPL、Compose preview 或 runtime-related 能力（若存在）；
- timeout/async handle 规则；
- Windows 路径或 wrapper 行为；
- license。

输出不是新的长文档优先；应把需要进入 adapter 的事实直接映射到 contract 十部分草稿，并把“不采用的上游规则”记成短 decision list。

### A4. Kotlin source evidence packet

至少检查：

- 仓库 Skill 目录与触发方式；
- 与 Gradle、Kotlin Toolchain、AGP migration、Kotlin tooling 直接相关的 Skill；
- 哪些规则是 Kotlin-specific，哪些只是通用 Gradle execution；
- 是否依赖上游 plugin packaging、脚本或外部路径；
- license / attribution；
- 哪些内容会真实改变 `win-android` agent decision。

结果必须明确列出：adopt / adapt / reject。不能因为是 Kotlin 官方仓库就整包吸收。

### A5. Source gate

A3/A4 未完成前不得进入正式 adapter/module 写入。发现 upstream API 与前期假设不一致时，以 checkout + live provider 为准，修改计划实施细节，不强行套聊天结论。

## §4 Phase B — route adapter 架构修复

这一 phase 应先于激活 `android-gradle`，避免新 adapter 上线后 runtime 仍没有确定性选择路径。

### B1. 扩展 deploy route generation

修改 `development/tools/deploy_skills.py`：

- 构建 `active_adapters_by_owner_scenario`；
- 每个 scenario skill candidate 只附带归属于自身的 active adapters；
- 生成 bounded `description` 与相对 `adapter_path`；
- 路径只能指向已复制的 active adapter；
- deterministic sort；
- planned adapter 仍由 copy filter 排除。

### B2. route schema v3 validation

扩展 route payload validation，至少拒绝：

- adapter entry 缺字段；
- 非 active status；
- owner 与 enclosing skill 不一致；
- adapter environment 不含 shard scenario；
- `adapter_path` 越出 `library/<owner>/adapters/`；
- 文件不存在；
- duplicate adapter name/path；
- planned adapter 被投影为 executable；
- v3 shard 含未知字段或非法 shape。

旧 v1/v2 识别逻辑保持显式，不把 legacy 默默升级成 v3。

### B3. Router/Core contract 对齐

修改：

- `development/skill/global-skill-router/SKILL.md`
- `development/skill/runtime-ops/SKILL.md`

只加入 route-to-adapter 选择规则，不把具体 Gradle/VBA adapter 名硬编码到 Core。

### B4. 架构回归

更新 `test_deploy_skills.py` 与必要的 control integration tests，先用 synthetic adapters 证明：

- 一个 scenario 一个 adapter；
- 同 scenario 同 owner 多 adapter；
- 不同 owner adapter 不串线；
- planned adapter 不输出；
- 路由输出稳定；
- runtime module path 与 adapter path 都可达。

## §5 Phase C — android-gradle adapter 实现与激活

### C1. 创建正式 adapter

新增 `development/skill/runtime-ops/adapters/android-gradle.md`，严格遵循 `references/contract-template.md` 十部分结构和 schema v1 frontmatter。

frontmatter 的 capability id 不在计划中硬编码最终全集；必须依据 Phase A 的真实 provider surface 决定。预期能力族包括：

- project/build discovery；
- wrapper/version inspection；
- task discovery；
- task/build execution；
- test execution/filtering；
- structured diagnostics/problem inspection；
- dependency inspection；
- runtime/repl/preview（仅真实存在时）。

### C2. 操作合同

对每个实际采用 operation 记录：

- live registered name；
- capability mapping；
- 最小调用 signature 或 provider schema 获取方式；
- wrapper/project identity；
- async/timeout 行为；
- return/result interpretation；
- failure shape；
- Windows-specific load-bearing semantics；
- 哪些输出可以形成 verification evidence。

禁止复制完整无关 output schema；只保留形成正确调用和正确判断所需的承重事实。

### C3. Task policy 与 fallback

adapter 必须包含：

- MCP-first decision；
- project wrapper precedence；
- task path 不猜测；
- bounded task discovery；
- high-impact task stop conditions；
- provider unavailable 的 degraded behavior；
- 若实现 shell fallback，则固定最小协议与 evidence downgrade。

目标不是教模型背更多 Gradle 命令，而是减少模型需要自己构造命令的空间。

### C4. Verification / mutation / recovery

根据真实 tool surface 声明 verification model。Gradle task 运行会改变 build outputs/caches，某些 task 甚至可能产生外部副作用，因此不得简单标 `mutation_support: none` 而忽略 side effect。

最终 `mutation_support` 与 Recovery model 必须由实际允许的 operation 边界决定。至少说明：

- source files 是否会被工具直接修改；
- build outputs/cache 如何视为可再生状态；
- 高影响/custom task 何时禁止自动执行；
- 如果 provider 支持会修改 build files/dependencies 的 operation，如何备份/恢复；
- 失败后哪些状态必须清理、哪些只能报告未验证。

### C5. Manifest 激活

在 adapter contract 和 tests 都准备好后才：

- `android-gradle.status: planned → active`；
- `runtime-ops.scenarios += win-android`；
- 更新 adapter description/version；
- 更新 scenario projection 文档。

禁止先改 active 再补合同。

## §6 Phase D — Kotlin managed module

### D1. 建立 kotlin-tooling

基于 Phase A adopt/adapt 清单，创建一个小型 managed module。SKILL.md 保持 kilobyte-scale；深材料进入自身 `references/`。

正文只负责：

- Kotlin-specific task classification；
- 何时需要 Kotlin tooling/module，而不是纯 Gradle runtime；
- progressive disclosure；
- 与 runtime-ops/android-gradle 的边界；
- Stop Conditions。

### D2. 避免 Gradle 重复知识

以下内容原则上只属于 android-gradle，不在 Kotlin module 重复：

- 如何调用 Gradle task；
- wrapper 命令；
- build/test result parsing；
- dependency graph operation signatures；
- Gradle MCP provider ABI。

Kotlin module 可以引用“需要执行 build/test 时加载 runtime-ops + android-gradle”，但不复制其 operation contract。

### D3. Manifest / router integration

新增 managed module 后：

- manifest `skills[]` 注册为 active scenario module；
- `scenarios: [win-android]`；
- `entrypoint: true`；
- router `composed_of[]` 纳入；
- `agents/openai.yaml` 满足 entrypoint gate；
- win-android shard 应同时可见 `runtime-ops` 与 Kotlin module，但 router 只加载任务真正需要的最小集合。

## §7 Phase E — 测试、部署验证与真实运行验证

### E1. Validator / unit regression

最低执行：

```powershell
py -3 development/tools/run_tests.py
```

重点断言：

1. 两个 source repository entry 在 checkout 缺席时仍合法；
2. checkout 存在时 origin/pinned-ref 规则按既有 validator contract 工作；
3. active `android-gradle` 必须有合法 adapter file；
4. `runtime-ops` 同时路由 `win-access-vba` 与 `win-android`；
5. `vba-office` 仍只进入 `win-access-vba`；
6. `android-gradle` 只进入 `win-android`；
7. `sql-server` / `wsl-python` planned adapter 不进入 payload；
8. Kotlin module 只进入 `win-android`；
9. v3 adapter mapping 的 negative matrix 全部被拒绝；
10. deterministic build 两次 route payload hash 一致。

### E2. Controlled payload validation

在临时 target root 执行：

```powershell
py -3 development/tools/deploy_skills.py --target-root <temp-root>
py -3 development/tools/deploy_skills.py --apply --target-root <temp-root>
py -3 development/tools/deploy_skills.py --verify --target-root <temp-root>
```

检查：

- 顶层仍只有一个 managed `global-skill-router`；
- `library/runtime-ops/adapters/vba-office.md` 和 `android-gradle.md` 都存在；
- planned adapter 不存在；
- `library/kotlin-tooling/` 存在；
- win-android shard 精确指向 runtime-ops/android-gradle 与 Kotlin module；
- win-access-vba shard 不受污染；
- verify 能识别 adapter path drift；
- rollback 仍可恢复前一 managed payload。

### E3. Source independence

完成 managed artifacts 后，使用不依赖两个 nested checkout 的验证路径证明：

- validator 不要求 `development/skill-repos/gradle-mcp` / `kotlin-agent-skills` 存在；
- deploy build 不复制它们；
- route/adapter/module 无跨根路径引用；
- provenance 只记录来源，不是 runtime dependency。

### E4. Live Gradle smoke

在明确指定的受控 Gradle/Android consumer project 上做最小 smoke，不用生产部署 task。

最低流程：

1. route 命中 `win-android`；
2. 加载 `runtime-ops` 与 `android-gradle`；
3. provider available 时，通过 structured discovery 识别 project/wrapper/tasks；
4. 运行一个低风险 targeted build/test/check；
5. 对失败场景读取 structured diagnostics；
6. 证明 agent 没有为了获取同一信息额外生成长 shell pipeline；
7. 若任务涉及 Kotlin tooling，再验证 router 能额外加载 Kotlin module，而纯 build 不加载它。

provider unavailable 时允许执行 adapter 声明的 degraded smoke，但必须在报告中明确 MCP path 未验证。

## §8 预计文件影响面

实施过程中预计修改或新增：

```text
development/skill/manifest.yaml
development/skill/global-skill-router/SKILL.md
development/skill/runtime-ops/SKILL.md
development/skill/runtime-ops/adapters/android-gradle.md
development/skill/kotlin-tooling/SKILL.md
development/skill/kotlin-tooling/agents/openai.yaml
development/skill/kotlin-tooling/references/*
development/tools/deploy_skills.py
development/tools/validate_skills.py              # 仅 route/manifest gate 真有需要时
development/tools/test_deploy_skills.py
development/tools/test_control_integration_p3.py  # 或新增更准确的 P5 test file
development/docs/scenario-routing.md
development/docs/plans/060-p5-gradle-kotlin-runtime.md
```

开发期本地但不纳入主仓：

```text
development/skill-repos/gradle-mcp/
development/skill-repos/kotlin-agent-skills/
```

如果 route v3 测试已使旧 P3/P4 测试命名失真，优先新增 `test_gradle_kotlin_runtime_p5.py` 或等价文件承载 P5-specific assertions，而不是把所有新断言继续堆进历史阶段测试。

## §9 实施顺序与切片

必须按以下顺序推进，避免 capability 先宣称后补证据：

### Slice 1 — Source intake
Clone/fetch → identity check → HEAD pin → license/readme/tool/skill inspection → manifest source entries。

Done when：两个来源均有可复现 SHA，adopt/adapt/reject 边界明确。

### Slice 2 — Route architecture repair
Route schema v3 → nested adapter mapping → router/runtime-ops selection contract → synthetic tests。

Done when：在不激活 android-gradle 的情况下，现有 vba-office 已能通过 v3 route 被确定性定位，且 P4 deploy/verify/rollback 回归通过。

### Slice 3 — Gradle runtime
根据本地 `gradle-mcp` 编写 android-gradle adapter → adapter ABI tests → manifest active + runtime-ops win-android。

Done when：controlled payload 中 win-android 可精确加载 runtime-ops/android-gradle，且 adapter 无 source-repo runtime dependency。

### Slice 4 — Kotlin module
根据官方 checkout 的 adopt 清单重建 kotlin-tooling → manifest/router integration → routing tests。

Done when：Kotlin-specific task 可命中该 module，纯 Gradle runtime task 不需加载它。

### Slice 5 — End-to-end validation
全量测试 → controlled deploy/apply/verify/rollback → source independence → live low-risk Gradle smoke。

Done when：§10 所有 acceptance criteria 满足。

每个 slice 完成后先检查 `git diff` 与全量/针对性测试，再进入下一 slice。不要把五个 slice 一次性写完后才首次测试。

## §10 Acceptance Criteria

P5 只有同时满足以下条件才能从 `executing` 改为 `done`：

- [ ] Codex 自行获取两个指定 GitHub 仓库到 `development/skill-repos/`。
- [ ] 两个 source 的 canonical origin 与实际 pinned full SHA 写入 manifest。
- [ ] source checkout 为 optional、gitignored、非 deployment dependency。
- [ ] 上游 license 已检查并记录；无不明复制来源。
- [ ] route contract 升级到 v3，scenario shard 能携带 active adapter mapping。
- [ ] route validation 能拒绝 owner/path/status/environment 不闭合的 adapter mapping。
- [ ] router/runtime-ops 不需要扫描 `adapters/` 来选择 adapter。
- [ ] `runtime-ops.scenarios` 包含 `win-android`。
- [ ] `android-gradle` adapter contract 自足且 active。
- [ ] Gradle operation/tool identity 来自真实 checkout/live catalog，不是聊天或记忆推测。
- [ ] Gradle task discovery、execution、test、diagnostic 至少覆盖实际 provider 中存在的核心能力。
- [ ] 高影响 task 有明确 stop/authorization 条件。
- [ ] verification model 不把 build/test/runtime 相互冒充。
- [ ] MCP unavailable 的 fallback 行为明确；不存在“悄悄降级却仍声称 structured verification”。
- [ ] Kotlin 官方来源经 adopt/adapt/reject 筛选，不整仓复制。
- [ ] Kotlin managed module 与 Gradle runtime adapter 无重复 ABI。
- [ ] win-access-vba/VBA route 与 adapter 行为回归通过。
- [ ] planned sql-server/wsl-python adapters 仍不可执行。
- [ ] 全量 `run_tests.py` 通过。
- [ ] controlled deploy plan/apply/verify/rollback 通过。
- [ ] 删除/隐藏两个 source checkout 后，managed payload 构建与验证仍可完成。
- [ ] live low-risk Gradle smoke 证明常规路径不再依赖临时长命令拼接。

## §11 Stop Conditions

实施过程中遇到以下任一条件必须停止受影响 slice，而不是继续猜：

1. 本地 source checkout origin 与 canonical URL 不一致。
2. upstream license 无法确认且计划直接复制其文本/代码。
3. Gradle MCP 的 live tool catalog 与 checkout 显著不兼容，无法确定真实 invocation schema。
4. route v3 需要破坏 P4 rollback/verify 兼容性且尚无迁移策略。
5. adapter 需要把 runtime 必需文件跨 root 指向 `development/skill-repos/`。
6. 为激活 android-gradle 必须把 Gradle-specific 规则写入 runtime-ops Core。
7. Kotlin module 只能通过复制整个上游 plugin/marketplace 才能工作。
8. 唯一可用的 Gradle task 属于 publish/deploy/release 等高影响类别，而任务没有明确授权。
9. source-dependent事实无法形成可机械验证的 adapter contract。
10. 现有 VBA route 回归失败且原因尚未定位。

## §12 回滚与恢复边界

P5 主仓修改全部应保持普通 Git 可回滚。两个 nested checkout 不由主仓 rollback 管理：

- 若 source clone 错误，修复其独立 checkout；不要通过主仓 `git restore` 假装恢复。
- 若 Slice 2 route schema 修复失败，在进入 adapter activation 前恢复到 v2 route contract。
- 若 android-gradle contract 未通过 gate，保持 manifest `status: planned`，不留下半激活状态。
- 若 Kotlin module 未通过 routing/quality gate，可保持 source entry 存在但不注册 active managed module。
- controlled deploy 失败时使用 P4 已有 snapshot/rollback 机制，不手工覆盖用户 skill root。
- 不因 P5 失败删除既有 `vba-office` 或更改其验证语义。

## §13 Executor Handoff

后续 Codex 执行本计划时，第一步不是编辑 managed Skill，而是读取本文件与根 `AGENTS.md`，确认当前 branch/cleanliness，然后进入 Slice 1。

执行者必须自己完成两个 GitHub repository 的 clone/fetch、identity/pin 检查和 source inspection；不得要求用户预先把仓库下载好。所有正式 Gradle/Kotlin 改造必须以这两个本地 checkout 为证据源。

实现原则按优先级排序：

1. deterministic routing before richer content；
2. source evidence before API claims；
3. MCP structured operations before ad-hoc shell；
4. smallest managed context before wholesale upstream import；
5. existing runtime-ops/router architecture before new top-level abstraction；
6. validation and rollback evidence before active/deployed claims。
