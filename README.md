# Cakrawala Intelligence Terminal

**Open intelligence for Indonesia and the world**

Cakrawala is an open-data intelligence terminal built to make economic, market, weather, disaster,
and model evidence easier to inspect without hiding uncertainty behind one opaque score. It is a
public information product and an owner research tool, not a dashboard built only for screenshots.

The public application is deployed at `https://cakrawala-terminal.streamlit.app`. Public Mode can
run without private credentials and reads approved public sources directly. Personal Mode remains
owner-only and stays closed until its OIDC and private database settings are configured.

## Public terminal workspaces

The public interface is organized as four working views rather than isolated source cards:

1. **Command Center** summarizes source health, current market movement, market risk, inflation,
   and the latest BMKG earthquake evidence.
2. **Indonesia & Macro** tracks population, GDP growth, and inflation with historical context and
   source provenance.
3. **Market Intelligence** provides 90-day BTC/USDT price history, candlesticks, daily returns,
   trading range, momentum, realized volatility, drawdown, and volume.
4. **Risk & Model Evidence** shows model-promotion readiness, descriptive market risk, policy gates,
   and `NO SIGNAL` whenever model evidence is not sufficient for a deterministic decision.

The terminal intentionally distinguishes descriptive analytics from forecasts. A market statistic
cannot become a recommendation unless the model and signal policy have passed their evidence gates.

## What it answers

1. What changed?
2. How unusual is the change?
3. Which source and model produced the conclusion?
4. How fresh is the evidence?
5. Is the model healthy enough for this task?
6. In owner-only research, what does the versioned rule policy return: BUY, HOLD, AVOID, or NO SIGNAL?

## Trust model

Every external response is untrusted at the network boundary. Cakrawala uses HTTPS-only adapters,
exact host allowlists, bounded timeouts and retries, response-size limits, content-type checks,
provenance hashes, schema validation, and quarantine before data is eligible for analytical use.

Missing, stale, rejected, or unhealthy evidence produces `NO SIGNAL`. The language model may explain
a stored signal but cannot create, upgrade, downgrade, or replace it. Credential-bearing query
parameters are redacted before a source URL is written to provenance metadata.

## Current source universe

| Domain | Provider | Access | MVP role |
| --- | --- | --- | --- |
| Indonesia statistics | BPS WebAPI | API key | Public macro and social data |
| Weather | BMKG | Open JSON | Public weather intelligence |
| Earthquakes | BMKG | Open JSON/XML | Public disaster intelligence |
| Global macro | World Bank Indicators V2 | No key | Cross-country context |
| Rates and macro series | FRED | API key | Curated macro context |
| Crypto market data | Binance market-data-only API | No key | Market features and evaluation |

Source interfaces were rechecked on 21 August 2026. See `docs/sources.md` for the approved endpoints
and attribution requirements.

The public terminal deliberately starts with sources that do not require credentials: BMKG,
World Bank, and Binance public market data. BPS and FRED can be enabled later without blocking the
public portfolio experience.

## Architecture

```text
approved external sources
          |
          v
secure provider adapters
          |
          v
raw bytes + provenance hash
          |
          v
schema and quality gates
     | fail      | pass
     v           v
 quarantine   canonical data
                   |
                   v
          point-in-time features
                   |
                   v
           model promotion gate
                   |
                   v
          versioned predictions
                   |
                   v
         deterministic policy
                   |
                   v
       BUY / HOLD / AVOID / NO SIGNAL
```

## Repository map

```text
app/                         Streamlit terminal
configs/                     providers, schedules, models, signals
migrations/                  raw, public, and personal PostgreSQL schemas
src/cakrawala/data/          secure provider boundary and provenance
src/cakrawala/models/        promotion policy
src/cakrawala/intelligence/  deterministic research signals
src/cakrawala/personal/      owner-only database access
src/cakrawala/terminal/      owner authorization boundary
src/cakrawala/observability/ source health
scripts/                     QA, source checks, deployment preflight
tests/                       regression and security tests
docs/                        architecture, sources, and runbooks
.github/workflows/            CI and source-health automation
```

## Quick start

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

Run the public terminal locally:

```bash
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

Public Mode caches only public-source responses with short TTLs. A manual refresh clears that public
cache. When a source is unavailable, the terminal displays the failure instead of inventing data.

## Public and Personal boundary

Public Mode is anonymous. Personal Mode uses Streamlit's native OIDC flow and remains unavailable
until Google auth settings and a stable owner `sub` are stored in the server-side secret store. An
authenticated account whose `sub` does not match the configured owner is denied.

Owner portfolio reads use a separate PostgreSQL connection and are deliberately not stored in the
shared Streamlit data cache. The transaction ledger is append-only at the database layer. Public and
personal data do not share credentials or cache paths.

A placeholder secret structure is available in `.streamlit/secrets.toml.example`. Real secrets must
never be committed.

## Deployment

The no-mandatory-cost portfolio launch path uses GitHub and Streamlit Community Cloud. Public Mode
can run without a database. Personal Mode can then use a private PostgreSQL service such as Neon's
Free Plan when its current limits fit the project.

Run the public preflight:

```bash
python scripts/preflight_deployment.py --mode public
python scripts/check_sources.py
```

Before enabling Personal Mode, run:

```bash
python scripts/preflight_deployment.py --mode personal
```

Then follow `docs/runbooks/deployment.md` for the OIDC, database, and smoke-test sequence.

## Attribution and limitations

BMKG must be shown as the source wherever BMKG data is displayed.

This product uses the FRED API but is not endorsed or certified by the Federal Reserve Bank of St.
Louis.

Signals are research outputs, not guarantees of returns or individualized financial advice. Model
performance and provider availability can change, so promotion and source-health gates remain part
of the production path.

## License

MIT. See `LICENSE`.
