# Cakrawala Intelligence Terminal

**Open intelligence for Indonesia and the world**

Cakrawala is an open-data research terminal for understanding market, macro, positioning, event,
and risk evidence without pretending that one indicator can explain the whole market. It is built
as a public information product and an owner-only research workspace, not as an automatic profit
machine.

**Live Dash app:** `https://cakrawala-intelligence-native.vercel.app`

**Streamlit fallback:** `https://cakrawala-terminal.streamlit.app`

The primary public presentation now runs on Plotly Dash through Vercel's Python runtime. The
production app uses Python 3.12 and a native WSGI entrypoint. Streamlit remains available as a
fallback while the project continues to mature.

## Why this project exists

Market decisions are often made from fragmented information: price action in one tab, macro data in
another, positioning somewhere else, and news without clear context. Cakrawala brings those pieces
into one evidence-first workflow while keeping the limits visible.

The working sequence is:

**context -> plan -> risk gate -> execution readiness -> review -> improve**

Public users can explore the evidence layer without private credentials. Personal Mode is designed
for the owner and stays closed until its own authentication and private storage are configured.

## Public research workspaces

- **Overview**: source health, BTC movement, momentum, realized volatility, futures crowding,
  funding, Indonesia inflation context, and BMKG earthquake evidence.
- **News**: official central-bank and policy headlines with a transparent reading-priority layer.
- **Positioning**: Binance public futures crowding plus CFTC institutional TFF positioning. Crowd
  and institutional horizons remain separate.
- **Market**: BTC market structure, realized risk, and ECB currency-strength context.
- **Macro**: Indonesia macro history plus scheduled BLS event risk.
- **AI Council**: a daily multi-role ChatGPT research brief with confidence, disagreements, risk
  flags, freshness, and source links. It cannot create or replace deterministic trade signals.
- **Risk & Tools**: deterministic position sizing, expectancy, and execution-readiness state.
- **Tool Radar**: primary-source review of actively maintained trading frameworks and architecture.
- **Personal**: owner-only portfolio, plans, journal, and playbook after OIDC and private storage are
  configured.

The Dash navigation deliberately groups related features into a smaller number of workspaces. The
objective is a calmer research terminal, not a long collection of disconnected widgets.

## Architecture

The research and trading logic does not belong to a UI framework. Public data access, intelligence,
risk logic, and owner authorization are kept outside presentation code where possible.

```text
main.py                         native Vercel WSGI bridge
.python-version                 Python 3.12 runtime pin
app/dash_app.py                 primary Dash application
app/assets/terminal.css         responsive terminal presentation
app/streamlit_app.py            fallback Streamlit entrypoint
src/cakrawala/data/             provider adapters and provenance
src/cakrawala/web/              public evidence service, cache, and OIDC boundary
src/cakrawala/intelligence/     research, risk, model, AI brief, and readiness policy
src/cakrawala/personal/         owner-only private storage access
configs/                        providers, models, signals, schedules, and tool radar
data/ai_briefs/                 validated scheduled AI research brief
migrations/                     public and private database migrations
tests/                          regression, runtime, security, and data-boundary tests
.github/workflows/              CI and source-health automation
vercel.json                     Vercel function limits
render.yaml                     optional Render deployment blueprint
```

`src/cakrawala/web/public_service.py` is framework-neutral. Dash uses a small bounded process-local
cache for public evidence. Private owner rows never enter that shared cache.

The Python wheel also contains the Dash app, CSS, provider configuration, and AI brief resource.
CI installs that wheel away from the repository checkout and smoke-tests it from `/tmp`, which helps
catch packaging failures before deployment.

## Deployment model

The production deployment is intentionally simple and has no mandatory paid hosting component for
the portfolio MVP.

```text
GitHub main
   |
   +-- CI
   |    compile
   |    no-em-dash check
   |    Streamlit fallback import
   |    Dash health smoke test
   |    native Vercel WSGI smoke test
   |    deployment wheel validation
   |    Ruff
   |    pytest
   |
   v
Vercel Python 3.12
   |
   +-- main:app
   +-- Plotly Dash
   +-- /healthz
   +-- public evidence providers
```

The current production app has been verified with:

- public root page returning HTTP 200;
- `/healthz` returning HTTP 200 and JSON status `ok`;
- Dash layout endpoint returning HTTP 200;
- Dash dependency endpoint returning HTTP 200;
- bundled terminal CSS returning HTTP 200;
- no clustered runtime errors after the live smoke tests.

The earlier Render path remains in the repository as an optional secondary deployment blueprint.
The connected Render workspace required payment information when a free web service was created
through its API, so Cakrawala did not add a card or create a paid Render resource.

## Free and traceable data path

The public experience is designed around interfaces that do not require a paid subscription for the
current portfolio workflow.

| Evidence | Provider | Public interface |
| --- | --- | --- |
| Indonesia statistics | BPS | WebAPI, optional server-side key |
| Weather and earthquakes | BMKG | Official open JSON |
| Global macro | World Bank | Indicators API V2 |
| Macro series | FRED | Optional server-side API key |
| Spot market structure | Binance | Public market-data API |
| Futures crowding | Binance USD-M Futures | Public positioning, open-interest, and funding endpoints |
| Currency reference context | European Central Bank | Official working-day FX reference-rate history |
| Institutional positioning | CFTC | Public TFF Futures-Only dataset |
| Scheduled U.S. event risk | BLS | Official iCalendar release schedule |
| Policy and central-bank news | Federal Reserve, BIS, ECB | Official feeds |

Every external response is treated as untrusted at the network boundary. Provider adapters use the
controls that fit each source, including HTTPS, host allowlists, bounded timeouts and retries,
response-size limits, content-type checks, schema validation, provenance, and explicit failure
handling.

An unavailable provider is shown as unavailable. The terminal does not create synthetic replacement
data to make a panel look healthy.

ECB reference rates are reference information and are not presented as executable FX prices. COT is
weekly positioning evidence, not live institutional flow.

See `docs/sources.md` for source details and evidence policy.

## Evidence before signal

Cakrawala separates four layers that should not be confused with one another:

1. **Descriptive evidence** such as price, volatility, crowding, COT, and currency context.
2. **Research bias** that summarizes evidence without becoming an order instruction.
3. **Model evidence** that must pass health, point-in-time, and validation gates.
4. **Deterministic signal policy** that is the only layer allowed to return BUY, HOLD, AVOID, or
   NO SIGNAL where that workflow is enabled.

Missing, stale, rejected, or unhealthy evidence cannot be upgraded into a trade by an LLM.

The execution-readiness guard can return:

- `BLOCKED`
- `OBSERVE`
- `PAPER READY`
- `OWNER READY`

`OWNER READY` is not an order. It only means the configured evidence, model, risk, and authorization
gates are satisfied. The public application has no route that sends a real-money trade.

An emergency-stop state overrides every other readiness condition. A future broker or exchange
adapter must pass separate paper-trading, security, credential, audit, and licensing review before
owner-only execution could even be considered.

## AI Research Council

Cakrawala uses ChatGPT as an external scheduled research layer rather than embedding a paid OpenAI
API call in each public page view.

The council separates these roles:

- News Analyst
- Macro Analyst
- Market Analyst
- Risk Analyst
- Quant and Model Steward
- Indonesia Analyst
- Chief Research Editor

The web application reads `data/ai_briefs/latest.json`. The schema restricts the research stance to:

- `RISK ON`
- `CAUTIOUS`
- `RISK OFF`
- `MIXED`
- `INSUFFICIENT EVIDENCE`

The council cannot publish BUY, SELL, LONG, SHORT, target prices, or order instructions. A brief
older than 36 hours is marked stale. Weak verification must become `INSUFFICIENT EVIDENCE` rather
than a guessed conclusion.

This design keeps OpenAI API credentials out of the public web application. ChatGPT product-plan
availability is separate from OpenAI API billing. See `docs/ai-research-council.md` for the full
boundary.

## Trader repository study

Cakrawala studies public trading projects to learn architecture and failure modes without copying
strategies or source indiscriminately.

Current references include:

- **Nocturna Trading System**: MIT. Useful reference for event-driven state, risk-manager separation,
  emergency stop, and explicit order-state concepts.
- **NautilusTrader**: LGPL-3.0. Architecture benchmark for event-driven modularity and adapters.
- **Freqtrade**: GPL-3.0. Architecture benchmark for strategy, data, backtest, dry-run, and runtime
  separation.
- **Hummingbot**: Apache-2.0. Reference for connector isolation and execution-service boundaries.

GPL and LGPL projects are treated as architecture references in Cakrawala's MIT core unless a future
integration explicitly accepts and documents the corresponding license obligations.

A weekly research process reviews maintenance activity, license, security risk, operational risk,
and useful architecture patterns. A project can be classified as observe, sandbox candidate, or
exclude. It cannot install itself into production or override Cakrawala's risk policy.

See `docs/trader-repository-study.md` and `configs/tool_radar.yaml`.

## Metavulus reference boundary

Cakrawala studies useful workflow ideas visible in public trading products, including Metavulus, but
does not copy proprietary research, paid datasets, private signals, scoring logic, trade ideas,
branding, screenshots, or visual assets. Free equivalents are implemented independently from public
or official sources.

Cakrawala also does not fabricate rate-cut probabilities merely to imitate another terminal. Such a
panel should exist only when free futures or OIS inputs, methodology, meeting mapping, and freshness
can be reproduced defensibly.

See `docs/trading-feature-map.md`.

## Public and Personal boundary

Public Mode is anonymous and uses public research state only.

Personal Mode remains fail-closed until all owner-side prerequisites are configured:

```text
GOOGLE_OIDC_CLIENT_ID
GOOGLE_OIDC_CLIENT_SECRET
GOOGLE_OWNER_SUB
WEB_SESSION_SECRET
DATABASE_PERSONAL_URL
```

Authorization uses the stable OIDC `sub`, not an email address. Private storage uses a separate
PostgreSQL connection. Portfolio history, trade plans, journal entries, and playbook entries stay
outside shared public caching. Historical research records are append-only at the database layer.

Personal Mode still requires external provisioning and the personal migrations in order:

```text
migrations/personal/001_init.sql
migrations/personal/002_research_workspace.sql
migrations/personal/003_journal_review_fields.sql
```

No placeholder credential is committed to the repository.

## Local QA

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e '.[dev]'
python -m compileall -q src scripts app api main.py
python scripts/check_no_em_dash.py
python -c "from cakrawala.terminal.enhanced_ui import run; assert callable(run)"
python -c "from main import app; client=app.test_client(); assert client.get('/healthz').status_code == 200"
python -m build --wheel
ruff check .
pytest
```

Run Dash locally:

```bash
python app/dash_app.py
```

Run the Streamlit fallback:

```bash
pip install -e '.[streamlit]'
streamlit run app/streamlit_app.py
```

## Automation

Cakrawala currently uses several guardrailed scheduled workflows:

- daily AI Research Council briefing;
- weekly trading-framework and market-intelligence review;
- repository source-health checks;
- external production-health monitoring every six hours.

The production-health watcher treats the Vercel Dash URL as primary and Streamlit as fallback. It
checks app health, AI-brief freshness, and critical evidence availability, and only alerts on
meaningful problems.

Automation is not allowed to add paid infrastructure, expose secrets, install a trading bot directly
into production, or override deterministic signal and risk policy.

## Limitations

Cakrawala is a research system, not a guarantee of returns. Public APIs can become unavailable,
provider schemas can change, historical relationships can fail, and execution conditions can differ
from research assumptions.

The current public terminal still has practical limitations:

- the BLS calendar does not cover every global macro event;
- COT is weekly evidence;
- the market breadth universe is intentionally small;
- Personal Mode is not production-enabled until owner OIDC and private storage are provisioned;
- there is no automatic real-money order execution;
- AI Council analysis is a research summary layer, not a trading engine;
- free hosting and public-provider limits can change, so they should be rechecked before major
  releases.

BMKG attribution must remain visible wherever BMKG data is displayed.

This product uses the FRED API where configured but is not endorsed or certified by the Federal
Reserve Bank of St. Louis.

## License

MIT. See `LICENSE`.
