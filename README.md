# Global Skill 结构构建

## 目的

为了加强对Codex开发的环境助力，故而建立此项目，通过简介成熟的SKILL结构，来为本地Codex运行环境提供一个完整的SKILL体系。

## 当前状态

项目已形成可验证的技能控制平台：`development/skill/manifest.yaml` 注册正式 Skill、owner-contained adapters 与只读设计来源，`development/tools/validate_skills.py` 负责生命周期、契约、场景路由和 deployment-role 门禁。当前由单一 active `global-skill-router` 暴露顶层入口，两个 active framework 作为 router modules；`development/tools/deploy_skills.py` 负责 routed payload 的 plan/apply/verify/rollback，`references` 仍是只读设计输入，不是部署依赖。

## 开发与校验

Python 工具由 uv 管理。首次使用或依赖变更后运行 `uv sync`，再运行：

```bash
uv run python development/tools/validate_skills.py
uv run python development/tools/run_tests.py
```

## 开发项目背景

当前本机开发场景有：

1. Windows原生项目，如SQL数据库管理，ACCESS前端管理、ACCESS/EXCEL VBA编写；
2. Windows系统下的安卓应用开发；
3. WSL中的原生筛选项目，使用Python脚本。

## 动态开发委派（0.2）

`development-delegation` 仍是全局继续路由模块，不替代后续场景技能。
总控按任务选择 Direct、Planned 或 Exploratory，按需把角色模块分配给宿主
Agent；角色职责、专业能力和模型身份分别管理，不要求每次固定启动五个角色。

- Direct 使用简短执行契约；未知问题先只读探索；架构、迁移等工作使用详细计划。
- 监督模式与审查策略独立；高风险变更仍要求独立审查，策略不授予写入权限。
- 并发实施要求隔离工作区、明确所有权和依赖图；合并后重新验证集成状态。
- YAML 仅声明策略，宿主负责实际调度、权限、模型和额度；离线测试不代表真实 Agent 调度已验证。
- 旧会话行为通过显式 legacy 兼容选项保留；不会改写已注册 Agent 或静默替换模型。

详细实施与验证记录见 [动态委派计划](development/docs/plans/150-dynamic-delegation.md)。
