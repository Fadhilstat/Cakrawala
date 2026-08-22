# Source Registry

Source status was rechecked on 22 August 2026. Runtime ingestion still treats every response as
untrusted until transport, content type, size, schema, and quality checks pass.

| Source | Approved interface | Authentication | Production note |
| --- | --- | --- | --- |
| BPS Statistics Indonesia | `https://webapi.bps.go.id` | API key | Keep the key server-side |
| BMKG earthquake | `https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json` | None | Show BMKG attribution wherever the data appears |
| BMKG weather | `https://api.bmkg.go.id/publik/prakiraan-cuaca` | None | Respect BMKG request limits and attribution |
| World Bank Indicators V2 | `https://api.worldbank.org/v2` | None | Use historical values with their reference year |
| FRED | `https://api.stlouisfed.org` | API key | Follow FRED API terms and attribution |
| Binance Spot market data | `https://data-api.binance.vision/api/v3` | None for market data | Price and volume evidence only |
| Binance USD-M futures | `https://fapi.binance.com` | None for public market data | Long-short ratio, open interest, mark price, and funding context |
| ECB FX reference rates | `https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml` | None | Daily working-day reference rates for research context, not transaction pricing |
| CFTC TFF Futures Only | `https://publicreporting.cftc.gov/resource/gpe5-46if.json` | None | Weekly institutional positioning, not intraday sentiment |
| BLS release calendar | `https://www.bls.gov/schedule/news_release/bls.ics` | None | Official scheduled U.S. labor and inflation release times |
| Investing.com Economic Calendar | `https://www.investing.com/economic-calendar/` | None for normal web viewing | Secondary human-readable cross-check only, not a bulk-ingestion source |
| Federal Reserve press releases | `https://www.federalreserve.gov/feeds/press_all.xml` | None | Official policy and regulatory news RSS |
| BIS press releases | `https://www.bis.org/doclist/all_pressrels.rss` | None | Official global central-bank context RSS |
| ECB press releases | `https://www.ecb.europa.eu/rss/press.html` | None | Official ECB press-release RSS |

## News evidence policy

The News & Research workspace ingests official Federal Reserve, BIS, and ECB press-release feeds.
Each feed is isolated from the others. If one source is temporarily unavailable, healthy sources
remain visible; the entire news workspace fails only when all configured macro feeds are unavailable.
Headlines are tagged with transparent keyword rules for themes such as monetary policy, liquidity,
financial stability, regulation, and digital assets. The attention score is a reading-priority aid,
not a sentiment forecast and not a trade direction.

Bank Indonesia remains an approved official source watch. Its public pages were accessible when
rechecked on 21 August 2026, but Cakrawala does not add a fragile scraper merely to increase the
headline count. A stable machine-readable interface should be approved before automated ingestion.

## FX reference-rate policy

Currency Strength uses official European Central Bank euro foreign-exchange reference rates. The
ECB publishes the reference set on working days and states that the rates are intended for
information purposes. Cakrawala therefore uses them only to compare recent currency movement versus
the euro. They are not displayed as executable FX prices and are not used to estimate slippage or
broker fills.

The strength transform is transparent. ECB rates are quoted as units of each currency per euro, so
Cakrawala reverses the sign of the percentage rate change when expressing whether that currency has
strengthened or weakened against the euro. The raw reference date remains visible in the workspace.

## Positioning evidence policy

Two positioning horizons are kept separate.

**Crowd futures context** uses Binance public USD-M futures endpoints. The terminal reads global
long-short account share, open interest, mark/index price, and funding context. Crowd extremes are
risk flags only. They do not trigger contrarian trades automatically.

**Institutional context** uses the CFTC Traders in Financial Futures Futures-Only public dataset.
The dataset exposes Dealer, Asset Manager/Institutional, Leveraged Funds, and other reporting
categories. Cakrawala calculates net positioning as reported longs minus reported shorts and shows
week-over-week changes where two observations are available. COT is weekly evidence and must not be
presented as a live positioning feed.

The CFTC public dataset was accessible when rechecked on 21 August 2026 and showed an August 2026
update. Exact report dates remain visible in the terminal rather than being described as real-time.

## Event-risk and economic-surprise policy

The automated free event calendar uses the official BLS release schedule. Event times are normalized
with timezone information when the calendar provides a `TZID`. A scheduled release near the current
time raises a review warning; it never predicts the release outcome.

Investing.com Economic Calendar was confirmed accessible on 22 August 2026 and exposes the fields
`Actual`, `Forecast`, and `Previous`, including high-impact events such as CPI, payrolls, GDP,
unemployment, and central-bank decisions. Cakrawala may consult that page during bounded daily
research as a secondary human-readable consensus reference. It is not used as a bulk scraper,
redistribution feed, or historical training database.

For a released event, the `Actual` value and release timing should be cross-checked against the
relevant official primary source whenever one is available. `Forecast` is treated as third-party
market consensus, not ground truth. `Previous` may later be revised, so revision risk must remain
visible.

The economic-surprise layer compares actual versus forecast and actual versus previous values, but
it does not use a naive higher-is-always-better rule. Examples:

- higher payrolls or stronger retail sales can support a stronger-activity interpretation;
- a higher unemployment rate or higher jobless claims usually points the other way;
- hotter CPI or PCE can add hawkish policy pressure, but the FX effect depends on the current policy
  regime and market pricing;
- central-bank rate decisions require statement and guidance context, not only the numeric rate;
- missing or stale forecast data produces insufficient evidence instead of a forced view.

Daily market and forex briefs can use the resulting surprise context as one input among price trend,
positioning, event proximity, source freshness, model health, and risk controls. It cannot override
those gates or place an order.

Additional automated calendars can be added only when the source has a stable machine-readable
interface and its automated use can be validated without a mandatory paid subscription.

## Trading tool research policy

Trading bots and execution frameworks are not data providers and are never trusted automatically.
Weekly research records primary-source activity, release evidence, security considerations, and an
observation or sandbox status in `configs/tool_radar.yaml`. No external bot may be installed or
connected to production solely because it appears in the radar.

The weekly process may create a feature branch and pull request after source verification. It may
not merge an unreviewed dependency change, copy exchange credentials, enable withdrawals, or bypass
Cakrawala's model-health, freshness, risk, authorization, or deterministic signal gates.

## Attribution

BMKG must be shown as the source wherever its data is displayed.

ECB FX reference rates must be described as reference information rather than executable market
prices.

FRED notice: This product uses the FRED API but is not endorsed or certified by the Federal Reserve
Bank of St. Louis.
