# Daily Market Intelligence

Cakrawala separates daily decision support from model promotion. A daily market view can change as new completed observations arrive, while a model is only refreshed or promoted through a separate validation workflow.

## Owner-only daily brief

The private route `/personal/market` combines two evidence paths:

1. Major FX pairs use official European Central Bank daily reference rates, the official BLS release calendar for near-term event risk, and a bounded macro-surprise snapshot when it is fresh.
2. Equities can optionally use Twelve Data through an owner-only API key and a private watchlist.

The displayed states are:

- `BUY BIAS`
- `SELL BIAS`
- `WAIT`
- `INSUFFICIENT`

These states are decision-support labels. They are not broker orders and they do not guarantee returns.

The deterministic price layer evaluates completed-price momentum over 1D, 5D, and 20D windows. A base buy or sell bias requires all three windows to agree after a small neutral deadband. Mixed horizons return `WAIT`. Missing, stale, future-dated, or insufficient observations return `INSUFFICIENT`.

For FX, that base state then passes through two additional context gates. Cakrawala must be able to verify the official scheduled-event calendar before it keeps a directional FX bias. If the calendar cannot be checked, the state becomes `INSUFFICIENT`. A scheduled release inside the near-term event window changes a directional state to `WAIT`. Fresh macro-surprise evidence may support the price direction or veto it when there is a material conflict, but macro evidence cannot create a directional bias on its own.

This layer remains intentionally transparent. It gives the owner a consistent baseline that can challenge more complex model or AI narratives instead of being replaced by them.

## Model health visibility

The Daily Market Brief also shows the current model-role state from `configs/models.yaml`. Each production role is labelled as `PRODUCTION`, `RESEARCH_ONLY`, or `BASELINE_ONLY`, together with the assigned model, latest verified run when available, and freshness status.

The current configuration has no promoted model assigned to expected return, direction probability, or volatility. That means the daily board is explicitly baseline-only even when a deterministic BUY BIAS or SELL BIAS appears. Research models do not silently strengthen a daily label unless a separate promotion decision assigns them to a production role.

A promoted model is considered stale when its latest verified run is more than eight days old or cannot be parsed. A baseline-only role is not marked stale because no production model is being relied upon. Missing or malformed model configuration fails visibly in the owner dashboard rather than being hidden.

## FX source boundary

ECB reference rates remain the preferred zero-cost official price context for major FX pairs. They are reference rates, not executable broker quotes. The official BLS release calendar is used as a near-term event-risk gate. The bounded macro snapshot is secondary context and is excluded when stale or unavailable.

A directional FX label therefore means that completed-price momentum is aligned and no deterministic context gate has vetoed it. It still does not mean that broker spread, liquidity, slippage, session conditions, or account-level risk are acceptable. Those checks remain part of the manual owner decision.

Each FX row exposes a compact decision path beside the final state. The path records the base completed-price state, official event-calendar status, macro alignment, model context, and final state. This keeps a directional label auditable and makes it clear when the result is baseline-only, research-only, production-backed, or unavailable. The model context remains informational until an eligible promoted model is explicitly wired into a deterministic gate.

Official references:

- `https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html`
- `https://www.bls.gov/schedule/news_release/bls.ics`
- `https://www.bls.gov/schedule/2026/home.htm`

The bounded economic-calendar snapshot may use a third-party consensus reference for Actual, Forecast, and Previous, while released Actual values are cross-checked against an official primary source when available. Consensus is evidence, not ground truth, and it never bypasses source, freshness, model-health, or risk gates.

## Optional equity source

Twelve Data is integrated only as an optional Personal Mode provider.

Environment variables:

```text
TWELVE_DATA_API_KEY=<server-side secret>
PERSONAL_EQUITY_WATCHLIST=BBCA@XIDX,AAPL@XNAS
```

The watchlist uses the ISO 10383 market identifier code after `@` when a venue is needed. Twelve Data exposed a dedicated Indonesia Stock Exchange page under MIC `XIDX` when the source policy was rechecked on 22 August 2026. Actual symbol and subscription availability must still be validated by the provider at request time.

The adapter:

- accepts daily history only for this workflow;
- caps requested history;
- validates symbol, exchange, and MIC identifiers;
- prevents ambiguous requests that send both an exchange and MIC code;
- uses HTTPS and an exact provider host allowlist;
- applies bounded timeout, retry, response-size, and content-type controls through the shared HTTP layer;
- validates response schema and OHLC consistency;
- redacts the API key from provenance URLs;
- never sends the API key to the browser;
- does not create placeholder data when the source or key is unavailable.

Twelve Data documentation indicated that individual-plan data was intended for personal or internal use when it was last reviewed. Cakrawala therefore keeps this provider out of the public Streamlit surface and does not publish its raw market data in public GitHub artifacts. Provider access, licensing, and plan terms can change, so the source policy must be rechecked before expanding use or changing the subscription tier.

References reviewed for the current private-provider policy:

- `https://twelvedata.com/docs`
- `https://twelvedata.com/exchanges/XIDX`
- `https://support.twelvedata.com/en/articles/5332349-commercial-and-personal-usage`
- `https://twelvedata.com/terms`

## Daily versus weekly work

Daily FX brief:

```text
fresh ECB completed observations
        |
1D / 5D / 20D price alignment
        |
base BUY BIAS / SELL BIAS / WAIT / INSUFFICIENT
        |
official BLS event-calendar availability
        |
near-term event-risk gate
        |
fresh bounded macro support or conflict
        |
final BUY BIAS / SELL BIAS / WAIT / INSUFFICIENT
        |
model-role health visibility
        |
broker context and account-risk review
        |
manual owner decision
```

Weekly model review:

```text
refresh eligible data
        |
retrain or rerun research model
        |
walk-forward or appropriate out-of-sample validation
        |
compare with simple benchmark
        |
check calibration, costs, drift, provenance, and model health
        |
retain as research-only unless every promotion gate passes
```

The repository schedules the BTC direction baseline and the FX foundation-model sandbox weekly. A successful workflow run only proves that the evaluation executed successfully. It does not prove predictive edge, and it does not promote a model automatically. Poor results stay visible. A new model version must earn promotion rather than inherit it.

## Analysis boundaries

Daily market output should include the evidence date, source, directional state, short rationale, invalidation condition, and model-role status. A missing official event calendar makes the FX state `INSUFFICIENT`. Nearby scheduled event risk or a material macro conflict makes the directional state `WAIT`. Stale or unavailable bounded macro evidence is treated as missing context rather than invented evidence.

AI may summarize or challenge the evidence, but it cannot override deterministic freshness, authorization, source-quality, model-health, event-risk, or private risk gates. No daily label places, modifies, or closes a broker order.

