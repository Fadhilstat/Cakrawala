# FX foundation-model sandbox

Cakrawala treats foundation-model forecasting as research infrastructure, not as a shortcut to a trading signal.

## Current sandbox

The first candidate is `amazon/chronos-bolt-tiny`, pinned to model revision `059e58e2d88886bc5254bceb365ffe5c71bcc261`. The model is Apache-2.0 licensed and intentionally uses the smallest Chronos-Bolt checkpoint so the evaluation can run on a standard CPU GitHub-hosted runner without adding a paid inference service.

The model is loaded only by the dedicated research workflow. It is not installed in the Vercel request path and is not part of the Streamlit public runtime.

## Data

Evaluation uses the ECB full-history euro foreign-exchange reference-rate XML feed. These are official daily reference rates. They are not executable broker quotes and should not be used as a substitute for spread-aware transaction pricing.

The first evaluation covers EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, and USDCAD. Each history is capped to the latest 1,200 ECB observations for bounded runtime. A forecast horizon of five ECB observations is used, so the horizon is measured in published observations rather than calendar days.

## Evaluation

The workflow uses multiple point-in-time walk-forward origins. Every forecast sees only observations available before its forecast origin. The model returns 10th, 50th, and 90th percentile forecasts.

For each pair the artifact records:

- median forecast MAE;
- last-value MAE as the simple benchmark;
- relative MAE improvement versus that benchmark;
- directional accuracy relative to the value at the forecast origin;
- empirical coverage of the nominal 80 percent interval;
- source provenance and model revision.

The research gate requires positive MAE improvement for every configured pair and at least 50 percent average direction accuracy. Passing this gate only means the candidate deserves more research. It does not change `configs/models.yaml`, does not populate a production role, and does not enable BUY, SELL, LONG, SHORT, or broker execution.

## First verified run

The first accepted workflow run completed on 22 August 2026 using ECB observations through 21 August 2026. Each pair contributed eight point-in-time forecast origins with a five-observation horizon, giving 40 evaluated forecasts per pair.

| Pair | Model MAE | Last-value MAE | MAE improvement | Direction accuracy | 80% interval coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| EURUSD | 0.008159 | 0.007388 | -10.44% | 45.0% | 82.5% |
| GBPUSD | 0.009019 | 0.007455 | -20.98% | 32.5% | 80.0% |
| USDJPY | 1.110472 | 1.035461 | -7.24% | 45.0% | 87.5% |
| USDCHF | 0.005372 | 0.005349 | -0.43% | 60.0% | 77.5% |
| AUDUSD | 0.005489 | 0.004976 | -10.31% | 67.5% | 75.0% |
| USDCAD | 0.006681 | 0.006225 | -7.32% | 37.5% | 82.5% |

Chronos-Bolt Tiny did not beat the last-value MAE benchmark on any configured pair. Average directional accuracy was about 47.9 percent. The research gate therefore failed and the model remains research-only.

This result is intentionally kept as evidence rather than tuned away. Repeatedly changing the model, horizon, pair set, or threshold against the same evaluation window would weaken the value of the backtest. Any next experiment should be defined before a new untouched evaluation window is used and should include stronger statistical baselines alongside the simple last-value reference.

## Why the baseline stays simple

A complicated benchmark can hide whether the foundation model adds real value. The last-value forecast is deliberately hard to misunderstand and difficult to contaminate with future information. A later phase may add stronger statistical baselines, but those should be reported alongside the simple benchmark rather than replacing it.

## Runtime and cost boundary

The scheduled workflow runs once a week on a standard GitHub-hosted runner for this public repository. No Hugging Face paid endpoint, OpenAI API, GPU rental, broker API, or Vercel inference service is required. If standard free-runner behavior or model availability changes, the workflow should fail visibly instead of enabling a paid service automatically.

## Promotion policy

A foundation model can only become a production candidate after repeated successful walk-forward runs, stable source provenance, stronger baseline comparisons, leakage review, calibration review, and an explicit human-approved promotion PR. The scheduled workflow has read-only repository permissions and cannot promote a model on its own.
