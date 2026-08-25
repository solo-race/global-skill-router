# 05. 可发现性与接口元数据

关注点：技能如何被路由器发现、触发描述怎么写、openai.yaml 何时该有。

## SpineCodex 参考

frontmatter 恰好两字段 name + description ✓；description 以 "Use when …" 收尾并列出触发短语（update-v8-version/SKILL.md:3、babysit-pr/SKILL.md:3、codex-issue-digest/SKILL.md:3）——路由召回率的关键。

缺陷：openai.yaml 仅 3/14 有且何时该加无判据；name 与目录脱钩已实际发生（code-review-breaking-changes/SKILL.md:2 为 `code-breaking-changes`）且无机械校验。

## recycling-company-investigation

frontmatter 合规 ✓；agents/openai.yaml 与 SpineCodex 约定**完全同构**：`interface.{display_name, short_description, default_prompt}`，default_prompt 内嵌 `$recycling-company-investigation` 触发。差异点：其 default_prompt 指向纯模型任务而非可运行命令——说明 openai.yaml 的判据应是"是否 agent-facing 入口"，与有无脚本无关。

## access-vba-dev

✗ **无 frontmatter**：skill/SKILL.md 617 行直接以 H1 开场。作为仓库内行为契约可行；作为全局可路由技能是致命伤——路由器无从发现它。宿主语义、验证阶梯、工具选择全部埋在正文里，没有可被检索的触发面。

## 全局架构规范

1. frontmatter 必选（name == 目录 slug；description 一句话 + Use when 触发短语）。
2. 机械校验入 CI/脚本：name==dirname、description 含触发短语、必备章节存在——审阅①的 bug 正是缺这道闸。
3. openai.yaml 判据明确化：面向用户直接调用的 agent 入口才配，判据与是否有脚本无关。
4. 中文口语请求下纯英文 description 有路由盲区 → 用场景 manifest（技能↔三大开发场景映射）补足召回。
