# P4 选择性发现与受管部署 — 精细实施计划

Status: draft
Date: 2026-09-05
Depends-on: 000-platform-skeleton, 040-p3-control-integration

> Status 生命周期：`draft → approved → executing → done`。被取代的计划保留状态 `superseded`，永不删除。Status 字段是本文件唯一事实源。

## §1 目标、基线与完成边界

P3 已完成逻辑控制面：manifest schema v2 分离 `sources / skills / adapters`，`research-investigation` 与 `runtime-ops` 为 active framework，`vba-office` 为 active adapter，三个后续 adapter 为 planned；profile/adapter/lifecycle/route gate 均已有机械校验。这个状态能回答“平台有哪些能力、哪些条目可 active”，但还没有解决运行时最关键的负载问题：如果把所有 active Skill 逐个复制到 Codex 顶层 skill root，Codex 仍会枚举多个 Skill 的 discovery metadata，集合增长后会增加 model-visible skill catalog 并最终触及 skills context budget。

P4 的目标是把“逻辑 Skill 集合”与“Codex 顶层可见 Skill 集合”分离。源码仍保留多个标准 Skill，便于独立开发、测试和版本控制；运行时只暴露一个薄 `global-skill-router`，其余 active framework/worker 进入 router 私有 `library/`，由 router 根据任务意图与场景按需读取。P4 同时实现 repo-owned deploy manager，使安装、更新、验证与失败恢复不依赖手工复制。

P4 完成后必须满足：新增 module 可以增长，但平台管理的 Codex 顶层 Skill 数保持 1；router 自身不吸收各 module 正文；未命中的 module 不被读取；部署可重复执行、更新同名 router payload、检测 drift，并在替换失败时恢复先前可用状态。

本阶段不迁移或删除现有 `C:\Users\tiany\.codex\skills\vba-skill`，不删除 `customer_screening/.agents/skills/recycling-company-investigation`，不实现 SQL/Android/WSL planned adapter，不把 Codex 本体修改为理解 global-skill-set manifest，也不假设 Codex 提供“Skill 调 Skill”的专有 API。Router 通过普通相对路径读取嵌套 module 的 `SKILL.md`，这是本阶段唯一依赖的调用机制。

## §2 架构决策 D1–D10

### D1 — 逻辑 registry 与物理 Codex catalog 分离

`development/skill/manifest.yaml` 描述平台逻辑能力集合；目标目录（默认用户级 `~/.codex/skills`）描述 Codex 直接 discovery 的物理 catalog。二者不再要求一一对应。P4 禁止将所有 active Skill 机械复制为 `~/.codex/skills/<name>`。

部署后的平台管理形状固定为：

```text
<target-skill-root>/
└── global-skill-router/
    ├── SKILL.md
    ├── agents/openai.yaml
    ├── _platform/
    │   ├── deployment-state.json
    │   └── routes/
    │       ├── index.yaml
    │       ├── win-access-vba.yaml
    │       ├── win-android.yaml
    │       └── wsl-python.yaml
    └── library/
        ├── research-investigation/
        │   └── ...完整 Skill root...
        └── runtime-ops/
            └── ...完整 Skill root...
```

`global-skill-router` 是本平台唯一顶层 Skill。`library/*` 不带到 target root 的同级目录，因此不进入平台管理的顶层 catalog。部署器不得修改 target root 中与本平台无关的既有 Skill。

### D2 — Manifest v3 增加 `deployment_role`

P4 将 manifest `schema_version` 从 2 升至 3；`sources / skills / adapters` 三个顶层身份面保持不变。每个 Skill 新增必填：

```yaml
deployment_role: router | module
```

语义：`router` 表示物理 Codex catalog 入口；`module` 表示只进入 router 私有 library。平台必须恰有一个 active router，名称固定为 `global-skill-router`。现有两个 framework 迁为：

```yaml
research-investigation: deployment_role: module
runtime-ops:            deployment_role: module
```

P4 新增：

```yaml
- name: global-skill-router
  path: development/skill/global-skill-router
  status: active
  scenarios: [win-access-vba, win-android, wsl-python]
  deps: []
  composed_of: [research-investigation, runtime-ops]
  entrypoint: true
  deployment_role: router
  version: "0.1.0"
  description: Thin router for selective loading of managed skill modules.
```

`entrypoint` 与 `deployment_role` 分工：`entrypoint` 表示逻辑上可被路由并要求 agent metadata；`deployment_role` 表示物理 Codex catalog 暴露。现有 framework 可保留 `entrypoint: true`，其 metadata 用于生成 router 的 route shard，但它们仍因 `deployment_role: module` 而不直接安装到顶层。

Validator 新增 gate：schema 必须为 3；每个 skill 的 deployment_role 合法；恰有一个 active router；router 必须 active + entrypoint true + scenarios 非空；所有 active module 中 `entrypoint: true` 的直接逻辑入口必须出现在 router `composed_of[]`；active `entrypoint:false` module 若未来出现，必须能从 router 直接入口的 composition closure 可达；不得把 source/adapter 当 deployment module。

### D3 — Router 是薄控制入口，不是聚合大 Skill

`development/skill/global-skill-router/SKILL.md` 只包含：Contract、最小路由步骤、加载纪律、Stop Conditions 和生成索引位置。它不得复制 `research-investigation` 或 `runtime-ops` 的领域/工具合同，不得内联 adapter/profile 内容，也不得随着 module 数增长追加每个 module 的长描述。

Router 正常流程：

1. 根据当前任务、repo/environment 线索判断候选 scenario；
2. 读取 `_platform/routes/index.yaml` 获得 scenario shard 路径；
3. 只读取必要的一个 shard；仅在场景确实不确定时读取第二个 shard；
4. 从 shard 中选择最小 module 集，默认一个；无匹配时不加载 module；
5. 读取所选 `library/<module>/SKILL.md`；
6. 后续 profile/adapter/reference 加载完全服从该 module 自己的 progressive-disclosure contract；
7. 不扫描 `library/`，不预读未命中 module。

“调取其他 Skill”在 P4 的准确含义是**读取并服从嵌套 module 的 SKILL.md**，不是要求 Codex 把 nested directory 再注册为原生 Skill。

### D4 — 路由索引分层，避免把 catalog 膨胀转移到 router

Deploy manager 根据 manifest + active logical entrypoint metadata 生成 `_platform/routes/`。`index.yaml` 只含固定 scenario vocabulary、shard 相对路径与极短 selector；不得列出所有 module。每个 `<scenario>.yaml` 只列该 scenario 的 active `deployment_role: module` 且 `entrypoint:true` 的候选项，字段限定为：

```yaml
- name: research-investigation
  description: <bounded short description>
  skill_path: library/research-investigation/SKILL.md
  status: active
```

route shard 不复制 SKILL body、profile、adapter operation 或 reference 内容。planned Skill/adapter 不进入可执行候选；如需要显示“能力尚未实现”，只能作为 bounded unavailable note，且不得生成可加载路径。

`agents/openai.yaml` 的 `short_description` 是 routing description 的优先来源；缺失时 active logical entrypoint 本身应因 validator gate 失败。生成顺序必须确定性排序，使同一 manifest 产生字节稳定索引。

### D5 — Router payload 是部署时组装产物

源码树保持：

```text
development/skill/global-skill-router/   # router source
research-investigation/                  # module source
runtime-ops/                             # module source
```

Deploy manager 在 staging tree 中复制 router source，再把 active modules 的完整 Skill root 复制到 `library/<name>/`，最后生成 `_platform/routes/*` 与 `deployment-state.json`。因此 router source 本身不需要在 Git 中持有派生 route shards；**assembled payload** 才是运行时自足单元。

P3 的 self-containment 约束在 P4 细化为：module source 自足；router assembled payload 自足。部署后不得回读仓库顶层 `references/`、`development/docs/` 或 manifest 源路径。

### D6 — Deploy manager 的 CLI 与默认安全模式

新增 `development/tools/deploy_skills.py`，Python stdlib-first，可导入同目录 validator 代码，不增加第三方依赖。最低 CLI：

```text
py -3 development/tools/deploy_skills.py [--target-root PATH] [--dry-run]
py -3 development/tools/deploy_skills.py --apply [--target-root PATH]
py -3 development/tools/deploy_skills.py --verify [--target-root PATH]
py -3 development/tools/deploy_skills.py --rollback [--target-root PATH]
```

默认 target root 为当前用户 `~/.codex/skills`；默认无 `--apply/--rollback` 时只 plan/dry-run，不改文件。`--target-root` 主要用于测试和未来项目级实验。工具必须先运行 manifest/control validation；源状态不绿则拒绝构建或部署。

`--apply` 的操作范围严格限定为 `<target-root>/global-skill-router` 和它在 `<target-root>` 同级/父级专用 backup root 中的本平台 snapshot；不得删除、重命名或覆盖 `vba-skill`、其他用户 Skill、项目 `.agents/skills`。

### D7 — 更新采用 staging + verify + recovery transaction

Apply 固定流程：

1. Validate：当前 manifest/skills 全绿；
2. Build：在 repo-local `.tmp/deploy/<run-id>/` 构建完整 router staging payload；
3. Hash：生成 deployment-state，记录 manifest schema/version/hash、module 列表、route hash、payload 文件 SHA-256；
4. Preflight：target root 可写；目标不存在 symlink/reparse escape；目标同名只允许是本工具管理的 router payload或首次安装空缺；
5. Compare：与已安装 state/hash 相同则 no-op；
6. Snapshot：已有 managed target 时保存一个 previous snapshot 到 target root 之外的专用 backup root；
7. Replace：将 staging payload 发布为 `<target-root>/global-skill-router`；Windows 下不假定 POSIX 目录覆盖原子性，允许用 rename/swap 序列，但每一步必须可恢复；
8. Verify：对安装后 state、hash、布局、routes、library closure 再验证；
9. Failure recovery：任一步失败则恢复 previous target；若恢复也失败，保留 snapshot 并明确返回非零与人工恢复路径。

成功后保留至多一个 previous snapshot供 `--rollback`；不无限积累历史备份。`--rollback` 只能恢复本工具生成且 state 完整的 previous snapshot。

### D8 — Deployment state 与 drift detection

`_platform/deployment-state.json` 至少含：

- `deployment_schema_version`；
- source manifest SHA-256 与 manifest schema version；
- router/module names + versions；
- route index/shard SHA-256；
- payload 文件相对路径 → SHA-256；
- 不包含绝对 repo path、用户名或机器秘密。

`--verify` 必须检测：缺文件、额外受管文件、hash 不一致、route 指向不存在 module、module 不在 `library/`、router 顶层文件缺失。检测到 drift 只报告，不自动覆盖；修复需显式 `--apply`。这样人工手改安装目录不会被静默吞掉。

### D9 — 旧 Skill 在 Alpha 期并存，不纳入 P4 管理

P4 安装后允许：

```text
~/.codex/skills/
├── global-skill-router/   # 本平台 managed
└── vba-skill/             # legacy，保持原样
```

`customer_screening/.agents/skills/recycling-company-investigation` 也保持原样。P4 不做 capability parity、rename、退役或自动迁移。其目的只是验证新 routed platform 的核心命题。旧 Skill 迁移必须另立计划，且只有在新 route/module 行为经过真实任务验证后才可执行。

### D10 — P4 不修改 Codex 本体

Codex 源码已经存在 model-visible skills list 与 skills context budget；P4 利用现有 discovery 行为降低本平台占用，不 patch Codex、不要求 fork 增加 manifest-aware router，也不依赖未稳定公开的内部接口。验证“顶层只有 router”以部署布局 + live Codex discovery/任务行为为证据。

若后续发现 Codex 原生提供稳定的 lazy skill catalog/host skill root API，可另立优化计划；P4 不预绑定该实现。

## §3 Router source contract

新增：

```text
development/skill/global-skill-router/
├── SKILL.md
├── agents/openai.yaml
└── references/
    └── routing-contract.md   # 仅在 SKILL.md 需要下沉细则时创建
```

`SKILL.md` frontmatter：`name: global-skill-router`，description 含明确 `Use when ...`。正文必须短，核心约束包括：只通过 `_platform/routes/index.yaml` 进入路由；禁止 glob/目录扫描 library；无匹配不加载；默认选最少 module；读 module 后其 contract 优先处理领域/工具动作；planned/unavailable 不得伪装 active；route shard 缺失/格式错误时停止并报告 deployment corruption，而不是猜测模块路径。

`agents/openai.yaml` 的 default_prompt 只提示加载 `$global-skill-router` 并按需选择 managed module，不列出所有 module 名称。

Router 不承担 module 的版本升级逻辑、部署逻辑或状态修复；这些属于 deploy manager。

## §4 Manifest v3 与 validator 扩展

`validate_skills.py` 升级至 schema v3，同时保留 P1/P2/P3 所有 contract gate。新增稳定错误类别至少包括：

| Gate | 失败示例 | 建议错误码 |
|---|---|---|
| deployment role | 缺失/非法 role | `DEPLOYMENT_ROLE_INVALID` |
| router cardinality | 0 或 >1 active router | `ROUTER_CARDINALITY_INVALID` |
| router identity | active router 名不是 global-skill-router | `ROUTER_ID_INVALID` |
| router activation | router 非 active/非 entrypoint/scenario 空 | `ROUTER_ACTIVATION_INVALID` |
| module coverage | active entrypoint module 不在 router composed_of | `ROUTER_MODULE_UNCOVERED` |
| nested reachability | active internal module 无 composition path | `MODULE_UNREACHABLE` |
| physical path safety | Skill/adapter canonical path 逃逸 owner/root | 使用 P3 hardening 已有或新增 path 错误码 |

P4 实施时顺手闭合已经识别但尚未阻塞 P3 的 path containment：Skill 必须 canonicalize 在 `development/skill/<name>`；adapter 必须 canonicalize 在 owner Skill 的 `adapters/` 下。该校验直接影响 deploy manager 的安全边界，因此属于 P4 必要前置，而不是无关 hardening。

Router 作为普通 Skill 仍通过 frontmatter、agents metadata、deps/composed_of cycle 等现有 gate。`global-skill-router.composed_of` 只登记逻辑 module，不把 adapters 放入组合边。

## §5 Route index builder contract

Route builder 可放在 `deploy_skills.py` 内部纯函数，不另建脚本，除非代码复杂度证明需要拆分。输入只来自已验证的 manifest 与对应 `agents/openai.yaml`；输出 YAML 使用 PyYAML 会给 deploy script 增加依赖，因此优先考虑 JSON 生成，或复用仓库已声明 PyYAML。若使用 YAML，PyYAML 已由 `validate_skills.py` 声明为 repo dependency，不算新增第三方包。

索引必须满足：

- `index` 大小只随 scenario 数增长，不随 module 数增长；
- module 数增长只影响对应 shard；
- shard 每项只含 routing 必需 metadata；
- deterministic ordering；
- route paths 为 router-relative POSIX style；
- planned entries 不进入 active candidate；
- route 生成后进行自验证，任何 path 不存在/越界则拒绝 deploy。

为了避免“router 为选 skill 又读取所有 skill”的反模式，SKILL.md 不允许回退成扫描 `library/*/SKILL.md`。

## §6 Deploy manager 测试计划

新增 `development/tools/test_deploy_skills.py`，继续通过 `run_tests.py` 运行。最低覆盖：

1. **First install**：临时 target root 从空状态安装成功，仅新增 `global-skill-router/`；两个 framework 只存在于 `router/library/`。
2. **No-op update**：同一源重复 apply 不改 state/hash，返回可识别 no-op。
3. **Content update**：修改 fixture module 内容后重新 apply，nested module 更新，router 顶层数量仍 1。
4. **Failure recovery**：在 replace/verify 中注入失败，旧 managed target 恢复；其他 target-root Skill 字节不变。
5. **Rollback**：成功更新后 previous snapshot 可恢复，恢复后 verify 绿。
6. **Drift**：人工改 installed nested file 后 `--verify` 非零并报告 hash mismatch，不自动覆盖。
7. **Path escape**：manifest/module/route 含绝对、`..`、owner escape 时拒绝部署。
8. **Legacy coexistence**：target root 预置 `vba-skill` fixture，apply/update/rollback 后逐字节不变。
9. **Planned exclusion**：planned skill/adapter 不进入 library 可执行候选。
10. **Determinism**：同一逻辑输入两次 build 的 routes 与 state（排除运行时临时字段）字节稳定。

## §7 负载控制与增长回归

P4 的核心不是“两个 Skill 能被复制”，而是“Skill 集合增长不扩大顶层 catalog”。因此必须新增一组 synthetic growth test：

- 基线：router + 2 active modules；
- 扩展：router + 至少 50 个 synthetic active entrypoint modules，分布到三个 scenario；
- 两次构建后 `<target-root>` 中本平台管理的顶层 Skill 数都为 1；
- router `SKILL.md` 和 `agents/openai.yaml` 字节完全不因 module 数变化；
- `_platform/routes/index.*` 字节不随 module 数线性增长，只允许固定 scenario metadata；
- 只有对应 scenario shard 增长；
- `library/` 增长不改变顶层 catalog；
- planned synthetic modules 不进入 active shards。

这是对 context-budget 目标的结构性代理证明。P4 不声称仅凭文件布局即可测出精确 token 数；真实模型可见行为由 §8 live Alpha 补证。

## §8 Live Alpha 验收矩阵

自动测试全绿后，使用真实 Codex 新 thread 做非破坏性 Alpha。至少完成：

| Case | 输入 | 预期 |
|---|---|---|
| A | 普通 evidence-first 公司/项目调查任务 | Codex 先用 router，随后只加载 `research-investigation`；按需要再加载 profile/reference |
| B | Access/VBA diagnose/review 任务 | router 选择 `runtime-ops`；runtime-ops 再选择 `vba-office`；不加载 research module |
| C | 与平台两框架均无关的普通编码任务 | router 不强行加载 module，或 Codex根本无需使用 router；不得为“总要选一个”而误路由 |
| D | 明确要求 `$global-skill-router` 但任务无匹配 | router 返回 no-match/continue-without-module，不扫描 library |
| E | 安装前后 skills discovery 对比 | 本平台新增的顶层可见 Skill 只有 `global-skill-router`，不是两个 framework + router |
| F | synthetic 扩展包（测试 target 或可控环境） | module 数增长不产生新的平台顶层 Skill |

观察项：是否错误读取未命中 module；router 是否因描述不足频繁误路由；是否需要同时加载两个 module；route shard 大小与阅读次数；旧 `vba-skill` 是否仍可显式使用。Alpha 结果只记录稳定决策所需结论，不把一次性 prompt transcript 塞入长期文档。

## §9 实施顺序

1. Baseline：确认 P3 commit clean，validator + 全测试绿；记录现有用户级 `vba-skill` 和项目级 recycling skill 只作“不触碰”边界，不读取无关内容。
2. Manifest v3：加入 deployment_role、router entry，并扩 validator cardinality/coverage/reachability/path containment gate。
3. Router source：新增薄 `global-skill-router/SKILL.md` + metadata；不得先写 module catalog 到正文。
4. Pure payload builder：在 tmp_path 构造 router + library + route shards + deployment state，不触碰真实 `~/.codex`。
5. Deploy plan/verify：实现 dry-run、hash/state、drift 校验。
6. Apply transaction：实现 staging → snapshot → replace → verify → failure recovery；随后实现 rollback。
7. Tests：first install/update/no-op/recovery/rollback/drift/path/legacy/determinism/growth 全部绿。
8. Docs sync：更新 repo-conventions 的 Deployment and Runtime Mapping，使其从 P3“只规定映射”升级为 P4 实际 deploy contract；README 仅更新稳定状态；AGENTS Commands 加 deploy 的 plan/verify 入口，仅当会改变 agent 操作时添加。
9. Disposable install：先对临时 target root 完整 apply/verify/rollback。
10. Real Alpha install：对用户级 Codex skill root 先 dry-run，审查只触碰 `global-skill-router` 后显式 apply；不改 legacy Skill。
11. Live Alpha：执行 §8；若发现 router 必须扫描全部 library 才能工作，则 P4 不得 done，回到 route-index 设计修复。

## §10 验收标准

P4 只有同时满足以下条件才可改为 `done`：

1. manifest 为 schema v3，恰有一个 active `deployment_role: router`，其余 active framework/worker 为 module；P1/P2/P3 gate 保持绿。
2. `global-skill-router` 为薄入口，其正文不复制 module contract，不列出完整 module catalog，不扫描 library。
3. route index 分层生成：固定 scenario index + scenario shards；planned 条目不成为可执行候选。
4. deploy manager 默认 dry-run；apply 只管理 `global-skill-router` 目标及专用 snapshot，不修改其他 Skill。
5. 安装 payload 自足：router 可相对路径读取 route/module；module 可继续加载自身 profiles/adapters/references；不依赖源码 repo 顶层 references。
6. apply 支持首次安装、no-op、更新；失败能恢复旧 target；verify 能检测 drift；rollback 能恢复 previous snapshot。
7. synthetic 50+ module growth regression 证明平台管理的顶层 Skill 数始终为 1，router SKILL/metadata 不随 module 数膨胀。
8. 全仓测试通过；deploy targeted tests 通过；validator/manifest 通过。
9. 真实用户级 dry-run 明确显示不会覆盖 `vba-skill`；apply 后旧 Skill 保持可用。
10. Live Alpha 至少完成 research、VBA runtime、no-match、discovery 对比四类核心 case，未观察到 router 常态预读全部 modules。

失败条件：若 framework 仍需作为顶层 Skill 才能被 router使用；若 router 为路由必须扫描全部 library；若新增 module 会新增 Codex 顶层 Skill；若 deploy update 会无备份覆盖现有 target；若 drift 被静默覆盖；若 P4 自动删除旧 Skill；任一成立，P4 不得标 done。

## §11 明确排除与后续计划

P4 不做旧 `vba-skill` → runtime-ops 的能力迁移，也不把 recycling project Skill 改成 profile-only；这些需要基于 Alpha 真实任务结果另立 migration plan。P4 不实现 SQL/Android/WSL adapters，不建立远程 skill marketplace，不做自动后台更新，不修改 Codex skills context budget，不把 router 做成常驻 MCP 服务。

P4 完成后，下一阶段才有足够证据决定两件事：一是旧 Skill 的 capability/knowledge 如何拆入 platform modules 并退役；二是是否需要多 router、项目级 router overlay 或原生 Codex extra-roots 集成。不得在 P4 为这些未来形态预造复杂机制。
