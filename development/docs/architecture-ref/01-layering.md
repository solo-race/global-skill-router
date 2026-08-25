# 01. 信息架构与分层

关注点：知识切几层、何时加载、references 按什么轴分桶。

## SpineCodex 参考

**扁平三层渐进披露**：frontmatter description 只做路由发现 → 正文承载操作指令 → references/*.md 承载深度背景（babysit-pr/SKILL.md:220-223 将 CI 分类清单推给 references/heuristics.md，正文只留一行引用 :86）。references 按**关注点**分桶（一文件一事：api-notes vs heuristics）。

缺陷：粒度失控——最小 336B 到最大 16.7KB；babysit-pr 正文内部冗余（Monitoring Loop Pattern :157-177 大量重复 Core Workflow :24-40），触发时 17KB 全量进上下文。

## recycling-company-investigation

同构三层，但 references 按**研究生命周期**三分桶：发现层 search-taxonomy / 交付层 output-schema / 裁决层 evidence-rules——每层对应工作流的一个阶段而非一个主题。SKILL.md 6.2KB 克制，章节序列 Contract → Workflow → Research lanes → Evidence handling → Required packet sections。

## access-vba-dev

**五层单向依赖栈** + repo 元层：

```
L1 政策入口   skill/SKILL.md          # 分类分发 + 证据政策 + 加载索引
L2 程序       workflows/{diagnose,modify,test,review}.md
L3 ABI        tool-contracts/{vba-doctor,vba-lint}.md
L4 知识       references/{shared,access,excel}/   # 宿主分类分桶
L5 配置       profiles/*.yaml
元层          README/AGENTS.md/docs/*  # 条件阅读路由
```

加载纪律最严格：§4 显式加载索引 "Do not load every reference file for every task"（skill/SKILL.md:86-113）；repo 元层同样条件阅读（AGENTS.md Required Reading，"Do not load all documentation by default"）。

风险：L1 自身 617 行/22.8KB——违反自家 development-rules.md 第一条 "Keep SKILL.md Small"；宿主语义（§6–10a）本应下沉 L4；加载索引线性膨胀且单点压在 L1。

## 全局架构规范

1. 分层按重量可选：轻技能止步 L1+L4（正文+references），重技能全开五层。
2. references 分桶轴全库一致（按关注点 / 生命周期 / 宿主，选一并声明），不混轴。
3. 加载索引单点维护、条目化；正文控制在千字节级，长策略下沉 references/。
4. repo 元层条件阅读：入口文件只做路由，不做知识容器。
