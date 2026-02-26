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
