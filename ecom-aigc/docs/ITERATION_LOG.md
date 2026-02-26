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
