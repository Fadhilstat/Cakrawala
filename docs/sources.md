# Source Registry

Source status was rechecked on 21 August 2026 before this normalized source tree was prepared.
Runtime ingestion still treats every response as untrusted until transport, content type, size,
schema, and quality checks pass.

| Source | Approved interface | Authentication | Production note |
| --- | --- | --- | --- |
| BPS Statistics Indonesia | `https://webapi.bps.go.id` | API key | Keep the key server-side |
| BMKG earthquake | `https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json` | None | 60 requests/minute/IP documented by BMKG |
| BMKG weather | `https://api.bmkg.go.id/publik/prakiraan-cuaca` | None | 60 requests/minute/IP documented by BMKG |
| World Bank Indicators V2 | `https://api.worldbank.org/v2` | None | V2 is the supported interface |
| FRED | `https://api.stlouisfed.org` | API key | Follow FRED API terms and attribution |
| Binance Spot market data | `https://data-api.binance.vision/api/v3` | None for market data | Market-data-only host |

BMKG must be shown as the source wherever its data is displayed.

FRED notice: This product uses the FRED API but is not endorsed or certified by the Federal
Reserve Bank of St. Louis.
