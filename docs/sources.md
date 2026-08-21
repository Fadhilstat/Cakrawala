# Source Registry

Source status was rechecked on 21 August 2026. Runtime ingestion still treats every response as
untrusted until transport, content type, size, schema, and quality checks pass.

| Source | Approved interface | Authentication | Production note |
| --- | --- | --- | --- |
| BPS Statistics Indonesia | `https://webapi.bps.go.id` | API key | Keep the key server-side |
| BMKG earthquake | `https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json` | None | Show BMKG attribution wherever the data appears |
| BMKG weather | `https://api.bmkg.go.id/publik/prakiraan-cuaca` | None | Respect BMKG request limits and attribution |
| World Bank Indicators V2 | `https://api.worldbank.org/v2` | None | Use historical values with their reference year |
| FRED | `https://api.stlouisfed.org` | API key | Follow FRED API terms and attribution |
| Binance Spot market data | `https://data-api.binance.vision/api/v3` | None for market data | Market-data-only host |
| Federal Reserve press releases | `https://www.federalreserve.gov/feeds/press_all.xml` | None | Official RSS feed for policy and regulatory news |
| BIS press releases | `https://www.bis.org/doclist/all_pressrels.rss` | None | Official RSS feed for global central-bank context |

## News evidence policy

The News & Research workspace currently ingests official Federal Reserve and BIS press-release feeds.
Headlines are tagged with transparent keyword rules for themes such as monetary policy, liquidity,
financial stability, regulation, and digital assets. The attention score is a reading-priority aid,
not a sentiment forecast and not a trade direction.

Bank Indonesia remains an approved official source watch. Its public press-release pages were live
when rechecked on 21 August 2026, but Cakrawala will not add a fragile scraper merely to increase the
headline count. A stable machine-readable interface should be approved before automated ingestion.

## Trading tool research policy

Trading bots and execution frameworks are not data providers and are never trusted automatically.
Weekly research records primary-source activity, release evidence, security considerations, and an
observation or sandbox status in `configs/tool_radar.yaml`. No external bot may be installed or
connected to production solely because it appears in the radar.

BMKG must be shown as the source wherever its data is displayed.

FRED notice: This product uses the FRED API but is not endorsed or certified by the Federal Reserve
Bank of St. Louis.
