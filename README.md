# Cakrawala Intelligence Terminal

**Open intelligence for Indonesia and the world**

Cakrawala is an open-data intelligence terminal built to make economic, market, weather, disaster,
and model evidence easier to inspect without hiding uncertainty behind one opaque score. It is a
public information product and an owner research tool, not a dashboard built only for screenshots.

The normalized MVP source tree is published in this repository. Live production deployment still
requires external database, identity, and hosting credentials, so this README does not claim a live
URL until those services are actually provisioned and smoke-tested.

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
a stored signal but cannot create, upgrade, downgrade, or replace it.

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

## Public and Personal boundary

Public Mode can be anonymous and must use read-only public data access. Personal Mode fails closed
until Google OIDC and private database roles are configured. Authorization is based on the stable
OIDC `sub` value after cryptographic token verification. Email is display metadata, not an
authorization key.

The portfolio transaction ledger is append-only at the database layer. Public and personal data do
not share credentials or caches.

## Deployment

The intended no-mandatory-cost portfolio deployment uses GitHub, Streamlit Community Cloud, and a
free PostgreSQL service when its current limits fit the project. Deployment credentials stay in the
hosting control plane and are never committed. Run:

```bash
python scripts/preflight_deployment.py
```

Then follow `docs/runbooks/deployment.md`.

## Attribution and limitations

BMKG must be shown as the source wherever BMKG data is displayed.

This product uses the FRED API but is not endorsed or certified by the Federal Reserve Bank of St.
Louis.

Signals are research outputs, not guarantees of returns or individualized financial advice. Model
performance and provider availability can change, so promotion and source-health gates remain part
of the production path.

## License

MIT. See `LICENSE`.
