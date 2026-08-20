# Cakrawala Intelligence Terminal

![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
![Streamlit 1.61+](https://img.shields.io/badge/Streamlit-1.61%2B-FF4B4B?logo=streamlit&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-persistent%20storage-4169E1?logo=postgresql&logoColor=white)
![License MIT](https://img.shields.io/badge/License-MIT-2F855A)
![MVP](https://img.shields.io/badge/MVP-deployment%20ready-1F6F5F)

**Open Intelligence for Indonesia and the World**

Cakrawala is an open-data intelligence terminal built to make economic, market, weather, disaster, and model evidence easier to inspect without hiding uncertainty behind a single opaque score. It is designed as a real personal research tool and a public information product, not as a dashboard made only for screenshots.

The MVP codebase is deployment-ready. Actual GitHub publication, persistent credentials, and a live Streamlit URL still require external account provisioning and are deliberately not claimed as complete inside this repository snapshot.

## Project Overview

Cakrawala answers six practical questions:

1. What changed?
2. How unusual is the change?
3. Which data and model produced the conclusion?
4. How fresh is the evidence?
5. Is the model healthy enough to trust for this task?
6. For the owner-only terminal, what does the versioned rule policy say: BUY, HOLD, AVOID, or NO SIGNAL?

Public Mode is anonymous and contains only approved public projections. Personal Mode is owner-only, authenticated with OIDC, and uses separate database credentials for signals, watchlists, and the immutable portfolio transaction ledger.

The language model is not an investment-decision engine. Cakrawala Analyst can explain curated evidence and an existing signal, but it cannot create, upgrade, downgrade, or replace BUY, HOLD, AVOID, REDUCE, EXIT, or NO SIGNAL.

### Current data universe

| Domain | Provider | Access path | MVP use |
| --- | --- | --- | --- |
| Indonesia statistics | BPS WebAPI | Official JSON API, key required | Public macro and social data |
| Weather | BMKG | Official open JSON | Public weather intelligence |
| Earthquakes | BMKG | Official JSON/XML feed | Public disaster intelligence |
| Global macro | World Bank Indicators API v2 | Official API, no key | Cross-country macro context |
| Rates, labor, commodities | FRED | Official API, key required | Curated macro series |
| Crypto market data | Binance Spot public API | Market-data-only host | Public market features and model evaluation |
| Monetary statistics | Bank Indonesia | Discovery-only | Held out until a stable machine interface is approved |

Every external provider is treated as untrusted at the network boundary. A source being official is not enough for automatic model use.

## Architecture & Logic

```text
Official / approved external sources
              |
              v
      Secure provider adapters
      HTTPS, host allowlist, rate limit,
      timeout, retry, response-size guard
              |
              v
       Immutable raw evidence
       payload hash + provenance
              |
              v
     Schema and quality validation
          |             |
          | fail        | pass
          v             v
      Quarantine   Canonical history
                        |
                        v
                 Analytical mart
                 point-in-time rules
                        |
                        v
        +---------------+----------------+
        |               |                |
        v               v                v
   Baselines       Econometrics       ML / DL / TSFM
        |               |                |
        +---------------+----------------+
                        |
                        v
             Champion promotion gate
                        |
                        v
              Versioned predictions
                        |
                        v
             Risk-aware signal policy
                        |
                        v
          BUY / HOLD / AVOID / NO SIGNAL
                        |
                 explanation only
                        v
                Cakrawala Analyst
```

### Data trust boundary

Exact upstream bytes are preserved before provider-specific parsing. Data cannot reach analytical features, model evaluation, production predictions, or personal signals until it passes validation. Suspicious responses remain auditable in quarantine.

### Leakage-safe modeling

Market bars become available only after the bar closes. Feature snapshots are point-in-time. Future labels carry their own availability timestamps. Walk-forward folds purge training examples whose future labels would not have been known at the test boundary.

FRED and World Bank historical macro observations remain blocked from historical model backtests when first-release timing is not strong enough to prove point-in-time availability. A clean-looking date is never treated as proof that information was known on that date.

### Model families

Cakrawala currently evaluates:

- transparent return and volatility baselines
- GARCH, GJR-GARCH, and EGARCH risk models
- LightGBM and XGBoost challengers
- compact N-HiTS-style and PatchTST-style PyTorch challengers
- Chronos-2-small and TimesFM 2.5 zero-shot adapter contracts

Champion selection is role-specific. Expected return, direction probability, and volatility forecasting can have different champions. Promotion requires health, benchmark improvement, fold stability, secondary-metric protection, and operational profiling when a model is resource-heavy.

### Signal policy

Personal signals are deterministic outputs from `configs/signals.yaml` and stored champion predictions. The MVP policy is explicitly marked as a research policy that still requires historical calibration. Missing, stale, rejected, or incomplete evidence produces NO SIGNAL instead of a fabricated neutral forecast.

### Public and Personal security boundary

```text
One Streamlit application
  |
  +-- Public Mode
  |     public read-only PostgreSQL credential
  |     approved views only
  |     shared cache allowed for sanitized public data
  |
  +-- Personal Mode
        Google OIDC
        issuer + audience + stable sub + expiry checks
        private signal read credential
        separate personal PostgreSQL database
        no shared cache for owner data
```

Email is display metadata, not an authorization key. The owner identity is matched through the stable OIDC `sub` claim.

## Repository Map

```text
app/
  streamlit_app.py                 # public and owner terminal
configs/
  providers.yaml                   # source trust registry
  core_universe.yaml               # curated macro and market universe
  features.yaml                    # point-in-time feature rules
  models.yaml                      # evaluation and promotion policy
  signals.yaml                     # transparent decision policy
  schedules.yaml                   # ingestion and evaluation cadence
migrations/
  raw/                             # immutable evidence database
  public/                          # control plane, analytics, models, views
  personal/                        # owner watchlist and transaction ledger
src/cakrawala/
  data/                            # providers, quality, storage, provenance
  analytics/                       # features, snapshots, as-of logic
  models/                          # baselines through champion promotion
  intelligence/                    # public intelligence, signals, analyst
  observability/                   # source and model health
  personal/                        # owner portfolio accounting
  terminal/                        # auth, views, deployment preflight
scripts/                           # ingestion, analytics, evaluation, health checks
tests/                             # regression, leakage, security, storage tests
docs/                              # architecture, sources, QA, deployment, runbooks
.github/workflows/                 # CI, ingestion, models, security analysis
```

## Installation & Quick Start

### 1. Create the environment

Python 3.12 is the deployment target.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev,postgres,models,ml,deep,web]"
```

The heavy foundation-model dependencies are optional:

```bash
pip install -e ".[foundation]"
```

They are not required by the public web process.

### 2. Run quality checks

```bash
PYTHONPATH=src pytest
python -m compileall -q src scripts app
python scripts/check_no_em_dash.py
```

CI additionally runs Ruff and mypy when the repository environment can install them.

### 3. Run a local provider ingestion

```bash
PYTHONPATH=src python scripts/run_ingestion.py bmkg-earthquake
PYTHONPATH=src python scripts/run_ingestion.py binance-core
```

BPS and FRED require their own server-side API keys.

### 4. Build analytical and model layers

```bash
PYTHONPATH=src python scripts/build_analytical_mart.py
PYTHONPATH=src python scripts/evaluate_baselines.py
PYTHONPATH=src python scripts/evaluate_econometrics.py
PYTHONPATH=src python scripts/evaluate_ml.py
PYTHONPATH=src python scripts/assess_model_promotions.py
PYTHONPATH=src python scripts/run_champion_inference.py
PYTHONPATH=src python scripts/run_signal_policy.py
```

Local mode is intended for development and regression testing. Production schedules use PostgreSQL roles separated by purpose.

### 5. Run the terminal

Install the lightweight web requirements and start Streamlit:

```bash
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

Without production read credentials, the terminal fails closed and explains that live data is not configured. It does not substitute synthetic market data.

## Production Deployment

The current no-mandatory-cost MVP target is:

- GitHub repository and GitHub Actions
- Streamlit Community Cloud
- Neon PostgreSQL Free
- Google OIDC for owner authentication

Run the redacted deployment preflight before launch:

```bash
PYTHONPATH=src python scripts/preflight_deployment.py
```

Then follow `docs/runbooks/deployment.md` and `docs/deployment/neon-free-setup.md`.

Migration credentials are never placed in scheduled workflows. Public web reads, private signal reads, personal writes, ingestion, analytics, model writes, and migration DDL all use separate scopes.

## Verification Philosophy

A phase is not marked healthy because a notebook produced a plausible chart. Cakrawala checks syntax, schema, point-in-time availability, idempotency, model health, storage isolation, workflow permissions, source provenance, and security boundaries. Failed checks are reported as failures or environment limitations, not silently converted into PASS.

The repository also includes:

- `SECURITY.md`
- `docs/runbooks/incident-response.md`
- `docs/runbooks/backup-restore.md`
- detailed phase QA records in `docs/qa/`

## Public Value

The public terminal is meant to help students, researchers, journalists, analysts, and curious citizens answer a basic but important question: what is happening, and how strong is the evidence?

The personal terminal adds owner-only market research and portfolio context without turning a statistical forecast into a promise of investment returns.

## Limitations

- The snapshot does not claim a live production URL until external infrastructure and credentials are actually provisioned.
- FRED and World Bank macro series are not used for historical backtests when true release timing cannot be established.
- Foundation-model production inference remains gated by real runtime profiling.
- Signal thresholds are an auditable MVP research policy and still require historical calibration before they should influence real capital decisions.
- Market predictions and risk levels are uncertain estimates, not guarantees.

## License

MIT. See `LICENSE`.
