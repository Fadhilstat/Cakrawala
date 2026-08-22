# Final MVP Release Record

Date: 22 August 2026

## Repository state

The repository contains the public application, private owner workspace, secure provider adapters, database migrations, tests, deployment runbooks, and scheduled validation workflows.

Current architecture deliberately separates public portfolio evidence from private decision support.

## Public Mode

Public Mode is intended to launch without private credentials. It uses approved public evidence and fails visibly when a provider is unavailable. No provider failure may be replaced with synthetic observations.

Public verification still requires a complete real-browser walkthrough of the deployed Streamlit application before final portfolio screenshots are accepted.

## Personal Mode

Personal Mode is a separate Flask application intended for the owner only. Browser access is protected with server-side configuration:

```text
PERSONAL_AUTH_USERNAME
PERSONAL_AUTH_PASSWORD_HASH
WEB_SESSION_SECRET
PERSONAL_OWNER_ID
```

Authentication fails closed when required configuration is absent. Private responses use no-store and noindex controls where implemented. The browser session does not authenticate the MT5 machine-to-machine sync endpoint, which uses its own bearer token.

Current private workspaces include the Forex Command Center, Summary Analytics, Risk Command Center, Infrastructure and Test Bed, Daily Market Intelligence, and AI Decision Lab.

## Private storage

Private persistence remains unavailable until a suitable free PostgreSQL project is provisioned and migrations are applied.

The versioned migration set currently covers versions `001` through `005`. The migration runner records checksums, rejects drift and unknown versions, uses a PostgreSQL advisory lock, requires an explicit apply action, and protects remote connections from disabled TLS.

The production release gate requires a post-apply inspection showing every migration as `APPLIED` before persistent private data is treated as ready.

## Market intelligence

Daily decision support can produce `BUY BIAS`, `SELL BIAS`, `WAIT`, or `INSUFFICIENT`. These labels are not broker orders and are not guaranteed-return claims.

Major FX evidence uses the official ECB reference-rate path already integrated in Cakrawala. ECB rates are reference observations, not executable broker quotes.

Optional equity analysis uses Twelve Data only in Personal Mode. The API key remains server-side, raw provider data is not redistributed through the public application, and each symbol and venue must still pass runtime provider validation.

Weekly model review is separate from the daily brief. A weekly rerun or retraining does not automatically promote a model. Failed benchmark or model-health gates remain visible and keep the model research-only.

## MT5 boundary

The local MT5 collector is designed for read-only account, position, and deal retrieval. It does not place broker orders. Real-data production verification still requires a provisioned private database, a server-side ingest token, and a complete reconciliation of imported records against the source account.

## Secret handling

Provider credentials, database URLs, password hashes, session secrets, ingest tokens, and owner identifiers must remain outside the repository, browser output, public notebooks, public caches, and logs.

The project does not treat an official provider as automatically safe. Runtime adapters still use controls such as HTTPS, host allowlists, bounded timeouts and retries, response-size limits, schema validation, content validation, provenance, and fail-closed behavior where applicable.

## Deployment verification

The repository can pass local and CI gates without proving the latest commit is live in production. Production state must be verified separately.

Before final release, confirm:

- the public Streamlit deployment reflects current `main`;
- public navigation exposes no Personal Mode routes or private data;
- the current `main` commit is published to the intended personal Vercel project;
- anonymous private access redirects or fails closed;
- owner login, logout, session behavior, no-store responses, and noindex headers work in production;
- private PostgreSQL is provisioned on a suitable free plan and migrations `001` through `005` are all applied;
- MT5 read-only sync works with real owner data and deduplicates correctly;
- optional equity analysis is enabled only after a valid private Twelve Data key and validated watchlist are available;
- deployment logs contain no unexplained errors or secret material.

## Code quality gate

Code-side readiness requires:

- Python source contains no em dash character;
- Ruff passes without weakened lint rules;
- pytest passes;
- Streamlit import smoke passes;
- Dash and native Vercel WSGI smoke checks pass;
- deployment wheel and installed-wheel smoke checks pass;
- deterministic signal logic fails closed on missing, stale, future-dated, or insufficient evidence;
- security-sensitive values remain server-side;
- public and private data paths remain separated.

## Portfolio release gate

Do not add final production claims, screenshots, or personal deployment links to the CV, LinkedIn, or public portfolio until the real deployed runtimes pass the full browser and security walkthrough.

Unfavorable model results remain part of the project record. Cakrawala should demonstrate disciplined evidence handling and decision support, not hide failed experiments or manufacture certainty.
