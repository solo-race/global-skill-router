# 03. 工具契约与运行时边界

关注点：确定性逻辑放在哪，模型与工具之间的接口是什么形态。

## SpineCodex 参考

**子进程 JSON 契约**：脚本封装全部 gh 子进程调用与解析，输出结构化 `actions` 动作标记（`retry_failed_checks` / `diagnose_ci_failure` / `stop_pr_closed` 等），模型只消费建议动作。脚本 stdlib-only；输出契约 = JSON stdout（indent=2 sort_keys）或 watch 模式 JSONL 流；退出码约定（错误 stderr + 1，Ctrl-C 130）。

## recycling-company-investigation

**零工具契约**：web 搜索/抓取假定为环境原生能力，无 API 名、无 key 配置；检索状态 `accessible | partial | failed` 是纯散文词汇（output-schema.md:36、evidence-rules.md:33）。同时存在**悬空外部契约**：`config/search_terms.yaml`、`SourceRecord`、`schemas/company_result.schema.json` 指向不可见宿主项目（全仓 grep 不存在）。

## access-vba-dev

**MCP 显式 ABI 合同**：tool-contracts/ 两份文档钉死工具名、签名、默认值、返回形态、失败消息与每宿主执行路径（vba-doctor 21 工具、vba-lint 4 工具），权威 = 外部服务器源码；观察到的不一致作为证据记录。配置注入由 **agent 中介**："neither external MCP server reads these files automatically"——profile 值由 agent 抄进工具调用；连 `["Excel"]` 大写 / `["access"]` 小写这种端点间大小写差异都作为承重细节编码进技能。

## 三档谱系与全局规范

三源恰好给出工具边界的三档谱系：

| 档位 | 形态 | 适用 |
|------|------|------|
| 低 | 环境原生假设（recycling） | 纯方法论、无确定性操作 |
| 中 | 子进程 JSON 契约（SpineCodex 脚本） | 有 CLI 可封装的确定性逻辑 |
| 高 | 显式 ABI 合同（access-vba-dev MCP） | 重工程、多端点、失败语义复杂 |

全局规范：
1. 按确定性需求选档，不越级加复杂度。
2. 重技能强制显式合同文档（工具名/签名/失败语义三要素齐备）。
3. 全局考题 = **合同兼容性最小公共集**：不同技能的合同若焊死在不同服务器上，每个重技能都是孤岛——需要一份跨技能的工具合同兼容约定。
