# PRD One-pager — Ecom AIGC Content Lab

## Goal
把电商内容生产从“能生成”升级为“可控、可评测、可上线”的闭环：生成→合规→评分→选优→导出→回流。

## Users
- 运营/投放：需要快速产出可投放素材（多版本 A/B）
- 风控/审核：需要自动提示违规风险与可解释原因

## Core flow
Input(Category/Product) → FACT_SHEET grounding → Multi-variant generation → Compliance + Scoring → Compare & Select → Export(JSON/TXT) → Regression eval(promptfoo) + Iteration log

## Key constraints
- 事实约束：仅引用 FACT_SHEET，不确定则“未明确说明”
- 输出规范：标题/卖点/详情/脚本结构化输出
- 合规门槛：violations=0 & total≥70 才可上线（可配置）

## Metrics (proxy)
- publishable rate（可上线比例）
- violations rate（违规率）
- keyword coverage（命中关键词数）
- regression pass rate（promptfoo 通过率）
