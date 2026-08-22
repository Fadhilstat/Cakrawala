# Private Vercel and public Streamlit split

Cakrawala uses two presentation surfaces with different jobs.

## Public Streamlit

The Streamlit deployment is the public-facing portfolio and education surface. It exposes evidence, market context, positioning, research, risk tools, and model governance. It does not expose the owner workspace, private journal, private portfolio, or owner-only forex workflow.

Public URL: https://cakrawala-terminal.streamlit.app

The public app must never require owner credentials and must never receive private database credentials.

## Personal Vercel

Vercel is the owner research surface. It can combine the public evidence modules with owner-only preparation tools, the Personal Forex Desk, model research status, and private decision-support workflows.

For the zero-cost Hobby path, use a Preview Deployment protected by Vercel Authentication under Standard Protection. Vercel documents this authentication method as available on Hobby. Standard Protection gates previews while leaving the canonical production domain public. Private Production Deployments are part of Advanced Deployment Protection, so Cakrawala does not depend on that paid feature.

The protected preview must be tested in a private browser window before it is treated as personal. Application-level Google OIDC remains a second authorization boundary for owner routes and is still required before stored private data is enabled.

The Vercel app must stay fail-closed for stored Personal Mode data. No credential, journal record, portfolio record, or personal AI brief belongs in the public repository or a shared public cache.

## Deployment rule

1. Streamlit tracks the public application on `main`.
2. The personal Vercel surface uses a protected Preview Deployment on the Hobby plan.
3. The public Vercel production alias is not treated as a private workspace and must never contain unguarded personal data.
4. Google OIDC protects owner routes independently of deployment-level protection.
5. Heavy models do not run in the Vercel request path. They belong in scheduled GitHub Actions, a local sandbox, or another explicitly free research runtime.
6. AI output is decision support. It cannot place orders or override model-health, freshness, authorization, or risk gates.
7. A feature is not promoted because its backtest looks attractive. It must beat a simple benchmark in point-in-time walk-forward evaluation.

## Free-tier constraint

No workflow may silently require a paid add-on. If a provider changes its free tier or starts requesting payment information, Cakrawala should fail visibly and keep the last known safe architecture rather than enabling billing automatically.
