# Daily Market Intelligence

Cakrawala separates daily decision support from model promotion. A daily market view can change as new completed observations arrive, while a model is only refreshed or promoted through a separate validation workflow.

## Owner-only daily brief

The private route `/personal/market` combines two evidence paths:

1. Major FX pairs use official European Central Bank daily reference rates already available in Cakrawala.
2. Equities can optionally use Twelve Data through an owner-only API key and a private watchlist.

The displayed states are:

- `BUY BIAS`
- `SELL BIAS`
- `WAIT`
- `INSUFFICIENT`

These states are decision-support labels. They are not broker orders and they do not guarantee returns.

The current deterministic layer evaluates completed-price momentum over 1D, 5D, and 20D windows. A buy or sell bias requires all three windows to agree after a small neutral deadband. Mixed horizons return `WAIT`. Missing, stale, future-dated, or insufficient observations return `INSUFFICIENT`.

This simple layer is intentionally transparent. It gives the owner a consistent baseline that can challenge more complex model or AI narratives instead of being replaced by them.

## FX source boundary

ECB reference rates remain the preferred zero-cost official context for major FX pairs. They are reference rates, not executable broker quotes. The private workflow must still verify broker price, spread, liquidity, session conditions, scheduled event risk, and position sizing before any manual trade decision.

Official reference:

`https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html`

## Optional equity source

Twelve Data is integrated only as an optional Personal Mode provider.

Environment variables:

```text
TWELVE_DATA_API_KEY=<server-side secret>
PERSONAL_EQUITY_WATCHLIST=BBCA@XIDX,AAPL@XNAS
```

The watchlist uses the ISO 10383 market identifier code after `@` when a venue is needed. Twelve Data currently exposes a dedicated Indonesia Stock Exchange page under MIC `XIDX`, which was rechecked on 22 August 2026. Actual symbol and subscription availability must still be validated by the provider at request time.

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

Twelve Data documentation confirms that individual plans are intended for personal or internal use and do not allow redistribution or commercial display to third parties. Cakrawala therefore keeps this provider out of the public Streamlit surface and does not publish its raw market data in public GitHub artifacts.

Confirmed references checked on 22 August 2026:

- `https://twelvedata.com/docs`
- `https://twelvedata.com/exchanges/XIDX`
- `https://support.twelvedata.com/en/articles/5332349-commercial-and-personal-usage`
- `https://twelvedata.com/terms`

Provider access and exchange licensing can change. The source policy must be rechecked before expanding public use or changing the subscription tier.

## Daily versus weekly work

Daily brief:

```text
fresh source evidence
        |
completed observations
        |
1D / 5D / 20D alignment
        |
BUY BIAS / SELL BIAS / WAIT / INSUFFICIENT
        |
event and risk review
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

A weekly refresh does not mean a weekly production promotion. Poor results stay visible. A new model version must earn promotion rather than inherit it.

## Analysis boundaries

Daily market output should include the evidence date, source, directional state, short rationale, and invalidation condition. When an event calendar, model-health check, source freshness check, or private risk guard disagrees with a directional view, the safer state is `WAIT` or `INSUFFICIENT`.

AI may summarize or challenge the evidence, but it cannot override deterministic freshness, authorization, source-quality, model-health, or risk gates.
