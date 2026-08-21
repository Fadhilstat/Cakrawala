# Cakrawala Intelligence Terminal

**Open intelligence for Indonesia and the world**

Cakrawala is an open-data research terminal for understanding market, macro, positioning, event,
and risk evidence without pretending that one indicator can explain the whole market. It is built
as a public information product and an owner-only research workspace, not as an automatic profit
machine.

Live app: `https://cakrawala-terminal.streamlit.app`

Public Mode works without private credentials. Personal Mode stays closed until owner OIDC and a
separate private database are configured.

## Trading research workflow

The terminal follows a practical sequence: **context -> plan -> risk gate -> execution readiness ->
review**.

### Public Mode

- **Overview**: source health, BTC movement, momentum, volatility, futures crowding, news watch,
  inflation, and BMKG context.
- **News & Research**: searchable official Federal Reserve and BIS headlines with transparent
  reading-priority tags. Attention is not a price-direction forecast.
- **Positioning**: Binance public futures crowding plus CFTC institutional TFF positioning. Retail
  and institutional horizons stay separate.
- **Market Structure**: 90-day BTC/USDT candlesticks, returns, range, momentum, realized volatility,
  drawdown, and volume.
- **Macro & Events**: Indonesia/global macro context plus official BLS scheduled release risk.
- **Research Desk**: Asia, London, and New York session awareness with an explainable research-bias
  board built from price, volatility, crowding, funding, and news evidence.
- **Risk Tools**: risk-budget position sizing, reward/risk calculation, historical expectancy, and a
  deterministic equity illustration.
- **Bot & Tool Radar**: weekly primary-source review of actively maintained open trading tools. A
  tool can become a sandbox candidate but is never installed or trusted automatically.
- **Execution Readiness**: source, news, model-promotion, freshness, and authorization gates. If the
  evidence is not sufficient, the correct output remains `NO SIGNAL`.

### Personal Mode

After owner authentication and private storage are configured, Personal Mode adds:

- private portfolio ledger
- immutable trade plans with thesis and invalidation
- post-trade journal with results measured in R
- reusable playbook entries

Private rows do not enter the shared public cache.

## Free and traceable data path

The public experience is designed around interfaces that do not require a paid subscription:

| Evidence | Provider | Public interface |
| --- | --- | --- |
| Indonesia statistics | BPS | WebAPI, optional server-side key |
| Weather and earthquakes | BMKG | Official open JSON |
| Global macro | World Bank | Indicators API V2 |
| Macro series | FRED | Optional server-side API key |
| Spot market structure | Binance | Public market-data-only API |
| Futures crowding | Binance USD-M Futures | Public long-short, open-interest, and funding endpoints |
| Institutional positioning | CFTC | Public TFF Futures-Only dataset |
| Scheduled U.S. event risk | BLS | Official iCalendar release schedule |
| U.S. policy/regulation news | Federal Reserve | Official RSS |
| Global central-bank context | BIS | Official RSS |

Source interfaces were rechecked on 21 August 2026. See `docs/sources.md` for endpoint, attribution,
and evidence-policy details.

## Evidence before signal

Every external response is untrusted at the network boundary. Cakrawala uses HTTPS-only adapters,
exact host allowlists, bounded timeouts and retries, response-size limits, content-type checks,
provenance hashes, schema validation, and explicit failure handling.

The terminal distinguishes:

1. **descriptive evidence**, such as price, volatility, crowding, and COT;
2. **research bias**, which is explainable context and not a trade instruction;
3. **model evidence**, which must pass walk-forward, point-in-time, health, and benchmark gates;
4. **deterministic signal policy**, which is the only layer allowed to return BUY, HOLD, AVOID, or
   NO SIGNAL.

Missing, stale, rejected, or unhealthy evidence cannot be upgraded into a trade by an LLM. Language
models may explain stored evidence but cannot create or override the deterministic policy decision.

## Metavulus reference boundary

Cakrawala studies useful workflow ideas visible in public trading products, including Metavulus, but
it does not copy proprietary research, paid datasets, private signals, scoring logic, trade ideas,
branding, screenshots, or visual assets. Free equivalents are independently implemented from public
or official sources. See `docs/trading-feature-map.md`.

## Bot and tool research

A weekly research process reviews current open trading bots, execution frameworks, and research
tools from primary sources. Candidates are classified as observe, sandbox candidate, or exclude.

The process cannot:

- install a bot automatically;
- copy exchange credentials;
- enable withdrawal access;
- merge an unreviewed dependency change;
- bypass model-health, freshness, risk, authorization, or signal-policy gates;
- send a real-money order simply because a new tool looks promising.

This keeps the project current without turning software discovery into a supply-chain risk.

## Repository map

```text
app/                         Streamlit entrypoint
configs/                     providers, schedules, models, signals, tool radar
migrations/                  raw, public, and private PostgreSQL schemas
src/cakrawala/data/          secure provider adapters and provenance
src/cakrawala/intelligence/  news, risk, bias, sessions, model and signal policy
src/cakrawala/personal/      owner-only database access
src/cakrawala/terminal/      public and private interface composition
src/cakrawala/observability/ source health
tests/                       regression, data-boundary, and security tests
docs/                        architecture, sources, feature map, and runbooks
.github/workflows/           CI and source-health automation
```

## Local QA

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e '.[dev]'
python -m compileall -q src scripts app
python scripts/check_no_em_dash.py
ruff check .
pytest
```

Run the terminal:

```bash
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

## Public and Personal boundary

Public Mode is anonymous and uses only public research state. Personal Mode uses Streamlit's native
OIDC flow and remains unavailable until Google auth settings and a stable owner `sub` are stored in
the server-side secret store. An authenticated account whose `sub` does not match the configured
owner is denied.

Personal storage uses a separate PostgreSQL connection. Portfolio history, trade plans, journal
entries, and playbook entries remain outside shared public caching. Historical research records are
append-only at the database layer.

## Deployment

The no-mandatory-cost portfolio path uses GitHub and Streamlit Community Cloud. Public Mode does not
require a database. Personal Mode can use a free PostgreSQL tier when its current limits fit the
project.

Public preflight:

```bash
python scripts/preflight_deployment.py --mode public
python scripts/check_sources.py
```

Personal preflight:

```bash
python scripts/preflight_deployment.py --mode personal
```

See `docs/runbooks/deployment.md` before enabling Personal Mode.

## Limitations

Cakrawala is a research system, not a guarantee of returns. Public APIs can become unavailable,
provider schemas can change, historical relationships can fail, and execution conditions can differ
from research assumptions. Market sessions are timezone-aware approximations and do not replace an
exchange holiday calendar. The BLS calendar covers scheduled BLS releases, not every global macro
event. COT is weekly evidence, not a live positioning feed.

BMKG attribution must remain visible wherever BMKG data is displayed.

This product uses the FRED API but is not endorsed or certified by the Federal Reserve Bank of St.
Louis.

## License

MIT. See `LICENSE`.
