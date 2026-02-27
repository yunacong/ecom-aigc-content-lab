# RESULTS — Ecom AIGC Content Lab（结果报告）

## 1) 数据概览
- 数据来源：Kaggle Sephora Products & Reviews
- 本地处理：构建 `product_facts.csv`（事实表）+ `reviews.csv`（评论表）
- Demo 数据：`data_sample/`（用于 Streamlit Cloud 展示）

## 2) 核心能力交付（按链路）
**(1) 结构化数据层**
- 两张核心表：product_facts（事实约束）/ reviews（证据来源）

**(2) 词库与风险词**
- keyword_lexicon：按类目抽取高频词（正向卖点候选）
- 风险词：过敏/刺痛/不适等 → 触发注意事项

**(3) 输出规范**
- CONTENT_SPEC：标题/卖点/详情/脚本的硬约束，使生成可控、可评测

**(4) 合规校验**
- policy_rules.json + compliance_check(text) → violations 列表与改写建议

**(5) 多版本生成与评分**
- 多版本生成（3–5个版本）
- 评分：合规（扣分）+ 关键词覆盖 + 可读性 → 总分

**(6) 对比与选优看板（compare page）**
- 版本对比表（分项指标、总分、可发布状态）
- Top 失败原因统计（违规/缺词/过长/过短）
- 一键推荐最优版本 + 解释理由

**(7) 回归评测（Promptfoo）**
- 评测集：test_cases.csv（10条起步）
- 断言：标题长度、禁用词、expected_keywords 至少命中 1 个
- 结果：
  - baseline：8/10（80%）
  - 修复关键词注入/截断策略后：10/10（100%）
- 报告产出：promptfoo_report.html / promptfoo_report.json

## 3) 典型 badcase（3个）→ 归因 → 修复
> 你先写 2 个（来自 Day13 的 FAIL），第 3 个写“合规触发 treat→care”即可

**Badcase A：关键词未命中（P420652）**
- 现象：expected=moisturizer/hydrating/night，但 title 未包含关键词
- 归因：拼接后截断导致关键词丢失
- 修复：预留关键词长度，再截断 brand+name
- 结果：回归通过

**Badcase B：标题截断导致关键词丢失（P269122）**
- 现象：expected=serum/hydrating/glow，但 title 被截断
- 归因：长度约束优先截断了后缀
- 修复：同上（关键词优先保留）
- 结果：回归通过

**Badcase C：合规触发（treat/treatment）**
- 现象：标题含 treat 被判违规/高风险
- 修复：统一替换为 care，并在合规模块提示“避免医疗化承诺”

## 4) 结论与下一步
- 已实现：可控生成 + 合规拦截 + 评分选优 + Demo 展示 + 回归评测闭环
- 下一步：
  - 扩展评测集 10 → 30+（覆盖更多类目/长尾）
  - 断言扩展到全 bundle（bullets/detail/video）
  - 接入真实 LLM（可选）并记录 token 成本与延迟
