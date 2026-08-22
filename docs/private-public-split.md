# Private Vercel and public Streamlit split

Cakrawala uses two presentation surfaces with different jobs.

## Public Streamlit

The Streamlit deployment is the public-facing portfolio and education surface. It exposes evidence, market context, positioning, research, risk tools, and model governance. It does not expose the owner workspace, private journal, private portfolio, or owner-only forex workflow.

Public URL: https://cakrawala-terminal.streamlit.app

The public app must never require owner credentials and must never receive private database credentials.

## Private Vercel

Vercel is the owner research surface. It can combine the public evidence modules with owner-only preparation tools, the Personal Forex Desk, model research status, and private decision-support workflows.

The preferred zero-cost protection is Vercel Authentication on the Hobby plan with the deployment scope set to All Deployments when that option is available for the project. The owner should verify the setting in a private browser window before treating the Vercel URL as private. Application-level Google OIDC remains the stronger boundary for routes that access private stored data.

The Vercel app must stay fail-closed for stored Personal Mode data. No credential, journal record, portfolio record, or personal AI brief belongs in the public repository or a shared public cache.

## Deployment rule

1. Streamlit tracks the public application on `main`.
2. Vercel is treated as a personal research environment and must be protected before private data is enabled.
3. Heavy models do not run in the Vercel request path. They belong in scheduled GitHub Actions, a local sandbox, or another explicitly free research runtime.
4. AI output is decision support. It cannot place orders or override model-health, freshness, authorization, or risk gates.
5. A feature is not promoted because its backtest looks attractive. It must beat a simple benchmark in point-in-time walk-forward evaluation.

## Free-tier constraint

No workflow may silently require a paid add-on. If a provider changes its free tier or starts requesting payment information, Cakrawala should fail visibly and keep the last known safe architecture rather than enabling billing automatically.
