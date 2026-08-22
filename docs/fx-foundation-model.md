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

## Why the baseline stays simple

A complicated benchmark can hide whether the foundation model adds real value. The last-value forecast is deliberately hard to misunderstand and difficult to contaminate with future information. A later phase may add stronger statistical baselines, but those should be reported alongside the simple benchmark rather than replacing it.

## Runtime and cost boundary

The scheduled workflow runs once a week on a standard GitHub-hosted runner for this public repository. No Hugging Face paid endpoint, OpenAI API, GPU rental, broker API, or Vercel inference service is required. If standard free-runner behavior or model availability changes, the workflow should fail visibly instead of enabling a paid service automatically.

## Promotion policy

A foundation model can only become a production candidate after repeated successful walk-forward runs, stable source provenance, stronger baseline comparisons, leakage review, calibration review, and an explicit human-approved promotion PR. The scheduled workflow has read-only repository permissions and cannot promote a model on its own.
