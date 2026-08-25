# 07. 移植性与环境假设

关注点：技能换环境还能不能跑——路径解析、环境依赖声明、外部引用所有权。

## SpineCodex 参考

**移植即断**：正文命令硬编码上游部署路径（`.codex/skills/babysit-pr/scripts/…`、`.github/scripts/rusty_v8_bazel.py`），在本仓副本中全部不存在；部分验证目标（`core/suite`）根本不在仓库。Unix 单平台假设（python3/bash//tmp/Sapling sl/bazel/just）；组织私有内容混入（go/workflow-approvals、devbox）。运行时依赖零声明。

## recycling-company-investigation

**悬空外部契约**：`config/search_terms.yaml`、`SourceRecord`/`source_id`、`customer_screening.evidence`、`schemas/company_result.schema.json` 全部指向不可见宿主项目——standalone 时 canonical 模式不可运行，只有方法论层可迁移。另有两个隐含假设：web 搜索/抓取能力环境原生存在；人工复核者环内存在。结构可扩展 ✓，内容不可迁移 ✗。

## access-vba-dev

三源中唯一正面解决移植性的：
- **路径自指化**："All relative paths in this skill resolve against the directory containing SKILL.md"（skill/SKILL.md:114）——杜绝部署路径硬编码；代价是整树必须原子移动。
- 残余耦合：L3/L5 焊死在两个具体 MCP 服务器上（vba-doctor/vba-lint），全局复用要求目标环境注册合同兼容的实现；单机单用户 Office 运行时假设；fixture 二进制为 gitignore 本地资产，新克隆须先供给才能跑 fixture 验证（docs/testing.md:68-69），且 docs 明示了这一点。

## 全局架构规范

1. 路径自指化为硬规范：相对 SKILL.md 所在目录解析，禁止 `.codex/skills/<name>/` 式绝对部署路径。
2. 环境依赖逐技能显式声明一行（Python≥3.8 / gh / Access / MCP 服务器名等）。
3. 外部 schema/config 引用必须重定向到全局层自己的位置并标注所有权——悬空引用要么落地要么删除。
4. 本地资产类依赖（fixture 等）必须在文档中声明供给方式，不假装新克隆即可全量验证。
5. 平台命令块按目标场景写原生等价物（PowerShell/COM/gradle），不默认 bash 化。
