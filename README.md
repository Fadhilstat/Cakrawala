# Cakrawala Intelligence Terminal

**Open intelligence for Indonesia and the world**

Cakrawala is an open-data research terminal for understanding market, macro, positioning, event,
and risk evidence without pretending that one indicator can explain the whole market. It is built
as a public information product and an owner-only research workspace, not as an automatic profit
machine.

Current fallback app: `https://cakrawala-terminal.streamlit.app`

The primary web presentation is being migrated to **Plotly Dash on Render**. Streamlit remains online
as a fallback until the Render deployment passes live smoke tests. No Render production URL is
claimed before that deployment is actually provisioned and verified.

## Trading research workflow

The terminal follows a practical sequence: **context -> plan -> risk gate -> execution readiness ->
review -> improve**.

### Public research workspaces

- **Overview**: source health, BTC movement, momentum, volatility, futures crowding, funding,
  inflation, and BMKG context.
- **News**: official central-bank and policy headlines with transparent reading-priority evidence.
- **Positioning**: Binance public futures crowding plus CFTC institutional TFF positioning. Crowd
  and institutional horizons stay separate.
- **Market**: BTC market structure, realized risk, and ECB currency-strength context.
- **Macro**: Indonesia macro history plus scheduled BLS event risk.
- **AI Council**: a daily multi-role ChatGPT research brief with confidence, disagreements, risk
  flags, freshness, and source links. It cannot create or replace deterministic trade signals.
- **Risk & Tools**: deterministic position sizing, expectancy, and execution-readiness state.
- **Tool Radar**: weekly primary-source review of actively maintained trading frameworks.
- **Personal**: owner-only portfolio, plans, journal, and playbook after OIDC and private storage are
  configured.

The Dash navigation deliberately groups related features into fewer workspaces than the Streamlit
prototype. The goal is a calmer professional terminal rather than a long list of disconnected pages.

## Framework migration

The research and trading logic does not belong to a UI framework. The migration introduces:

```text
app/dash_app.py                 Dash production entrypoint
app/assets/terminal.css         responsive terminal presentation
src/cakrawala/web/              framework-neutral public evidence, cache, and OIDC boundary
src/cakrawala/intelligence/     research, risk, model, AI brief, and execution readiness policy
render.yaml                     Render Free Web Service blueprint
```

`src/cakrawala/web/public_service.py` replaces Streamlit-specific caching in the Dash path with a
small bounded process-local cache for public evidence. Personal data is never stored in that cache.
The original Streamlit presentation remains available during migration but is no longer the target
architecture.

## Execution boundary

Cakrawala separates research readiness from execution. The deterministic execution guard can return:

- `BLOCKED`
- `OBSERVE`
- `PAPER READY`
- `OWNER READY`

`OWNER READY` is not an order. It only means the configured evidence, model, risk, and authorization
gates are satisfied. The public application has no route that sends a real-money trade.

An emergency-stop state overrides every other readiness condition. A future broker or exchange
adapter must pass a separate paper-trading, security, credential, audit, and licensing review before
it can be considered for owner-only use.

## Trader repository study

Cakrawala studies public trading projects to learn architecture and failure modes without copying
strategies or source indiscriminately. Current references include:

- **Nocturna Trading System**: MIT, useful for event-driven state, risk-manager separation, emergency
  stop, and explicit order-state concepts.
- **NautilusTrader**: LGPL-3.0, architecture benchmark for event-driven modularity and adapters.
- **Freqtrade**: GPL-3.0, architecture benchmark for strategy, data, backtest, dry-run, and runtime
  separation.
- **Hummingbot**: Apache-2.0, reference for connector isolation and execution-service boundaries.

GPL and LGPL projects are treated as architecture references in Cakrawala's MIT core unless a future
integration explicitly accepts and documents the corresponding license obligations. See
`docs/trader-repository-study.md` for the detailed reuse policy.

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
| Currency reference context | European Central Bank | Official working-day FX reference-rate history |
| Institutional positioning | CFTC | Public TFF Futures-Only dataset |
| Scheduled U.S. event risk | BLS | Official iCalendar release schedule |
| Policy and central-bank news | Federal Reserve, BIS, ECB | Official feeds |

Source interfaces were rechecked on 21 August 2026. See `docs/sources.md` for endpoint, attribution,
and evidence-policy details.

ECB reference rates are reference information and are not presented as executable FX prices.

## AI Research Council

Cakrawala uses ChatGPT as an external scheduled research layer rather than embedding a paid OpenAI
API call in each web session. A daily task reviews live primary sources from seven separate analyst
roles and writes one validated JSON brief into the repository.

The web application reads `data/ai_briefs/latest.json`. The schema restricts the council to `RISK ON`,
`CAUTIOUS`, `RISK OFF`, `MIXED`, or `INSUFFICIENT EVIDENCE`. It cannot publish BUY, SELL, LONG,
SHORT, target prices, or order instructions. A brief older than 36 hours is marked stale.

This avoids an OpenAI API credential in the web application and avoids per-page OpenAI API usage.
ChatGPT product-plan availability is separate from OpenAI API billing. See
`docs/ai-research-council.md` for the role and security model.

## Evidence before signal

Every external response is untrusted at the network boundary. Cakrawala uses HTTPS-only adapters,
exact host allowlists, bounded timeouts and retries, response-size limits, content-type checks,
provenance hashes, schema validation, and explicit failure handling.

Public providers are isolated. An optional source failure is displayed as unavailable rather than
allowed to crash the terminal or trigger synthetic replacement data.

The terminal distinguishes:

1. **descriptive evidence**, such as price, volatility, crowding, COT, and currency context;
2. **research bias**, which is explainable context and not a trade instruction;
3. **model evidence**, which must pass walk-forward, point-in-time, health, and benchmark gates;
4. **deterministic signal policy**, which is the only layer allowed to return BUY, HOLD, AVOID, or
   NO SIGNAL.

Missing, stale, rejected, or unhealthy evidence cannot be upgraded into a trade by an LLM.

## Metavulus reference boundary

Cakrawala studies useful workflow ideas visible in public trading products, including Metavulus, but
does not copy proprietary research, paid datasets, private signals, scoring logic, trade ideas,
branding, screenshots, or visual assets. Free equivalents are independently implemented from public
or official sources. See `docs/trading-feature-map.md`.

Cakrawala does not fabricate rate-cut probabilities merely to imitate another terminal. Such a panel
should be added only when free futures or OIS inputs, timing, methodology, and freshness can be
reproduced defensibly.

## Bot and architecture research

A weekly research process reviews current open trading bots, execution frameworks, architecture, and
research tools from primary sources. Candidates are classified as observe, sandbox candidate, or
exclude.

The process cannot:

- install a bot automatically;
- copy exchange credentials;
- enable withdrawal access;
- merge an unreviewed dependency change;
- copy GPL or LGPL source into the MIT core automatically;
- bypass model-health, freshness, risk, authorization, or signal-policy gates;
- send a real-money order because a repository or backtest looks promising.

## Repository map

```text
app/                         Dash target and Streamlit fallback entrypoints
configs/                     providers, schedules, models, signals, tool radar
data/ai_briefs/              validated scheduled AI research brief
migrations/                  raw, public, and private PostgreSQL schemas
src/cakrawala/data/          secure provider adapters and provenance
src/cakrawala/intelligence/  news, risk, AI brief, model and readiness policies
src/cakrawala/personal/      owner-only database access
src/cakrawala/web/           framework-neutral public services and Dash auth boundary
src/cakrawala/terminal/      Streamlit fallback presentation
tests/                       regression, runtime, data-boundary, and security tests
docs/                        architecture, source, AI, trader-study, and deployment notes
.github/workflows/           CI and source-health automation
render.yaml                  Render Free deployment blueprint
```

## Local QA

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e '.[dev]'
python -m compileall -q src scripts app
python scripts/check_no_em_dash.py
python -c "from cakrawala.terminal.enhanced_ui import run; assert callable(run)"
python -c "from app.dash_app import server; assert server.test_client().get('/healthz').status_code == 200"
ruff check .
pytest
```

Run Dash locally:

```bash
python app/dash_app.py
```

Run the temporary Streamlit fallback:

```bash
streamlit run app/streamlit_app.py
```

## Public and Personal boundary

Public Mode is anonymous and uses only public research state. Dash Personal Mode remains unavailable
until Google OIDC and a stable owner `sub` are stored server-side. Authorization uses the OIDC `sub`,
not email.

The Dash environment variables are:

```text
GOOGLE_OIDC_CLIENT_ID
GOOGLE_OIDC_CLIENT_SECRET
GOOGLE_OWNER_SUB
WEB_SESSION_SECRET
DATABASE_PERSONAL_URL
```

Private storage uses a separate PostgreSQL connection. Portfolio history, trade plans, journal
entries, and playbook entries remain outside shared public caching. Historical research records are
append-only at the database layer.

## Deployment

The target no-mandatory-cost portfolio deployment uses GitHub, Render Free Web Service, and a
separate persistent free PostgreSQL tier when Personal Mode is enabled. `render.yaml` defines the
public Dash service with Gunicorn, `/healthz`, and deploy-after-checks behavior.

Render becomes the primary portfolio URL only after the deployed Dash build passes the smoke-test
checklist. Until then, Streamlit remains the fallback URL.

See `docs/runbooks/render-deployment.md` for Render setup and `docs/runbooks/deployment.md` for the
existing private-data boundary.

## Limitations

Cakrawala is a research system, not a guarantee of returns. Public APIs can become unavailable,
provider schemas can change, historical relationships can fail, and execution conditions can differ
from research assumptions. The BLS calendar does not cover every global macro event. COT is weekly
evidence, not live institutional flow. The current market breadth is intentionally small and should
not be treated as full cross-asset coverage.

Render's free plan can have cold starts and its local filesystem is not durable storage. Current
free-plan limits should be rechecked before each major deployment.

The AI Research Council is a research summary layer. Scheduled task availability depends on the
user's ChatGPT product plan, and the project does not claim that OpenAI API usage is free.

BMKG attribution must remain visible wherever BMKG data is displayed.

This product uses the FRED API but is not endorsed or certified by the Federal Reserve Bank of St.
Louis.

## License

MIT. See `LICENSE`.
