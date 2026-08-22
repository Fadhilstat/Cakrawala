# AI trading research roadmap

This roadmap is designed for decision preparation, not autonomous execution. Every model or agent must add evidence quality before it earns a place in the workflow.

## What is worth adding

### 1. Multi-agent research council

Reference: TradingAgents, Apache-2.0.

Useful pattern: separate macro, market, news, positioning, risk, and editor roles, then force disagreement to be recorded instead of averaging everything into one confident answer. Cakrawala already follows this pattern in the private Daily Forex Council. The next improvement is structured evidence scoring and explicit contradiction flags.

### 2. Probabilistic time-series forecasts

Candidates:

- Amazon Chronos-Bolt Small, Apache-2.0, about 47.7M parameters according to its Hugging Face model card.
- IBM Granite TinyTimeMixer R2.1, Apache-2.0, with small checkpoints suitable for scheduled CPU research.

These models should run only in offline or scheduled research. Their output should be quantiles and uncertainty bands, not a direct BUY or SELL label. Each candidate must be tested with walk-forward evaluation, completed candles only, transaction-cost-aware diagnostics where relevant, and simple benchmarks such as last value, drift, or logistic baselines.

### 3. Financial headline sentiment

ProsusAI FinBERT is a useful candidate for headline tagging, but Cakrawala keeps it observe-only until the exact license and intended-use constraints are confirmed. Sentiment is context, not a price forecast. Duplicate headlines, delayed publication, and central-bank wording changes can all distort naive sentiment scores.

### 4. Quant research architecture

References:

- FinRL, MIT: useful for reinforcement-learning experiment design, but RL should remain a late-stage sandbox because reward design can make poor strategies look strong.
- Microsoft Qlib, MIT: useful for reproducible separation of datasets, experiments, models, records, and evaluation.

Cakrawala should borrow architecture ideas, not import large frameworks unless a specific feature justifies the operational cost.

## Private decision-prep stack

The private Vercel workspace should eventually combine these layers:

1. Source health and freshness
2. Daily and multi-horizon FX reference trends
3. CFTC institutional positioning
4. Scheduled macro event risk
5. Central-bank and official macro news
6. Market-session and liquidity context
7. Deterministic decision-prep alignment
8. Model forecast distributions from validated research models
9. News sentiment as a secondary annotation
10. Cross-model disagreement and confidence calibration
11. Risk budget and position-sizing tools
12. Written thesis, invalidation, and post-trade journal review

No single layer is allowed to become an execution command.

## Promotion standard

A model is research-only until it satisfies all of the following:

- point-in-time features and labels
- completed observations only
- expanding or rolling walk-forward testing
- explicit benchmark comparison
- calibration or probabilistic scoring when probabilities are produced
- transaction-cost assumptions documented when strategy diagnostics are shown
- no leakage from future news, revised macro releases, or finalized event outcomes
- repeatable run with pinned model revision and source provenance
- model-health and freshness gates
- independent risk review

If it fails any gate, it remains useful as research evidence but stays outside production signal roles.

## Runtime strategy

Vercel should remain lightweight. Heavy inference belongs in scheduled GitHub Actions or a local sandbox so the owner dashboard stays responsive and the project does not require a paid server. Model artifacts should be small, reproducible, and retained only when they add measurable value.
