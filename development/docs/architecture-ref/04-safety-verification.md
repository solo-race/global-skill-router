# 04. 安全护栏与验证阶梯

关注点：行为红线怎么写、何时必须停、验证到什么程度才许声称完成。

## SpineCodex 参考

护栏**章节化**：GitHub State Mutation Policy（babysit-pr/SKILL.md:116-139，不许回复人类评论、不许动他人 thread）、Git Safety Rules（:141-155）、Stop Conditions (Strict)（:188-201）——同时枚举"何时必须停"与"何时禁止停"。重试有预算上限（flaky 最多 3 次）；越权动作默认禁止（update-v8-version/SKILL.md:36 "Do not publish tags, releases, or pushes unless the user asked"）。

## recycling-company-investigation

护栏前置为 **Contract 章节**（SKILL.md:12-30），行为红线清单化：不发明 SourceRecord/source_id、unknown ≠ negative、冲突路由人工复核、禁评分禁自动排除禁删除、"Do not bypass login, CAPTCHA, robots rules, paywalls…"（:27）。人工复核是**强制终态**：覆盖缺口永远留在 manual_review_reasons 里可见。

## access-vba-dev

**认识论护栏**：
- 验证阶梯 Static < Compile < Runtime，顶格因宿主不对称（Access 无 compile 档），铁律"Never report a higher level than was actually achieved"（docs/testing.md:13-14），报告须写明实际达到的最高档。
- 静态/runtime 边界由**工具分离强制执行**：lint 结果永不证明运行时状态，宏运行成功永不证明编译通过。
- 写安全 = 规范化备份约定：`backups/<host>/<file-stem>/<module>.<yyyyMMdd-HHmmss>.txt`，回滚走同一工具（tool-contracts/vba-doctor.md:152-178）；set_vba_code 是整模块替换，无备份即破坏性。

## 全局架构规范

1. 护栏强度随破坏力分级：会写数据库、改 VBA 工程、发外网的技能 = 最高档必配（Contract 清单 + Stop Conditions + 备份/回滚约定）。
2. 验证阶梯 + "只报实际达到的档位"普适采用——这是认识论纪律，不限 VBA 域。
3. 禁止行为写成 Contract 清单条款，不散落散文。
4. 自治循环类技能必须有双向停止条件（必须停 + 禁止停）与重试预算。
