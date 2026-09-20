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
