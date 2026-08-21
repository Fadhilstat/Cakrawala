# Deployment Runbook

## Verified target stack

The portfolio launch path was rechecked on 21 August 2026.

- GitHub remains the source of truth for code and deployment history.
- Streamlit Community Cloud remains a free deployment option for Streamlit apps connected to GitHub.
- Neon still offers a Free Plan suitable for a small owner-only PostgreSQL workload when its current limits fit the project.
- Streamlit supports native OpenID Connect authentication, including Google, through `st.login`, `st.user`, and `st.logout`.

Free-tier policies can change. Recheck them before a later migration or scale-up decision.

## Stage 1: public launch

Public Mode does not need database or identity credentials. It reads approved public evidence directly
through the secure provider boundary and fails visibly if a provider is unavailable.

1. Open Streamlit Community Cloud and connect the GitHub repository.
2. Select `main` and `app/streamlit_app.py` as the entrypoint.
3. Select Python 3.12.
4. Do not add secrets just to make Public Mode work.
5. Run `python scripts/preflight_deployment.py --mode public` in a matching environment.
6. Run `python scripts/check_sources.py` from the target environment.
7. Open the deployed URL anonymously and verify BMKG, World Bank, and public market panels.
8. Confirm provider failures display a warning instead of synthetic fallback data.
9. Check the deployment logs before sharing the URL.

The root `requirements.txt` installs the local project with `-e .`, so imports from `src/cakrawala`
are available to the Streamlit entrypoint.

## Stage 2: owner-only Personal Mode

Personal Mode should be enabled only after the public launch is healthy.

1. Create a Google web application for OIDC.
2. Copy `.streamlit/secrets.toml.example` to a private local file or enter equivalent values in the Streamlit secret store.
3. Set the deployed callback to `<streamlit-app-url>/oauth2callback` in both Google and Streamlit settings.
4. Store a strong random cookie secret, Google client ID, and Google client secret only in the secret store.
5. Record the stable Google `sub` value for the owner and store it as `cakrawala.owner_sub`.
6. Provision a private PostgreSQL database and apply `migrations/personal/001_init.sql` with a dedicated migration credential.
7. Create a runtime database role with only the minimum permissions needed by Personal Mode.
8. Store that runtime connection string as `cakrawala.database_personal_url`.
9. Run `python scripts/preflight_deployment.py --mode personal` without printing secret values.
10. Verify the owner can log in and read only the owner ledger.
11. Verify a different authenticated Google account is denied.
12. Verify the ledger remains unavailable if the private database is missing or unreachable.

Private portfolio reads are not stored in `st.cache_data`. Public and private data do not share a
credential or cache path.

## Credentialed data sources

BPS and FRED remain optional for the first public launch because both require API keys. When enabled,
keep `BPS_API_KEY` and `FRED_API_KEY` server-side. FRED query credentials are redacted before source
URLs are written to provenance metadata.

## Final smoke test

Before adding a live URL to the CV or portfolio site, verify all of the following in the deployed
runtime:

- Public Mode opens without authentication.
- Public source attribution is visible where required.
- A failed provider does not create synthetic evidence.
- Personal Mode cannot be opened by a non-owner identity.
- No database URL, client secret, API key, cookie secret, or owner identifier appears in the browser, logs, or repository.
- Restarting or redeploying does not weaken the owner authorization boundary.

A live URL is not considered complete until these checks pass on the deployed instance.
