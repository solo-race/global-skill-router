# 02. 任务模型与分发

关注点：技能被触发后如何组织执行——单流程、流水线段位还是固定模式分类。

## SpineCodex 参考

默认**触发即单一编号流程**（Objective → Inputs → Workflow 编号步骤）。复杂技能带分支路径（update-v8-version 的 Core Workflow / Failure Path 双轨）。组合用**编排者薄壳**：`code-review/SKILL.md`（666B）分发到 code-review-{testing,context,change-size,breaking-changes} 四个单一关注点子模块。

## recycling-company-investigation

**流水线段位嵌入**：技能假定自己插在外部流水线 `Acquisition → Source → Signal → Fact → Score` 的 Signal→Fact 段位（SKILL.md:14），边界条款明确"Keep the pipeline boundary intact"。内部为 7 步线性 workflow（:32-52）+ research lanes 并行支线（:54-67，"Use only lanes relevant… stop when additional searches repeat the same evidence"）。

## access-vba-dev

**固定四模分类学**：每个请求必须先归入 Diagnose / Review / Modify / Test 之一（skill/SKILL.md §2:20-66），每个模式钉死一个 canonical workflow 文件。隐含状态机：diagnose→modify→test（diagnose.md 结尾移交 modify.md）；review 为并行审计轨，行为问题升级到 test.md。

预设：任务空间可穷尽划分为四模。缺口：没有 build-new / refactor-only 模式——分类学封闭性未声明的代价。

## 全局架构规范

1. 小技能单一流程即可，不强行建模。
2. 重技能必须显式任务分类学 + 每模一个 canonical 文件；分类学须声明是否封闭，并预留扩展模式的登记位置。
3. 多技能组合一律用薄壳编排者分发，不在单技能里堆多流程。
4. 技能若嵌入外部流水线，段位边界必须写成显式 Contract 条款。
