# Final MVP Release Record

Date: 21 August 2026

## Repository state

The repository root now contains the actual application source tree. Packaging-only release fragments
are no longer the public face of the project. The source includes the Streamlit app, provider
adapters, security boundaries, migrations, tests, deployment runbooks, and GitHub workflows.

## Public Mode

Public Mode is designed to launch without private credentials. Its first live evidence panels use:

- BMKG latest earthquake data
- World Bank Indicators V2 for an explicit reference-year macro value
- Binance's market-data-only Spot API for a public BTC/USDT snapshot

If one provider fails, the panel reports the failure and does not replace it with synthetic data.
Public responses may use short shared caches. Each displayed result retains a source URL and fetch
time.

## Personal Mode

Personal Mode stays closed until server-side OIDC settings and the stable owner `sub` are configured.
A logged-in identity whose `sub` does not match the configured owner is denied.

Owner portfolio reads use a separate PostgreSQL connection. They are not stored in the public
Streamlit data cache. SQL parameters are bound rather than interpolated. The portfolio transaction
ledger is append-only at the database layer.

## Secret handling

Provider credentials belong only in server-side environment or secret stores. FRED's API key is
used in the outbound request but redacted from the URL retained in provenance metadata.

The repository contains only a placeholder `.streamlit/secrets.toml.example`. Real client secrets,
cookie secrets, database URLs, API keys, and owner identifiers must never be committed.

## Source verification

The approved interfaces were rechecked against official pages on 21 August 2026:

- BPS WebAPI: https://webapi.bps.go.id/developer/
- BMKG earthquake JSON: https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json
- BMKG weather documentation: https://data.bmkg.go.id/prakiraan-cuaca/
- World Bank Indicators API V2: https://api.worldbank.org/v2
- FRED series observations: https://api.stlouisfed.org/fred/series/observations
- Binance market-data-only API: https://data-api.binance.vision/api/v3

A documented interface is not treated as trusted merely because it is official. Runtime adapters
still enforce HTTPS, exact host allowlists, bounded retries, timeouts, response-size limits, content
type checks, schema checks, and fail-closed behavior.

## Deployment verification

Streamlit Community Cloud was rechecked as a free GitHub-connected deployment option. Neon was
rechecked as offering a Free Plan for PostgreSQL. Google and Streamlit documentation were rechecked
for the OIDC flow used by Personal Mode.

The repository is deployment-ready, but it does not claim a live Streamlit URL until an external
Streamlit account deploys `main:app/streamlit_app.py` and the deployed instance passes the smoke test
in `docs/runbooks/deployment.md`.

CI and scheduled source-health workflow files are present in the repository. A green workflow run
must be confirmed in GitHub Actions after the final merge rather than inferred from the workflow
files alone.

## Release gate

Code-side MVP readiness requires:

- normalized source tree present on `main`
- no em dash character in Python source
- deterministic signal policy fails closed on missing or stale evidence
- provider credentials remain server-side
- public data failures remain visible
- owner authorization uses stable OIDC subject identity
- private portfolio reads avoid shared cache
- repository documentation does not claim a deployment that has not been observed

External launch readiness additionally requires:

- Streamlit app deployment
- public runtime source-health check
- Google OIDC client provisioning for Personal Mode
- private PostgreSQL provisioning and migration for Personal Mode
- owner and non-owner authentication smoke tests
- final log review for accidental secret exposure
