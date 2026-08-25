# 06. 知识治理与质量保障

关注点：知识条目的出处与准入、测试策略、知识库自身的质量控制。

## SpineCodex 参考

references 一文件一事、零交叉依赖。版本意识仅存在于脚本内部（collector `SCRIPT_VERSION = 5`），技能级无版本/来源字段——快照与上游的漂移不可见。测试模式优秀但覆盖极不均（2/14）：pytest 同置 + importlib 文件加载 + monkeypatch，纯函数覆盖解析/排序/决策逻辑。

## recycling-company-investigation

**词汇治理**：英文是唯一可执行语言；本地化别名需"业务审批 + 翻译评审 + 测试"三门放行才可执行（search-taxonomy.md:93-95）。**证据四态词汇表**：confirmed / inferred / unknown / conflicting 各有判定规则（evidence-rules.md:12-23），配来源层级与实体匹配规则——知识主张在产出侧就被强制分类。

## access-vba-dev

三件套最完整：
- **出处元数据**：每条知识主张标五种 evidence type 之一（documented_fact / evidence_based_inference / verified_empirical_behavior / project_convention / community_guidance）+ 源优先级（skill/references/shared/sources.md）。
- **准入门槛**："Add information only when it is likely to change an agent's decision"（docs/development-rules.md:76）；加规则前六步流程（明确主张→定证据类型→查一手文档→定宿主范围→找例外→配 fixture）；GPL 隔离条款（:87）。
- **回归哲学**：测错误的 agent 决策而非文件存在；规则尽量配正负案例对（false-positive 抗性与检出同等重要，docs/testing.md:18-44）；controlled fixtures 为 gitignore 本地资产。

## 全局架构规范

1. 知识条目强制出处元数据（证据类型 + 来源 + 日期），无出处的"最佳实践"不入库。
2. 准入门槛写进开发规则：会改变 agent 决策才加入。
3. 机械一致性校验脚本（frontmatter/命名/章节）作为入库闸门。
4. 测试按技能重量分级：纯方法论技能免测；带脚本技能必配同置 pytest 纯函数套件。
