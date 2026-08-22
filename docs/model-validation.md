# Model validation

Cakrawala does not treat the presence of a machine-learning model as evidence that the model is useful.
A model must survive point-in-time validation, benchmark comparison, health checks, and the project
promotion gate before it can be considered for any downstream decision workflow.

## Current baseline

The first trained predictive baseline is `logistic_direction_v1`.

Its job is deliberately narrow: estimate the probability that the next BTC/USDT daily session closes
above its own opening price. The baseline is not a price target, not a trading signal, and not an
execution engine.

Features are computed only from a fully completed daily candle at time `t`. The evaluated trade
session starts at the next daily open and ends at the next daily close. This avoids assuming that a
position can be entered at the same closing price that was needed to calculate the features.

The feature set contains:

- 1-day return;
- 3, 7, 14, and 30-day momentum;
- 7, 14, and 30-day realized volatility;
- distance from 10, 20, and 50-day simple moving averages;
- daily range relative to the open;
- 20-day volume z-score.

The estimator is a standardized logistic regression with balanced class weights. Training uses an
expanding walk-forward window, starts after 365 usable observations, and retrains every 30
observations. There is no shuffled train/test split.

## Data boundary

The automated backtest uses the existing Binance public market-data adapter and does not require an
API key. The runner records the source URL, fetch timestamp, byte count, response SHA-256, raw candle
count, completed candle count, and the close time of the latest accepted candle.

A daily candle is accepted only when its Binance close timestamp is earlier than the provider fetch
timestamp. An in-progress daily candle is excluded before feature construction or target creation.

This completed-candle filter has its own regression test.

## First verified live backtest

The first accepted live run was produced on 21 August 2026 from the pull-request validation workflow.
It received 1,000 Binance daily candles and accepted 999 completed candles. The latest accepted
candle closed at 20 August 2026 23:59:59.999 UTC.

The final out-of-sample window contained 584 predictions from 14 January 2025 through 20 August
2026. The expanding training history began on 14 January 2024.

| Metric | Model | Probability baseline |
| --- | ---: | ---: |
| Accuracy | 47.26% | 49.32% |
| Balanced accuracy | 47.21% | 50.00% |
| Brier score | 0.25485 | 0.25080 |
| Log loss | 0.70318 | 0.69474 |
| ROC AUC | 0.46744 | 0.48341 |

Lower is better for Brier score and log loss. The model's Brier score was worse than the simple
training-history class-frequency baseline. Relative Brier improvement was about -1.62%.

The promotion gate therefore returned **FAIL** with reason
`benchmark_improvement_below_gate`.

## Latest verified rerun

A fresh pull-request workflow completed on 22 August 2026 using Binance observations through
21 August 2026. It again received 1,000 daily candles and accepted 999 fully completed candles.
The evaluation still contained 584 out-of-sample predictions, now covering 15 January 2025 through
21 August 2026.

| Metric | Model | Probability baseline |
| --- | ---: | ---: |
| Accuracy | 47.09% | 49.32% |
| Balanced accuracy | 47.04% | 50.00% |
| Brier score | 0.25507 | 0.25081 |
| Log loss | 0.70366 | 0.69476 |
| ROC AUC | 0.46496 | 0.48255 |

Relative Brier improvement was about -1.70%. The promotion gate again returned **FAIL** with reason
`benchmark_improvement_below_gate`.

That repeated failure is preserved as useful evidence. `logistic_direction_v1` remains
**research-only** and is not connected to Cakrawala's deterministic decision states or broker
execution.

## Strategy diagnostic

A separate long-or-cash diagnostic enters at the next daily open only when predicted probability is
at least 0.55. The test assumes 10 basis points of round-trip transaction cost for every invested
session, with no leverage and no short selling.

For the latest 22 August rerun:

- model-driven long/cash total return: -20.93%;
- model-driven maximum drawdown: -34.53%;
- exposure: 14.21%;
- traded sessions: 83;
- hit rate while invested: 53.01%;
- continuous buy-and-hold total return after its entry and exit cost: -18.95%;
- buy-and-hold maximum drawdown: -52.97%.

The strategy diagnostic is not used to rescue a model that fails predictive validation. Exposure is
materially different from buy-and-hold, and a return comparison alone is not evidence of predictive
edge. Model promotion remains anchored to reproducible predictive performance against the declared
benchmark and governance gates.

## Automation

`.github/workflows/model-backtest.yml` runs the same validation automatically on relevant pull
requests and once a week. Each successful run stores a JSON artifact for 30 days and writes a compact
GitHub Actions summary.

The weekly workflow retrains or reruns the model on the data available at that time. It does not mean
the model is automatically promoted every week. A candidate must still beat the benchmark and pass
all governance checks before any production role can be considered.

The production-health watch also checks whether the weekly validation workflow has failed or become
stale. A failed promotion gate is not considered an operational incident. It is a valid outcome when
a model has not earned promotion.

## Promotion policy

A model candidate must satisfy the policy in `configs/models.yaml`, including:

- minimum model-health score;
- minimum relative benchmark improvement;
- maximum tolerated secondary-metric regression;
- complete walk-forward evaluation;
- point-in-time feature evidence.

Passing those checks would still not authorize real-money trading. Production integration would
require a separate reviewed change, risk review, security review, and explicit owner authorization.

## What comes next

The next model iteration should be evaluated against this baseline without repeatedly tuning against
the same final test window. Useful follow-up work includes a separately reserved evaluation period,
stronger calibration checks, regime-aware features, and comparison with models that add complexity
only when they demonstrate reproducible out-of-sample improvement.
