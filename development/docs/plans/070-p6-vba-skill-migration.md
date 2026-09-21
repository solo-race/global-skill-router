# P6 VBA Skill 统一迁移与全局上下文退役 — 精细实施计划

Status: executing
Date: 2026-09-20
Depends-on: 030-p2-runtime-ops, 040-p3-control-integration, 050-p4-selective-discovery-deployment

> 编号说明：本分支故意跳过 `060`。该编号保留给并行的 Kotlin/Gradle runtime 工作；本计划固定使用 `070`，后续合并不得改回 `060`。
>
> Status 生命周期：`draft → approved → executing → done`。被取代的计划保留状态 `superseded`，永不删除。Status 字段是本文件唯一事实源。

## §1 目标、现状与完成边界

P2 已从 Access/Excel VBA Skill 中抽出通用 runtime control plane，并建立 `runtime-ops + vba-office`；P3/P4 已把该能力接入 manifest、router 与单入口部署拓扑。当前 `win-access-vba` 已能路由到 `runtime-ops + vba-office`，因此 VBA 不再需要作为所有 Codex session 都预加载的全局规则。

迁移仍未完成，但运行时基线已经发生一项外部变化：用户已于 2026-09-20 手工从用户级 Codex `AGENTS.md` 删除 VBA 专属段。P6 不再负责执行或回滚这次编辑；该已删除段中的规则转为迁移 parity 清单，必须由 managed VBA bundle 自主承接，不能依赖 global AGENTS 兜底。

当前仍有两套 active VBA runtime source 需要收敛：

1. 用户级顶层 `vba-skill` 仍作为独立 Skill 被 Codex discovery，包含 Access/Excel 宿主知识、四套 workflow、两份 MCP tool contract、两个 lint profile 和 SaveAsText helper；
2. 平台内 `development/skill/runtime-ops/adapters/vba-office.md` 已重复承载两个 MCP 的 ABI、mutation/recovery、验证和 task routing，但尚未完整承接旧 Skill 的宿主知识、operator boundary，以及原 global AGENTS 中已经移除的若干 hard guard。

因此非 Office session 的 VBA 全局上下文负担已经提前消失；P6 剩余目标是消除 legacy Skill 与 managed adapter 的双 runtime source，并证明在没有 global AGENTS VBA 兜底的条件下，managed bundle 仍保持原有安全和证据边界。

P6 的目标是把 VBA 的运行时规则、两个 MCP 的调用合同、宿主知识与工作流统一收敛到 **router-managed `runtime-ops/vba-office` bundle**，并在 capability/knowledge parity 与受控 cutover 验证完成后：

- 将旧顶层 `vba-skill` 移出 Codex 顶层 Skill discovery；
- 保持 `vba-doctor` 与 `vba-lint` 为外部 provider，不复制其实现；
- 保持非 Office session 不加载 VBA adapter 或 VBA knowledge；
- 在 global AGENTS 已无 VBA 规则的基线下，保持 Access/Excel 的宿主语义、写入安全、operator handoff、静态/运行时证据边界无回退；
- 不使用已经收束并投入使用的 Access 项目作为迁移 fixture 或验证靶标。

P6 完成后的唯一运行时入口必须是：

```text
global-skill-router
  → scenario: win-access-vba
    → runtime-ops
      → adapter: vba-office
        → 仅按任务需要加载 workflow / Access|Excel|shared reference
        → 调用外部 vba-doctor / vba-lint
```

本阶段不是重写 VBA Skill，也不是把所有旧文件机械复制进平台。迁移的验收单位是“会改变 agent 决策的能力、知识、限制和验证证据”，不是旧目录字节级一致。

## §2 事实源与冲突处理

迁移期间按以下优先级处理冲突，任何差异必须显式解决，不得用“旧 Skill 已经这么写”覆盖真实 provider 行为。

### S1 — MCP 实现是工具 ABI 的最高事实源

- `vba-doctor` 注册工具、参数、返回状态、ownership、timeout/dialog、compile dispatch 等语义，以当前外部 server 实现和其测试为准；
- `vba-lint` 工具签名、hostLibraries 匹配、catalog、severity/category 行为，以当前外部 server 实现和 live catalog 为准；
- skill/adapter 只镜像 agent 决策所需合同，不复制 server 实现。

迁移开始时先做一次 bounded contract sync。已知至少有两处需要重新校正：

1. 当前 managed `vba-office.md` 仍把 Excel `compile_vba_project` 写成可返回 `status: ok` 并建立 Compile evidence；当前 provider 实现实际在 target-checked command dispatch 后返回 `status: unverified`，不能建立 Compile Verified；
2. legacy tool contract 已包含 Excel `open_workbook(..., safe_inspection=False)` 的安全检查模式，而 managed adapter 当前签名仍未表达该参数与行为。

这些已知漂移必须在 legacy 退役前修复；同时检查其余工具，不假设只有这两处。

### S2 — Legacy Skill 与已删除的 global AGENTS 规则是迁移输入，不是永久 runtime dependency

当前用户级 `vba-skill` 是主要 capability/knowledge parity 输入；原 global AGENTS 的 VBA 规则已经从运行环境删除，其必须保留的决策约束以本计划 §6 的自足 parity 表为准。P6 不要求重新把旧段写回 AGENTS 才能比较。

迁移完成后：

- deployed managed bundle 不依赖 legacy Skill 路径；
- router/module 不回读用户级 `AGENTS.md` 获取 VBA 语义；
- legacy Skill 可作为退役快照暂存于 discovery root 外，但不再是 active runtime source；
- current global AGENTS 保持无 VBA-specific tooling rules，P6 不再修改它。

### S3 — `references/access-vba-dev` 保留为 development provenance

`references/access-vba-dev` 继续是只读设计来源和测试迁移来源，可保留在 repository 中；它不得成为部署后执行 VBA 任务所必需的路径。P6 不要求删除该 reference repository。

## §3 架构决策 D1–D10

### D1 — VBA 只有一个 managed runtime owner

VBA runtime contract 的 owner 固定为 `runtime-ops` 下的 `vba-office` adapter。不得新增第二个顶层 `vba` Skill，也不得新增专门的“vba-doctor Skill”或“vba-lint Skill”。

两个 MCP 是 provider；`vba-office` 是把 provider capability、宿主语义、mutation/recovery 与 evidence discipline 组合成可执行 Office contract 的 adapter。

### D2 — Adapter 保持执行合同自足，宿主知识按需外置

`adapters/vba-office.md` 必须自足到足以：

- 识别 provider、host/file identity 与 capability；
- 正确形成每个工具调用；
- 判断 precondition / permission / ownership failure；
- 决定哪些 mutation 允许发生及如何恢复；
- 区分 static / compile-dispatch / runtime / operator-observed evidence；
- 进入 operator-only boundary；
- 根据任务模式选择需要继续加载的 workflow/reference。

但 Access/Excel 的细粒度对象模型知识不再堆在 adapter 正文。Form lifecycle、focus/control、record navigation、DAO、Workbook/Worksheet ownership、events、UserForm、Ribbon、xlam 等进入 `references/vba-office/` 并只按问题加载。

因此 P6 后 adapter 的“self-sufficient”含义是**执行和证据合同自足**，不是“所有 Office 知识都在单文件内”。

### D3 — Workflow 只承载模式序列，不复制 Core/ABI

保留 Diagnose / Review / Modify / Test 四个 workflow，因为它们会改变 Office 任务的实际检查顺序；迁入后必须删去重复的通用 Core、安全说明和完整 tool signature。

Workflow 只应表达：

- 该模式何时使用；
- 需要加载哪些宿主 reference；
- 相对 Core lifecycle 的模式特化步骤；
- mode-specific stop/resume condition；
- mode-specific output/evidence。

Capability、ownership、backup/recovery、operator boundary 的权威定义仍在 adapter/Core，不在四个 workflow 各复制一遍。

### D4 — 不保留第二套 MCP tool-contract 文档

legacy `tool-contracts/vba-doctor.md` 与 `tool-contracts/vba-lint.md` 中会改变调用或判断的内容必须同步进 `vba-office.md`；同步完成后，managed runtime tree 不再建立第二套 `tool-contracts/`。

原因：provider API 已由 adapter mirror；再保留完整 tool-contract 只会恢复 P6 要消除的三源漂移。

### D5 — 两个 lint profile 默认吸收入 adapter

legacy 的两个 profile 当前主要编码：

- Access: `hostLibraries: ["access"]`, `severity: "warning"`;
- Excel: `hostLibraries: ["Excel"]`, `severity: "warning"`。

这些值体量小、只服务一个 adapter，且 provider 不自动读取 profile。P6 默认将其作为 adapter 的 host invocation policy 内联，不复制 `profiles/vba-lint-*.yaml`。

只有实施时发现 profile 被其它独立工具机械消费，才允许保留配置文件；不得仅因为 legacy 已有文件就继续保留。

### D6 — SaveAsText helper 保留为唯一的确定性辅助脚本

`extract_access_saveastext.py` 解决的不是 MCP ABI，而是 Access `Application.SaveAsText` 混合对象 dump 与纯 VBA source 的确定性边界。该场景仍可能在 code review 中出现，且 provider 不等价提供此转换。

因此迁移：

- `scripts/extract_access_saveastext.py`；
- `references/access/saveastext-source.md`；
- 对应 `ready / no_vba / unresolved` regression tests。

不得把原始 SaveAsText `.txt` 直接送入 `vba_parse` / `vba_inspect_workspace`。

### D7 — 用户级 AGENTS 的 VBA 清理已完成，P6 只验证独立性

用户级 `AGENTS.md` 当前已经不再包含 `vba_lint`、`vba_doctor`、Access Eval、Office production target 等领域专属内容。P6 接受这一状态为 baseline，不恢复、不重写该段；是否读取 VBA contract 完全由 router 的 `win-access-vba` 场景决定。

P6 必须证明 managed bundle 在该 baseline 下仍自足承载原 hard guard。P6 不把其它全局 working rules 搬进 Skill，也不让 Skill 覆盖通用 repository、安全或 subagent 规则。

### D8 — Legacy retirement 不扩张 deploy manager 的永久 ownership

P4 的 deploy manager 只管理 `global-skill-router` 及其专用 snapshot。P6 不为了删除一次 legacy Skill 就让 deploy manager 开始管理整个 `~/.codex/skills` 或用户级 `AGENTS.md`。

Legacy retirement 是一次明确的 cutover operation：

- 在 managed payload 已验证后执行；
- 对 exact legacy Skill target 做可逆移动；
- 验证后再继续；
- 失败时恢复原 discovery 位置。

global AGENTS 的 VBA 删除已经由用户在 P6 外完成，不纳入 deploy manager 或 P6 rollback ownership。这不是长期 migration framework，也不新增通用 legacy compatibility layer。

### D9 — 退役采用可逆移出 discovery，而不是先删除

首次 cutover 不直接永久删除 `vba-skill`。将 exact legacy Skill directory 移到 Codex skill discovery root 外的 operator-reviewed backup location，再验证 router-only 行为。

验证失败时移回原位置即可恢复。P6 done 不要求清除该退役快照；是否后续删除由单独维护动作决定。

### D10 — 迁移不得增加非 Office 上下文成本

Router 仍只依据已有 task/repository/environment evidence 选择一个 scenario shard。VBA workflow/reference 不进入 route index，不成为顶层 Skill metadata，也不在选择 `runtime-ops` 前预读。

新增 10+ VBA reference 文件后，no-match、Android、WSL、普通 repository task 的 model-visible VBA 内容必须仍为零。

## §4 目标目录结构

P6 目标 runtime tree：

```text
development/skill/runtime-ops/
├── SKILL.md
├── adapters/
│   └── vba-office.md                 # 唯一 VBA execution/tool/safety/evidence contract
├── workflows/
│   └── vba-office/
│       ├── diagnose.md
│       ├── modify.md
│       ├── review.md
│       └── test.md
├── references/
│   ├── verification-ladder.md        # 现有 Core contract
│   ├── contract-template.md           # 现有 Core contract
│   ├── evidence-types.md              # 现有 Core contract
│   └── vba-office/
│       ├── shared/
│       │   ├── sources.md
│       │   ├── error-handling.md
│       │   └── vba-encoding.md
│       ├── access/
│       │   ├── saveastext-source.md
│       │   ├── form-lifecycle.md
│       │   ├── controls.md
│       │   ├── record-navigation.md
│       │   ├── form-state.md
│       │   └── dao.md
│       └── excel/
│           ├── workbook-worksheet-model.md
│           ├── worksheet-events.md
│           ├── userform-model.md
│           ├── ribbon-xml.md
│           └── addin-xlam.md
└── scripts/
    └── vba-office/
        ├── extract_access_saveastext.py
        └── test_extract_access_saveastext.py
```

不新增 managed `tool-contracts/` 或 `profiles/`，除非实施证据推翻 D4/D5；若发生，必须在本计划中记录原因后再改结构，不能静默复制 legacy。

`vba-office.md` 增加最小 load index，例如：

- diagnose → mode workflow + selected host references；
- review → review workflow + source/evidence reference + selected host references；
- modify → modify workflow + affected host references；
- test → test workflow；仅在测试问题涉及具体 host semantics 时再加载 reference；
- SaveAsText review → Access SaveAsText reference + helper；
- 不命中细知识问题时不得扫描整个 `references/vba-office`。

## §5 Legacy 资产去向

| Legacy 资产 | Managed 去向 | 处理方式 |
|---|---|---|
| `SKILL.md` | `vba-office.md` + workflow/reference | 拆分，不原样复制；execution/safety 进 adapter，模式流程进 workflow，宿主知识进 reference |
| `tool-contracts/vba-doctor.md` | `vba-office.md` | 与 live provider 同步后吸收；managed runtime 不保留第二份完整 contract |
| `tool-contracts/vba-lint.md` | `vba-office.md` | 同上；live catalog 仍优先 |
| `profiles/vba-lint-access.yaml` | `vba-office.md` host invocation policy | 默认吸收并退役 profile |
| `profiles/vba-lint-excel.yaml` | `vba-office.md` host invocation policy | 默认吸收并退役 profile |
| `workflows/diagnose.md` | `workflows/vba-office/diagnose.md` | 迁移并去重 Core/ABI 文本 |
| `workflows/modify.md` | `workflows/vba-office/modify.md` | 迁移并去重，保留完整-module、minimum patch、rollback sequence |
| `workflows/review.md` | `workflows/vba-office/review.md` | 迁移并去重，保留 SaveAsText gate 与 host interpretation |
| `workflows/test.md` | `workflows/vba-office/test.md` | 迁移并修正 verification model |
| `references/shared/*` | `references/vba-office/shared/*` | 按需迁移，保留 evidence/source/encoding/error-handling 决策知识 |
| `references/access/*` | `references/vba-office/access/*` | 按需迁移，禁止项目业务名进入 generic bundle |
| `references/excel/*` | `references/vba-office/excel/*` | 按需迁移 |
| `scripts/extract_access_saveastext.py` | `scripts/vba-office/` | 迁移；带现有 regression test |
| legacy 顶层 Skill directory | discovery root 外退役位置 | parity + controlled fixture cutover 后移动，不先删除 |
| 原用户级 `AGENTS.md :: VBA tooling` | adapter/workflow | 已由用户手工删除；以 §6 parity 表逐条确认 managed owner，不再执行 AGENTS edit |

实施前应以实际 legacy tree 再做一次 bounded inventory；如果发现本表未列出的文件，只判断其是否改变 agent 决策或提供 runtime capability，不因“文件存在”而自动迁移。

## §6 已删除 global AGENTS 规则的 parity 合同

用户级 `AGENTS.md` 的 VBA 段已由用户手工删除。以下映射现在是 **managed bundle 必须独立满足的 parity 清单**，不是未来的 AGENTS 编辑步骤。实施时不得为了通过测试把这些规则重新写回 global AGENTS：

| 原全局规则 | 新 owner |
|---|---|
| “仅 Windows native Office 任务继续读取 VBA 规则” | router scenario + adapter load trigger |
| `vba_lint` 可自动 parse/inspect/workspace/list | `vba-office.md` capabilities/operations |
| lint 为 advisory，clean lint 不证明 compile/runtime | adapter evidence contract |
| `vba_doctor` 可自动做 read-only open/list/read | adapter capability + operation policy |
| write 仅在用户请求 VBA 修改且 target 为 dev/test 时允许 | adapter mutation precondition / stop condition |
| 修改 existing module 前必须读当前完整 source | adapter recovery contract + modify workflow |
| 修改后 reread + lint + narrow runtime verification | adapter verification contract + modify/test workflow |
| 未明确授权不得修改 production/authoritative database | adapter mutation hard stop |
| 不得无必要删除/替换 existing business module | modify workflow host guard |
| 不得把普通 `Public Sub` / parameterized macro 当 Access baseline smoke | adapter Access execution semantics |
| 多个 `Access.Application` 时不得猜 macro binding | adapter host/session identity + ownership |
| Access runtime candidate path = no-arg `Public Function` via `Eval`; deployment evidence remains unverified until direct/provider execution succeeds | adapter execution semantics |

当前 global AGENTS 无 VBA 摘要的状态应保持不变。若某条确实适用于所有语言/宿主，应另行作为真正的通用规则评估；P6 不借 VBA migration 修改全局 working rules。实施验证只需确认 current AGENTS 未重新出现 VBA-specific tooling section，不需要读取或保存其历史文本。

## §7 Verification model 修正

当前 managed adapter 声明 `verification_model_kind: linear`，并使用 `Static → Compile → Runtime`。这与现 provider 的证据通道已经不完全一致：

- Access 没有 registered compile operation；
- Excel `compile_vba_project` 只能 target-check + dispatch compile command，返回 `unverified`；
- Access/Excel 又都可以获得 targeted runtime execution evidence。

因此 P6 不得继续把 compile dispatch 当作线性 ladder 中可自动达到的 Compile Verified。

目标模型改为 **independent checks**：

1. **Static**：changed source reread + host-correct `vba_parse` / `vba_inspect`；
2. **Compile**：当前 registered provider 对 Access 为 unsupported，对 Excel 为 dispatch-only/unverified；只有未来存在独立可靠 result channel 时才可标 achieved；
3. **Runtime**：targeted entry point 实际执行并观察到预期结果/state；dialog 必须走 owned structured path；
4. **Operator-observed**：单独证据通道，不是 Static/Compile/Runtime 的替代物。

后果：

- adapter frontmatter 与 verification section 必须同步；
- workflow 不再使用“highest achieved level”来暗示 Runtime 自动证明 Compile；
- Excel compile command 结果单独记录为 `compile dispatch: unverified`；
- Access runtime smoke 仍不得改写成 compile evidence；
- Core 无需改变，因为 `runtime-ops` 已支持 `independent_checks` / 非线性报告语义。

### M5-01 final Access runtime evidence state

The U32 stop-loss probe closes the Access runtime investigation for this P6
session. Two operator-prepared fixed files were opened as trusted databases
with `AutomationSecurity=2`; their paths, HWNDs, and PIDs were distinct. On
the same managed A instance, direct `Eval("P6ManagedHwnd()")` and the provider
`run_macro(A, "P6ManagedHwnd")` path each failed once with the same Access
function-name-not-found error. No copy/run-directory, VBE access, dynamic
module mutation, or provider implementation change was involved.

This is not Runtime Verified and is not evidence of a Microsoft bug. The
accurate deployment state is:

```text
Access runtime execution evidence: UNVERIFIED / accepted known limitation
```

The direct/provider agreement supports treating the result as a current Access
runtime/environment limitation rather than a migration-parity, instance-
binding, marshal, Trusted Location, ACL, copy-method, or wrapper defect. The
fixed files' sizes remained unchanged, but their mtimes changed during the
run; report only that no planned VBA/module mutation occurred, not byte-level
immutability. Do not reopen this investigation inside P6 unless a future task
explicitly requests provider/runtime certification.

如果实施时发现 Core validator 对 `independent_checks` 已有 contract 但测试缺口，则补 targeted validator regression；不得为了保留旧 VBA linear 文案去削弱 Core。

## §8 实施阶段 M1–M7

### M1 — Freeze migration inventory 与 provider contract

只读完成：

1. 记录当前 branch/HEAD 与 clean state；
2. bounded tree/read 当前用户级 `vba-skill`；
3. 确认 current 用户级 `AGENTS.md` 已无 VBA-specific tooling section；原规则以 §6 的自足表作为 parity 输入，不要求恢复历史段；
4. 对 `vba-doctor` / `vba-lint` 当前注册工具和实现做 targeted contract sync；
5. 建立 legacy → destination parity table，并标出 `absorb / lazy-reference / helper / duplicate-drop / retire`；
6. 先修正任何会造成错误调用或错误 verification claim 的 provider drift，再继续内容搬迁。

M1 不修改外部 MCP server。

### M2 — 建立 managed VBA bundle

新增 §4 目标目录中的 workflow/reference/script。迁移时：

- 保留原 reference 的证据类型与 Microsoft source priority；
- 只消除重复，不主动“现代化重写”宿主语义；
- 改写内部相对路径到新的 `runtime-ops` root；
- project-specific form/query/workbook/business logic 禁止进入 bundle；
- SaveAsText helper 同步迁移现有 Python regression tests。

此时 legacy Skill 仍保持原状；global AGENTS 继续保持已经移除 VBA 段后的当前状态。

### M3 — 收敛 `vba-office.md`

更新 adapter：

1. 与当前 provider 同步 tool signatures / defaults / failure semantics；
2. 吸收两个 lint profile 的 invocation policy；
3. 按 §6 parity 表吸收原 global AGENTS 曾承载但 managed adapter 仍缺失的 production target、existing-module、Access instance ownership、operator boundary 等规则；
4. 切换 verification model 为 §7；
5. 增加 workflow/reference lazy-load index；
6. 删除已被外置 host reference 承载的长领域知识，避免 adapter 再膨胀成旧 `SKILL.md`；
7. provenance 仍可指向 `references/access-vba-dev`，但部署运行不得依赖它。

### M4 — Validator、部署与回归测试

只补能捕获真实迁移失败的检查：

- runtime-ops payload assembly 必须包含新增 workflow/reference/script；
- adapter 引用的相对路径必须存在且留在 skill root；
- no-match/其它 scenario 不加载 VBA companion files；
- planned adapters 仍不得受 VBA bundle 影响；
- SaveAsText helper 的现有 regression 全部通过；
- verification regression 明确拒绝把 Excel `status: unverified` 升级为 Compile Verified；
- Access baseline candidate contract 保持 no-arg `Public Function` / Eval；deployment evidence remains `unverified` unless direct/provider execution succeeds；
- deployment tests 仍证明 deploy manager 不自动删除 legacy Skill。

不要增加“扫描每个 reference 内容是否完全相等”的脆弱 snapshot test。

### M5 — Synthetic/dev-fixture parity Alpha (M5 closed; Access runtime limitation accepted)

当前没有近期 VBA 开发需求，既有 Access 项目已经收束并投入使用。P6 **禁止**把该项目或任何 production/authoritative Office 文件作为迁移验证对象；不得为了完成 Skill migration 重新打开业务开发面。

使用 legacy Skill 作为知识对照、managed router 作为候选运行时，并仅在 controlled synthetic/dev fixtures 上执行需要真实 Office host 的验证。M5 的静态、合同、安全、exact-instance、marshal/fail-close、Excel artifact/runtime 与其它 parity/live evidence 已按本会话记录完成；M5-01 的 Access runtime 结果按 §7 关闭为 accepted limitation，不再作为迁移 STOP。至少覆盖：

1. Access source read + lint/review；
2. Access runtime diagnose：以 no-arg Public Function / Eval 作为候选路径；当前部署若无法解析函数，必须报告 Runtime `unverified`，不得升级为 Runtime Verified；
3. Access dev-fixture existing-module modify：read → backup → write → reread → lint → runtime/rollback；
4. Access record navigation / focus / Dirty-NewRecord / DAO 中至少两个宿主知识案例，可由 synthetic source/fixture 驱动；
5. Excel workbook/worksheet/range ownership review；
6. Excel event re-entry / `EnableEvents` 案例；
7. Excel compile dispatch 必须报告 `unverified`；
8. Ribbon 或 xlam 中至少一个 synthetic artifact-specific case；
9. Access SaveAsText review，验证混合 dump 不直接进入 parser；
10. operator-only boundary，验证结构化工具失败后不会静默使用 generic computer-use；
11. 普通非 Office task，验证不读取 VBA workflow/reference；
12. 在 current global AGENTS 已无 VBA 段的 session 中，确认 production/write/verification/operator hard guards 仍来自 managed bundle。

如果本机 controlled Office fixtures 暂不可用，只阻塞需要 host runtime evidence 的对应 case；不得以已投用 Access 项目替代。fixture provision 后继续该 case，不需要等待下一次真实业务 VBA 需求。

发现 parity gap 时修 managed bundle，不给 global AGENTS 再新增临时兼容规则。

### M6 — Legacy Skill cutover

前提：M1–M4 与其它 M5 parity/live cases 已通过；M5-01 已明确记录为
`Access runtime execution evidence: UNVERIFIED / accepted known limitation`。
Access Eval runtime PASS 不再是 M6 的前置条件。

1. 确认当前 deployed `global-skill-router` payload 与 source 一致；
2. 记录 legacy Skill exact path；
3. 将 legacy Skill directory 移到 skill discovery root 外的 reviewed backup location；
4. 不删除其内容，不修改其 Git history；
5. 启动新的 Codex session / discovery context，确认顶层 catalog 不再出现 legacy VBA Skill；
6. 仅使用 synthetic/dev Access + Excel fixture 运行最小 managed smoke；不得触碰已投用业务项目。Access smoke 必须覆盖 router 正确选择 `runtime-ops + vba-office`、source read/static contract、production target/write guards 与 exact instance/path safety，并明确报告 Access Runtime `unverified`，不得制造 runtime claim；Excel 保留既有 runtime/artifact smoke；
7. 在 current global AGENTS 已无 VBA 段的条件下确认 adapter hard guards 仍存在；
8. 失败则立即把 legacy Skill 移回原 discovery path，并停止 cutover。

### Deferred provider/environment follow-up — Access runtime expression-resolution / live-runtime certification

This is a provider/environment follow-up, not a P6 migration gate. It may be
reopened only by a future task that explicitly requests new Access runtime
certification. It must not change the P6 evidence state, weaken identity or
fail-close contracts, or be used to claim Runtime Verified without fresh direct
behavioral evidence.

### M7 — Post-cutover closeout

前提：M6 router-only smoke 通过。

1. 新 session 验证普通 task 不携带 VBA-specific global instructions；
2. 新 session 验证 Access/Excel synthetic task 只通过 managed router 获取 VBA contract，不再发现 legacy 顶层 Skill；
3. 确认 current global AGENTS 仍保持无 VBA-specific tooling section，P6 未对其做写入；
4. 复核 legacy backup location 与恢复步骤可用；
5. 记录仍受 fixture availability 限制、但不需要真实业务项目才能补齐的证据。

M7 不修改用户级 AGENTS；其目标是证明迁移后的运行形态稳定并可恢复。

## §9 文件修改范围

预期 repository 修改集中于：

```text
development/docs/plans/070-p6-vba-skill-migration.md
development/skill/runtime-ops/adapters/vba-office.md
development/skill/runtime-ops/workflows/vba-office/**
development/skill/runtime-ops/references/vba-office/**
development/skill/runtime-ops/scripts/vba-office/**
development/skill/manifest.yaml                    # 仅当 adapter version/metadata 需要
development/tools/test_validate_skills.py          # 仅补真实 contract gate
development/tools/test_deploy_skills.py            # 仅补 payload/legacy coexistence regression
development/tools/test_*vba*                       # 若 repo 现有测试布局需要
```

只有 routing contract 真正变化时才修改 `global-skill-router/SKILL.md` 或 route generation。P6 默认不改变 scenario 名称、router 选择算法或顶层 Skill 数。

Repository 外 cutover target 只有：

```text
<target-skill-root>/vba-skill
```

用户级 `<codex-home>/AGENTS.md` 已在 P6 外手工清理，本阶段只读验证其未重新出现 VBA 专属段，不把它纳入 cutover 或 rollback ownership。

## §10 测试与验收矩阵

### A. 静态/结构测试

- `validate_skills.py` 通过；
- adapter 所引用 workflow/reference/helper 全部存在；
- 所有相对路径从 `runtime-ops` Skill root 可解析；
- deployed `library/runtime-ops` 自足，不回读 repository `references/access-vba-dev`；
- manifest 中 `vba-office` 仍只有一个 active owner；
- 顶层 managed Skill 数仍为 1。

### B. Tool contract regression

- Excel `open_workbook` 的当前参数和 safe inspection 语义与 provider 一致；
- Excel compile dispatch 只能产生 dispatch/unverified claim；
- Access compile 仍显式 unsupported；
- Access no-arg Eval path 与 parameterized path 区分；当前部署的 Access Runtime 状态必须单独报告为 `unverified`，不得把 provider capability 或候选 smoke 形状写成 Runtime Verified；
- Access/Excel session ownership 不依赖 foreground window；
- dialog mutation 只使用 structured discovery 返回的 owned HWND；
- lint hostLibraries casing/default/severity 与当前 provider contract 一致。

### C. Knowledge parity

逐项证明迁移后仍可得到会改变修复/审阅决策的规则：

- Access event callback、focus/`.Text`、record navigation、form state、DAO；
- Excel ownership、events/global state、UserForm、Ribbon、xlam；
- shared error handling、encoding、evidence/source priority；
- SaveAsText source classification。

“不再保留原文件”不是 parity failure；只有决策知识丢失或行为改变才是。

### D. Runtime/cutover

- legacy Skill 在 discovery root 外时，synthetic/dev Access/Excel task 仍命中 managed route；
- Access runtime limitation 被显式报告为 `unverified`；不再要求 Access live Eval PASS 才能完成 migration；
- global AGENTS 已无 VBA section 的当前基线下，managed adapter 仍施加 production/write/verification/operator constraints；
- 已投用 Access 项目和其它 production/authoritative Office 文件不参与 P6 验证；
- no-match session 不加载 VBA bundle；
- unrelated installed Skills 不被 cutover/deployer修改；
- rollback 演练至少一次：legacy Skill 可移回 discovery root。

## §11 Rollback contract

P6 有三类状态，分别恢复，不制造统一“大回滚器”。

### Repository implementation rollback

使用正常 Git/repository recovery 恢复 P6 implementation files。不要改外部 MCP provider 来掩盖 skill regression。

### Managed deployment rollback

继续使用 P4 deploy manager 的既有 router snapshot/rollback。P6 不改变该 contract。

### User-level cutover rollback

Legacy Skill：

- cutover 前只移动、不删除；
- route/capability 失败时移回原 `<target-skill-root>/vba-skill`；
- 恢复后用新 session 验证 legacy discovery。

Global AGENTS 不属于 P6 rollback：VBA 段已经由用户在本计划实施前手工删除。若 managed bundle 暴露 parity gap，修 repository/managed payload 根因；不得把旧 VBA 段临时写回 global AGENTS 作为兼容层。

Rollback 成功只代表恢复 legacy Skill discovery，不代表 managed migration 已完成。只有重新经过 M5–M7 才能再次退役。

## §12 验收标准

P6 只有同时满足以下条件才可改为 `done`：

1. `vba-office` 是平台内唯一 VBA runtime owner；没有新增顶层 VBA Skill 或 MCP wrapper Skill。
2. 两个外部 MCP 的当前 tool ABI 与 adapter 一致，已知 compile/open_workbook 漂移已解决。
3. verification model 不再把 Excel `status: unverified` 当 Compile Verified，也不把 Access runtime smoke 当 compile evidence。
4. legacy 四个 workflow 与 Access/Excel/shared decision knowledge 已迁入 managed lazy-load tree，且没有明显 capability/knowledge regression。
5. duplicate tool-contract/profile 信息已按 D4/D5 收敛，不形成新的多份事实源。
6. SaveAsText gate/helper 与 regression test 保留，混合 dump 不会被误送入 VBA parser。
7. 用户级 global `AGENTS.md` 在 P6 开始前已无 VBA-specific tooling section；P6 未重新写入该段，且 managed bundle 已独立承接 §6 hard guards。
8. legacy `vba-skill` 已移出顶层 Skill discovery，但有可逆退役副本；router-only synthetic/dev Office smoke 通过；M5-01 的 Access runtime limitation 已显式记录且不被写成 PASS。
9. Access/Excel mutation 仍要求 exact target、pre-read、recoverable path、reread、host-correct static analysis 与 targeted runtime evidence where available；Access Runtime 必须明确报告 `unverified`，production/authoritative target 未被默认授权。
10. 已投用 Access 项目未作为 P6 fixture、smoke target 或 mutation target。
11. operator-only boundary 保留；structured tooling 不可用时不会静默退化到 generic desktop interaction。
12. router 的顶层 Skill 数仍为 1，no-match/其它 scenario 不预读 VBA workflow/reference。
13. targeted tests、validator、deploy tests 与 relevant full validation 全绿；P1–P4 已有 contract 无回退。
14. 至少一次 cutover rollback path 被验证可恢复 legacy Skill discovery。

当前收尾状态：P6 仍为 `executing`，M5 已以 accepted Access runtime limitation
收尾；M6/M7 尚未执行，且本次收尾不标记 P6 `done`。

任何以下情况成立，P6 不得标 done：managed adapter 仍与 provider ABI 冲突；legacy Skill 退役后才发现唯一知识来源；managed bundle 缺失原 global AGENTS 已承载的 VBA hard guard；为了 parity 把整个 legacy SKILL 正文塞进 adapter；deploy manager 开始无界管理用户级配置；为完成迁移而触碰已投用 Access 项目；非 Office task 会预读 VBA bundle；或 verification claim 强度高于实际证据。

## §13 明确排除

P6 不做：

- 修改 `vba-doctor` / `vba-lint` 实现来配合现有 Skill 文案；
- 新增 Office GUI 自动化、foreground-window fallback 或通用 mouse/keyboard control；
- SQL Server、Android/Gradle、WSL adapter 工作；
- 项目业务 VBA、具体 form/query/workbook 名称迁入 generic bundle；
- 删除 `references/access-vba-dev`；
- 建立通用 legacy-Skill migration framework；
- 重新写入、恢复或由 deploy manager 自动编辑用户级 `AGENTS.md` 的 VBA 段，或自动删除任意顶层 Skill；
- 为短期 coexistence 保留永久兼容层；
- 仅为了目录对称而保留重复 profile/tool-contract。

## §14 与并行 Kotlin/Gradle 分支的合并约束

本计划使用 `070-p6-vba-skill-migration.md`，即使当前 branch 尚未包含 `060` 文件，也不得占用 `060`。并行 Kotlin/Gradle 工作合并后预期使用 `060`，两者没有功能依赖。

P6 implementation 应尽量避免无必要修改 `000-platform-skeleton.md`、全局路线索引或其它并行 phase 的计划文件。若 merge 后需要在总 roadmap 中登记 P5/P6，只在 integration commit 统一更新，避免两个 feature branch 同时改 roadmap 造成无意义冲突。

本次“计划落盘”只新增本文件；不在计划分支中提前实施 VBA migration。
