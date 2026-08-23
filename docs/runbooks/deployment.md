# Deployment Runbook

## Current deployment split

Cakrawala uses two separate runtime surfaces.

- Public Mode runs on Streamlit Community Cloud and exposes only portfolio-safe evidence and research views.
- Personal Mode runs as a separate Flask application on Vercel and is protected by the owner credential gate.

This split is intentional. Public Mode must not depend on private credentials, private PostgreSQL, MT5 data, or Personal Mode navigation.

Free-tier policies and provider terms can change. Recheck them before a later migration or scale-up decision.

## Stage 1: public Streamlit

Public Mode should open without private credentials.

1. Deploy `main` with `app/streamlit_app.py` as the entrypoint. A root
   `streamlit_app.py` compatibility entrypoint is also public-only, but the configured path should
   remain explicit in Streamlit Community Cloud.
2. Use the supported Python version from the repository configuration.
3. Run `python scripts/preflight_deployment.py --mode public` in a matching environment.
4. Run `python scripts/check_sources.py` from the target environment.
5. Open every public workspace in a real browser.
6. Confirm source attribution and freshness are visible where required.
7. Confirm provider failures stay visible and are never replaced with synthetic evidence.
8. Confirm no owner portfolio, journal, playbook, Forex Desk, AI Decision Lab, database identifier, or private route is exposed.
9. Review runtime logs before publishing the URL.

## Stage 2: Personal Vercel authentication

The Vercel application uses a server-side Flask session and password hash. Configure these values only in Vercel environment variables:

```text
PERSONAL_AUTH_USERNAME=<owner login name>
PERSONAL_AUTH_PASSWORD_HASH=<Werkzeug password hash>
WEB_SESSION_SECRET=<strong random secret>
PERSONAL_OWNER_ID=<stable private owner identifier>
```

Run:

```text
python scripts/preflight_deployment.py --mode personal
```

The preflight reports only `configured` or `missing`. It never prints secret values.

### Production deployment path

The repository contains `.github/workflows/vercel-production.yml` as the guarded production path for Personal Mode. It targets the existing `cakrawala-intelligence-native` Vercel project and runs after changes reach `main`, or through an explicit workflow dispatch.

The workflow remains harmless until the repository secret `VERCEL_TOKEN` is configured. Create the token in the owner's Vercel account, then store it directly in GitHub Actions secrets. Do not paste it into source code, workflow YAML, issues, pull requests, chat transcripts, screenshots, or logs.

The Vercel team ID and project ID used by the workflow are identifiers rather than credentials. Authentication still requires the private token.

A production deployment performs these checks before it is accepted:

1. the repository no-em-dash check passes;
2. package and project release versions match;
3. Vercel CLI deploys the exact checked-out `main` revision to production;
4. the authenticated Vercel CLI waits until the exact deployment reaches a ready state;
5. the canonical production `/healthz` endpoint responds successfully;
6. the canonical `/releasez` endpoint returns the expected Cakrawala Personal Mode version;
7. release and login responses include the expected private-response security headers;
8. anonymous private routes either redirect to `/login` or fail closed with HTTP 503 when authentication has not been configured.

The exact deployment URL can be protected by Vercel deployment protection. The workflow therefore uses the authenticated Vercel CLI to validate deployment readiness and uses the canonical production URL for application-level HTTP verification. This avoids treating a protected deployment URL as an application failure.

The same application verification can be run manually without credentials:

```text
python scripts/verify_personal_release.py \
  --base-url https://cakrawala-intelligence-native.vercel.app
```

After deployment, verify `/healthz` first. Then open `/releasez` and confirm the returned application version matches the intended release. The release fingerprint contains only service status and version information. It must not contain commit credentials, environment variables, owner identifiers, database information, or provider secrets.

After the release fingerprint is correct, verify anonymously that private routes redirect to `/login`. Then verify owner login, logout, CSRF handling, secure session cookies, remembered-session behavior, `Cache-Control: no-store`, `X-Robots-Tag: noindex, nofollow`, frame protection, referrer policy, permissions policy, and fail-closed behavior when auth configuration is missing.

Private routes currently include:

```text
/personal/forex
/personal/forex/review
/personal/forex/risk
/personal/forex/system
/personal/market
/personal/ai-lab
```

The MT5 sync endpoint is a separate machine-to-machine path and does not use the browser session.

## Stage 3: private PostgreSQL

Provision PostgreSQL only on a genuinely suitable free plan. Do not enable paid resources just to complete the portfolio MVP.

Set only on the private runtime or migration environment:

```text
DATABASE_PERSONAL_URL=<private PostgreSQL URL>
```

Remote database connections must use TLS. The migration helper rejects explicit remote `sslmode=disable` and adds `sslmode=require` when a remote URL does not specify a mode.

Before applying SQL, inspect the plan:

```text
python scripts/manage_personal_db.py --check
```

Then apply the versioned migration set explicitly:

```text
python scripts/manage_personal_db.py --apply
```

Run the check again and confirm every version is `APPLIED`.

For a release where persistent Personal Mode data is required, use:

```text
python scripts/preflight_deployment.py --mode personal --require-storage
```

Use a least-privilege runtime database role where the provider supports it. Migration credentials and runtime credentials should be separate when practical.

## Stage 4: MT5 read-only sync

Configure the ingest token server-side:

```text
PERSONAL_FOREX_INGEST_TOKEN=<strong random token>
```

Require it in preflight with:

```text
python scripts/preflight_deployment.py --mode personal --require-storage --require-mt5
```

The local MT5 collector must remain read-only. It may read account information, positions, and deal history, normalize the records, and send them to the protected HTTPS sync endpoint. It must not call broker order placement methods.

After the first real sync, verify duplicate handling, position freshness, fees, commission, swap, realized and floating P/L, drawdown semantics, stop-loss coverage, margin level, and risk-state behavior against the source account.

## Stage 5: optional private equity intelligence

Twelve Data is restricted to Personal Mode for the current individual-use workflow.

Configure only on the private runtime:

```text
TWELVE_DATA_API_KEY=<private key>
PERSONAL_EQUITY_WATCHLIST=BBCA@XIDX,AAPL@XNAS
```

Require both settings with:

```text
python scripts/preflight_deployment.py --mode personal --require-equity
```

Use `@MIC` when venue disambiguation is needed. Validate each actual symbol and subscription entitlement at request time. Do not publish raw Twelve Data market data in the public Streamlit surface or public repository artifacts.

## Final production gate

A release is not considered complete until the deployed instances pass these checks:

- Public Mode opens without authentication and exposes no Personal Mode navigation.
- `/healthz` responds successfully on the intended build.
- `/releasez` reports the intended application release and exposes no private configuration.
- Every private browser route rejects or redirects anonymous access.
- Owner login and logout work in the deployed runtime.
- Security headers and secure cookie behavior match the application configuration.
- PostgreSQL migrations are fully applied when persistent private features are enabled.
- MT5 sync remains read-only and owner-scoped.
- Twelve Data credentials and licensed raw rows remain private.
- Source failures are visible and never replaced by invented data.
- No database URL, password hash, session secret, API key, ingest token, or owner identifier appears in browser output, repository content, or logs.
- Runtime logs show no unexplained application errors after the complete browser walkthrough.

Only after these checks pass should the final production links and screenshots be used in the CV, LinkedIn, or public portfolio.

