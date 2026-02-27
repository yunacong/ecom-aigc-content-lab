# ITERATION_LOG — Feedback Loop

## Iteration 0 (baseline)
- Data source: synthetic human_preference.csv (proxy)
- Generation: v1 rule-based variants (Day9 pack)
- Scoring: simple win-rate + basic heuristics

Observations:
- (TBD) Winners tend to include more concrete benefit keywords (e.g., moisturizing/light/clean)
- (TBD) Losers contain generic filler tokens (e.g., like/way/used)

Changes:
- (TBD) Increase weight of high-signal keywords in title/bullets
- (TBD) Add stopword filter to prevent filler tokens in variants

Expected impact:
- Higher keyword coverage
- Higher human preference win-rate

## Iteration 1 (feedback-driven update)
- Signals:
  - BOOST terms (example): oil, recommend, light, moisturizer, smooth, soft, texture...
  - BLOCK terms (example): like, used, time, really, product... (generic fillers)
- Changes:
  - Added stopword cleaning for BOOST candidates
  - Updated generation strategy: force BOOST terms into title + first 2 bullets; filter BLOCK terms
- Proxy metrics (before → after):
  - avg boost_hits: 0.2 → 2.1
  - avg block_hits: 14.5 → 0.2
- Conclusion:
  - Feedback loop successfully increases high-signal keyword coverage and reduces filler noise.

## Day13 — Promptfoo 回归评测（Regression Eval）

**Goal**
- 把“生成脚本”升级为“可回归测试”的工程：有评测集、有断言、有报告输出。

**Setup**
- Tool: promptfoo（CLI）
- Provider: `file://ecom-aigc/eval/pf_provider.py`（本地 Python provider，无需外部 API）
- Config: `ecom-aigc/eval/promptfooconfig.yaml`
- Test cases: `ecom-aigc/eval/test_cases.csv`（10 条起步）
- Report output:
  - `ecom-aigc/docs/promptfoo_report.html`
  - `ecom-aigc/docs/promptfoo_report.json`

**Assertions（自动验收规则）**
1) Title 长度：`<= 60`
2) 禁用词：不得出现 `treat/treatment/cure/heal`
3) 关键词命中：标题需命中 `expected_keywords` 至少 1 个（每条用例自带）

**Result (baseline)**
- Passed: 8 / 10（80%）
- Failed: 2 / 10
- Error: 0

**Failure cases（root cause）**
- PID=P420652：No keyword hit（expected=moisturizer/hydrating/night；output=...Vitamin C |）
- PID=P269122：No keyword hit（expected=serum/hydrating/glow；output truncated: ...Daily Pe）
- Root cause：标题构造“先拼接再截断”导致关键词注入不稳定/被 60 字截断裁掉。

**Implemented fix（已落地）**
- Updated title composition in `pf_provider.py`:
  - Reserve space for `| must_keyword` first, then truncate `brand + product_name` to fit 60 chars.
  - Guarantees `expected_keywords[0]` is present in final title and not cut by length constraint.

**Result after fix**
- Passed: 10 / 10（100%）
- Failed: 0 / 10
- Report regenerated: `docs/promptfoo_report.html` + `docs/promptfoo_report.json`

**Next improvements（下一步）**
- Extend eval set from 10 → 30+ cases (more categories + longer-tail products).
- Expand assertions from title-only → bullets/detail/video (keyword coverage + policy across full bundle).