# Deployment Runbook

## Target stack

The no-mandatory-cost portfolio target is GitHub, Streamlit Community Cloud, and a free PostgreSQL
service such as Neon when its current free plan fits the workload. Confirm provider limits again
before production provisioning because free-tier policies can change.

## Required server-side values

- `DATABASE_PUBLIC_URL`
- `DATABASE_PERSONAL_URL`
- `GOOGLE_OIDC_CLIENT_ID`
- `GOOGLE_OWNER_SUB`
- `BPS_API_KEY` when BPS ingestion is enabled
- `FRED_API_KEY` when FRED ingestion is enabled

Never put these values in repository files or Streamlit client code.

## Order

1. Create separate database roles for raw ingestion, public reads, model writes, and personal data.
2. Apply migrations with a dedicated migration credential, then remove that credential from the
   normal application runtime.
3. Add Streamlit secrets through the hosting control plane.
4. Run `python scripts/preflight_deployment.py`.
5. Run source health checks from the deployed environment.
6. Verify Public Mode anonymously.
7. Verify Personal Mode denies every non-owner identity.
8. Check logs for accidental secrets before sharing the live URL.
