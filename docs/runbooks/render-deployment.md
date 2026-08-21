# Dash and Render Deployment Runbook

Cakrawala is migrating its primary web presentation from Streamlit to Plotly Dash. Streamlit remains
a fallback until the Dash deployment passes live smoke tests. The research, data, model, risk, and
personal-storage layers remain shared so the migration does not create two competing sources of
truth.

## Free MVP target

The portfolio deployment target is a Render Free Web Service created from `render.yaml`.

Current free-tier constraints must be treated as product constraints rather than hidden from users:

- a free web service can spin down after a period without traffic;
- waking a sleeping instance can produce a noticeable cold start;
- the local filesystem is ephemeral and must not be used for personal or durable state;
- free-plan availability and limits can change, so they must be rechecked before every major launch.

For those reasons Cakrawala keeps public evidence stateless, stores scheduled AI briefs in GitHub,
and keeps Personal Mode data in a separate persistent PostgreSQL service.

## Blueprint

The repository includes `render.yaml` with:

- Python runtime
- free plan
- Singapore region
- editable install from the repository
- Gunicorn production server
- `/healthz` health check
- deploy after repository checks pass

The service starts with:

```bash
gunicorn app.dash_app:server --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120
```

`app.run()` remains available only for local development and is not the production start command.

## Public deployment

1. Connect Render to the GitHub repository.
2. Create a Blueprint from `Fadhilstat/Cakrawala`.
3. Keep the service on the free plan for the portfolio MVP.
4. Deploy `main` only after CI is green.
5. Open `/healthz` and confirm it returns HTTP 200 with `status=ok`.
6. Open the root terminal and verify each public workspace independently.
7. Verify a failed provider produces a visible unavailable state rather than synthetic data.
8. Review Render logs for uncaught exceptions and accidental credentials.
9. Keep the existing Streamlit URL available until the Render build passes all smoke tests.

## Personal Mode

Personal Mode remains disabled until all owner settings are configured through Render environment
variables or the hosting secret store. Do not commit these values.

Required identity settings:

- `GOOGLE_OIDC_CLIENT_ID`
- `GOOGLE_OIDC_CLIENT_SECRET`
- `GOOGLE_OWNER_SUB`
- `WEB_SESSION_SECRET`

Required private-data setting:

- `DATABASE_PERSONAL_URL`

The Google web-client redirect URI must point to:

```text
https://<render-service-host>/auth/callback
```

The application authorizes the owner using the stable OIDC `sub`. Email and display name are not
accepted as authorization keys.

`WEB_SESSION_SECRET` should be a high-entropy random value generated outside source control. Session
cookies are configured secure, HTTP-only, and SameSite Lax.

## Database boundary

Do not store private state on the Render service filesystem. Apply personal migrations with a
migration-only database credential, then remove that credential from normal runtime use.

Apply in order:

```text
migrations/personal/001_init.sql
migrations/personal/002_research_workspace.sql
migrations/personal/003_journal_review_fields.sql
```

The normal Dash runtime should receive only a minimum-permission owner-data connection string.

## Live smoke test

A migration is complete only after all of the following pass on the deployed Render service:

1. `/healthz` returns HTTP 200.
2. Overview renders even when an optional source fails.
3. News, Positioning, Market, Macro, AI Council, Risk & Tools, and Tool Radar open without an uncaught
   exception.
4. AI Research Council marks an old brief stale rather than current.
5. Personal Mode remains closed without OIDC configuration.
6. A non-owner authenticated identity is denied after OIDC is configured.
7. No secret appears in the browser, provenance URL, application error, or hosting log.
8. CI and source-health checks remain green after the deployment commit.

Only after this checklist is complete should Render become the primary portfolio URL. Streamlit can
then remain as a temporary fallback until the new deployment has demonstrated stable operation.
