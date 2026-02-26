# EVAL_METRICS — Ecom AIGC Content Evaluation System

本文件定义电商 AIGC 内容的评测指标体系，用于：
- 版本选优（同一商品多版本生成后排序）
- 线上门槛（不合规则拒绝发布）
- A/B 对比（有无词库/事实约束/不同prompt的效果差异）
- 面试讲述：把“写脚本”升级为“产品化评测体系”

---

## 0. 评测对象与输入

### 评测对象（被评估文本）
- Title（标题）
- Bullets（5条卖点）
- Detail（结构化详情）
- Video Script（3镜头脚本）

### 评测输入（用于自动化评测）
- FACT_SHEET（来自 product_facts + evidence，Day6）
- KEYWORDS（类目高频词/短语，Day3）
- POLICY_RULES（禁用词/风险声明，Day5）
- CONTENT_SPEC（输出规范，Day4）

---

## 1. 指标总览（0–100分）

我们把评测拆成 5 个指标：准确性、风格一致、可读性、关键词覆盖、合规性。
每个指标输出 0–100 分，并给出可解释的子项与扣分原因。

最终总分为加权和（见第6节）。

---

## 2. 准确性（Fact Consistency）

### 定义
生成内容是否严格基于 FACT_SHEET，不编造不存在的事实。

### 为什么重要
电商内容的最大风险是“幻觉”：编造成分/功效/认证/适用人群，会触发平台或监管风险，且损害用户信任。

### 自动评测（MVP）
- Fact-only 约束：输出中出现 FACT_SHEET 之外的“强事实声明”则扣分
- 重点检查字段：
  - ingredients（成分）
  - claims/highlights（卖点）
  - price（价格）
  - medical-like claims（治疗/处方/医美级等）
- 简化实现：
  1) 允许词/短语白名单：来自 FACT_SHEET 的品牌名、品名、类目、highlights、价格数值
  2) 黑名单触发：出现“治疗/治愈/处方/替代药物/医美级”等视为强幻觉风险

### 评分规则（0–100）
- 初始 100
- 每发现 1 条“未在 FACT_SHEET 的强事实声明”扣 20
- 最低 0
- 输出解释：列出可疑片段 + 对应缺失事实字段

### 人工抽检（推荐）
- 每批次随机抽取 20 条人工核验（是否引用事实/是否夸大）

---

## 3. 风格一致（Brand Tone）

### 定义
文案是否符合“电商语气/品牌调性”：简洁、口语化、不过度夸张；并与 CONTENT_SPEC 一致。

### 自动评测（MVP）
- 格式通过率：是否符合 CONTENT_SPEC 的结构（标题长度、bullet条数、详情结构、3镜头脚本）
- 绝对化/夸张词惩罚：出现“最强/第一/100%/立刻见效”等扣分（也会在 Policy 里扣）
- 语气一致性：避免医学化/学术化表达；避免过多感叹号/全大写

### 评分规则（0–100）
- 初始 100
- 违反格式（如 bullet 不是 5 条 / 详情缺段 / 视频不是 3 镜头）：每项扣 25
- 夸张语气（过多感叹号、极端词）：每项扣 10

---

## 4. 可读性（Readability）

### 定义
文案是否易读、信息密度合适、无明显重复/冗长。

### 自动评测（MVP）
- 长度区间：过短/过长扣分
- 重复率：重复词占比过高扣分
- 结构清晰度：bullet 每条短、详情按段落输出

### 建议阈值（可调整）
- Title：<= 60英文字符（或<=30中文）
- Bullets：5条，每条<=40英文字符（或<=20中文）
- Detail：建议 80–250词（或 120–400字）
- Video：3镜头，每镜 1–2 句

### 评分规则（0–100）
- 初始 100
- 超出长度区间：扣 10–20
- 重复率>0.4：扣 15
- 语言噪声（乱码/大量无意义词）：扣 20

---

## 5. 关键词覆盖（SEO / 类目词）

### 定义
文案是否覆盖该类目用户最关注的关键词/短语（来自 Day3 keyword_lexicon），提高“像真实电商”的程度，同时提升站内搜索/SEO。

### 自动评测（MVP）
- 命中数：在文本中命中多少个 KEYWORDS（按类目 Top N）
- 至少要求：
  - Title 命中 >=1
  - Bullets 命中 >=2（硬约束）
  - Detail 命中 >=2

### 评分规则（0–100）
- coverage_score = min(100, unique_hits * 15)
- 并在输出中给出：命中的关键词列表

---

## 6. 合规性（Policy）

### 定义
是否触发禁用词/风险宣称（来自 Day5 policy_rules.json），以及是否按规则补充“注意事项”。

### 自动评测（MVP）
- 命中禁用词：高危（banned_terms / medical claims）直接扣分
- 命中风险词（allergy/irritation等）：必须在“注意事项”出现 patch test 提示，否则扣分

### 评分规则（0–100）
- 初始 100
- 每条 high severity 违规扣 30
- 每条 medium severity 违规扣 15
- 若出现风险词但无注意事项：额外扣 20
- 输出解释：列出 rule_id + 命中词 + 建议改写

---

## 7. 总分公式（加权）

建议权重（可根据业务阶段调整）：
- Fact Consistency：0.30
- Policy：0.25
- Keyword Coverage：0.20
- Readability：0.15
- Brand Tone：0.10

总分：
Score = 0.30*Fact + 0.25*Policy + 0.20*Coverage + 0.15*Readability + 0.10*Tone

### 线上门槛建议（示例）
- Policy < 80：拒绝发布
- Fact < 80：拒绝发布
- 总分 < 75：进入人工审核

---

## 8. 输出格式（评测报告建议）

每个版本输出：
- total_score
- fact_score + fact_issues
- policy_score + violations
- coverage_score + keyword_hits
- readability_score
- tone_score
- pass/fail（是否达到上线门槛）

