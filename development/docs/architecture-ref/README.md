# 00. 索引：三次 Skill 架构审阅的模块化拆分

本目录将三次 skill 架构审阅按**架构模块**（而非按来源）拆分为轻量参考文档，供在 `development/skill/` 重建 global skill 体系时按工作面查阅。

## 三次审阅

| # | 审阅对象 | 类型定位 | 全文存档 |
|---|---------|---------|---------|
| ① | `references/SpineCodex-skills/`（14 个上游技能） | 扁平方法论库 | [skill-architecture-evaluation.md](skill-architecture-evaluation.md) |
| ② | `references/cusomer-research-skills/recycling-company-investigation/` | 自建·方法论型（纯模型原生） | 内容已拆入下列模块文档 |
| ③ | `references/access-vba-dev/` | 自建·工程型（五层栈 + repo 元层） | 内容已拆入下列模块文档 |

## 模块地图

| 模块 | 文档 | 关注什么 |
|------|------|---------|
| 01 信息架构与分层 | [01-layering.md](01-layering.md) | 知识切几层、何时加载、references 按什么轴分桶 |
| 02 任务模型与分发 | [02-task-model.md](02-task-model.md) | 触发后如何组织执行：单流程 / 流水线段位 / 固定模式分类 |
| 03 工具契约与运行时边界 | [03-tool-contracts.md](03-tool-contracts.md) | 确定性逻辑放哪、模型与工具的接口形态 |
| 04 安全护栏与验证阶梯 | [04-safety-verification.md](04-safety-verification.md) | 行为红线、停止条件、验证等级纪律 |
| 05 可发现性与接口元数据 | [05-discoverability-metadata.md](05-discoverability-metadata.md) | frontmatter、触发句式、openai.yaml、路由 |
| 06 知识治理与质量保障 | [06-knowledge-quality.md](06-knowledge-quality.md) | 出处元数据、准入门槛、测试策略 |
| 07 移植性与环境假设 | [07-portability-environment.md](07-portability-environment.md) | 路径解析、环境依赖声明、跨场景迁移 |

## 阅读指引

- 重建某一面（如"给新技能写 tool contract"）时，只读对应模块文档。
- 需要审阅①完整证据链时读全文存档；模块文档只保留结论级引用（`文件:行号` 均为实际读到的内容）。
- 各模块末尾"全局架构规范"是该模块对重建的直接规范输出；全部规范合并即 global 架构骨架。
