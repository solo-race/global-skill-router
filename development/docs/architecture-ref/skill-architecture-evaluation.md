# SpineCodex-skills 架构评估

评估对象：`references/SpineCodex-skills/` 下 14 个技能模块。目的：为在 `development/skill/` 重建 global skill 体系提供架构依据。

评估方法：全文精读 10 个代表性模块（babysit-pr、codex-issue-digest、update-v8-version、codex-bug、path-types、remote-tests、codex-pr-body、pushing-ci-changes、code-review-breaking-changes、heuristics.md），结合全量结构扫描数据（14 模块的文件清单、脚本与测试、agents/openai.yaml）。引用格式 `文件:行号` 均为实际读到的内容。

## 总体判断

核心架构成熟，值得整体继承。价值集中在四个设计决策：三层信息分离、确定性逻辑下沉到脚本、动作契约化、显式安全护栏。但它是一套 Unix 单平台、无校验机制、无版本管理的内部快照，直接照搬会把死路径和粒度失衡一并搬入。结论：**借骨架，修四处，弃三样**。

## 参考结构速览

```
<skill-name>/                  # kebab-case slug，目录名 = frontmatter name
├── SKILL.md                   # 必备：YAML frontmatter（name + description）+ 正文
├── agents/openai.yaml         # 可选（3/14）：interface.{display_name, short_description, default_prompt}
├── scripts/<name>.py          # 可选（2/14）：stdlib-only Python 助手
├── scripts/test_<name>.py     # 随脚本同置的 pytest 套件
└── references/*.md            # 可选（1/14）：深度背景笔记
```

## 优点

### 1. 三层渐进式信息披露
frontmatter `description` 只做路由发现 → SKILL.md 正文承载操作指令 → `references/*.md` 承载深度背景。证据：`babysit-pr/SKILL.md:220-223` 将 CI 分类清单推给 `references/heuristics.md`，正文只留一行引用（`:86`）。对上下文窗口稀缺的正确响应。

### 2. 确定性逻辑下沉到可测脚本，判断力留给模型
`gh_pr_watch.py` 封装全部 gh 子进程调用与 JSON 解析；SKILL.md 的 15 步工作流只消费脚本输出的结构化建议。"分支相关还是偶发失败"这类判断写在 `heuristics.md:25-36` 决策树里。代码与模型的接口是一条干净的 JSON 契约，代码侧有 pytest 纯函数测试兜底（test_gh_pr_watch.py 约 290 行、test_collect_issue_digest.py 约 750 行）。

### 3. 显式护栏章节
`babysit-pr/SKILL.md:116-139` GitHub State Mutation Policy（不许回复人类评论、不许动他人 thread）；`:141-155` Git Safety Rules；`:188-201` Stop Conditions (Strict)——同时枚举"何时必须停"与"何时禁止停"。`update-v8-version/SKILL.md:36`："Do not publish tags, releases, or pushes unless the user asked"。自治长任务代理的防灾难设计。

### 4. 输出格式契约化
`codex-issue-digest/SKILL.md:36-58` 把报告写成规格：首行必须是单行判断性 headline、安静日固定句式、attention_marker 只准照抄不准自造、来源脚注行格式，并附两个完整范例。产出质量因此可复现。

### 5. 触发路由写法统一
复杂技能的 description 全部以 "Use when …" 收尾并列出触发短语（`update-v8-version/SKILL.md:3`、`babysit-pr/SKILL.md:3`、`codex-issue-digest/SKILL.md:3`）。这是路由召回率的关键。

### 6. 模块自包含 + 测试同置
每个技能目录零交叉依赖、可单独移植。测试用 `importlib.util.spec_from_file_location(Path(__file__).with_name(...))` 加载被测模块，任何 cwd 下免包装即跑。

### 7. 编排者-子技能分解
`code-review/SKILL.md`（666B 薄壳）分发到 code-review-{testing,context,change-size,breaking-changes} 四个单一关注点子模块。组合而不膨胀。

### 8. 自带验证入口
`codex-issue-digest/SKILL.md:111-127` 独立 `## Validation` 章节，含 dry-run 与测试命令。

## 缺点

| # | 问题 | 证据 |
|---|------|------|
| 1 | 无一致性校验，name 与目录脱钩已实际发生 | `code-review-breaking-changes/SKILL.md:2` frontmatter 为 `code-breaking-changes` |
| 2 | 上游路径硬编码，移植即断 | 正文命令全是 `.codex/skills/babysit-pr/scripts/…`、`.github/scripts/rusty_v8_bazel.py`；在本仓库副本中这些路径全部不存在 |
| 3 | 粒度失控且文件内冗余 | 最小 336B（breaking-changes），最大 16.7KB（babysit-pr）；后者 Monitoring Loop Pattern（`:157-177`）大量重复 Core Workflow（`:24-40`），触发时 17KB 全量进上下文 |
| 4 | Unix 单一环境假设 | python3/bash//tmp/Sapling sl/bazel/just/devbox；对本项目 Windows 原生场景无一可直接运行 |
| 5 | 运行时依赖零声明 | 脚本要求 gh CLI、Python≥3.8，无任何 requirements/manifest |
| 6 | 无版本/来源追踪 | 技能级无版本字段，快照与上游漂移不可见（仅 collector 内部有 SCRIPT_VERSION = 5） |
| 7 | 接口元数据规则缺失 | 仅 3/14 有 agents/openai.yaml，何时该加没有判据 |
| 8 | 测试覆盖极不均衡 | 14 个技能中仅 2 个脚本有测试 |

## 可借鉴之处

### A. 直接继承的骨架

1. **模块解剖**：kebab-case 目录 = slug = frontmatter name；SKILL.md 必备，scripts/references/agents 按需可选。
2. **章节序列**：Objective → Inputs → Workflow（编号步骤 + bash 块）→ Stop Conditions → References。
3. **"Use when …" 触发句式**写入每个 description。
4. **脚本 + 同置 pytest** 模式：WSL Python 筛选场景几乎原样复用（stdlib-only + importlib 加载 + monkeypatch）。
5. **动作契约模式**：Windows 场景的确定性操作（如 Access 数据库体检）写成输出结构化 JSON 的脚本，模型只消费建议动作，而非即兴拼 COM 调用。
6. **护栏章节**：对会写数据库、改 VBA 工程的高破坏力自动化为必选项（例：编译失败连续 N 次即停止报告；修改生产 accdb 前 stop-and-ask）。
7. **编排者模式**：如 access-release 薄壳分发到 vba-lint / vba-compile / runtime-smoke 子技能。

### B. 必须补强的四处（重建时应超越参考库）

1. **一致性校验脚本**（置于 development/skill 的元数据位置）：检查 name==dirname、description 含触发短语、必备章节存在。参考库正是缺它才带着 bug 入库。
2. **路径自指化**：命令一律用相对技能自身的 `{SKILL_DIR}/scripts/…` 写法，杜绝 `.codex/skills/<name>/` 式硬编码——参考库最痛的移植伤。
3. **每技能声明运行时依赖**：一行字段（Python≥3.8 / gh / Access / JDK 等），并配根级 manifest 把技能映射到三大开发场景（Windows SQL/Access/VBA、Android on Windows、WSL Python），弥补中文口语请求下纯英文 description 的路由弱点。
4. **版本与来源字段**：标注上游出处与本地修改记录，防止重建后静默漂移。

### C. 明确不搬的三样

1. Unix 专属命令块（python3/bash heredoc//tmp）——Windows 场景改写为 PowerShell/COM/gradle 等价物；
2. 组织私有内容（go/workflow-approvals、devbox、OpenAI 内部约定）；
3. babysit-pr 式 17KB 单体正文——长策略拆进 references/，正文控制在千字节级。

## 一句话结论

这套参考架构回答了"skill 该长什么样"（分层、契约、护栏），没回答"如何保证质量与可移植"（校验、依赖声明、版本化）——后者是重建时应超越它的地方。
