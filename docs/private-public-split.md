# Private Vercel and public Streamlit split

Cakrawala uses two presentation surfaces with different jobs.

## Public Streamlit

The Streamlit deployment is the public-facing portfolio and education surface. It exposes evidence, market context, positioning, research, risk tools, and model governance. It does not expose the owner workspace, private journal, private portfolio, Personal Forex Desk, or AI Decision Lab.

Public URL: https://cakrawala-terminal.streamlit.app

The public app must never require owner credentials and must never receive private database credentials.

## Personal Vercel

Vercel is the owner's private research surface. Its URL is intentionally not distributed through the portfolio, CV, LinkedIn, or public project links.

Access is protected inside the Flask and Dash application with a username and password. The deployment stores only a one-way Werkzeug password hash and a separate high-entropy session secret. The plaintext password is never committed or stored in the deployment environment.

The application gate protects the root page, Dash layout and callback endpoints, assets, Personal Forex Desk, AI Decision Lab, and any future private storage UI. `/healthz` stays open for health monitoring and contains no private research data.

The login form uses CSRF protection, no-store caching, noindex headers, secure and HTTP-only cookies, SameSite protection, and an optional seven-day remembered session. If the authentication variables are incomplete, Vercel fails closed with an unavailable response rather than exposing the terminal.

Required environment variables:

```text
PERSONAL_AUTH_USERNAME
PERSONAL_AUTH_PASSWORD_HASH
WEB_SESSION_SECRET
PERSONAL_OWNER_ID
```

`PERSONAL_OWNER_ID` is optional until private storage is enabled. If omitted, the username is used as the stable owner key.

## Deployment rule

1. Streamlit on `main` is the only public application link.
2. Vercel is for personal research and must require an authenticated application session.
3. The Vercel URL is not advertised publicly even though the login gate remains mandatory.
4. Private database credentials and personal records never belong in Streamlit, GitHub, shared caches, logs, or screenshots.
5. Heavy models do not run in the Vercel request path. They belong in scheduled GitHub Actions or a local research sandbox.
6. AI output is decision support. It cannot place orders or override model-health, freshness, authorization, or risk gates.
7. A model is not promoted because a backtest looks attractive. It must beat a defensible benchmark in point-in-time walk-forward evaluation.

## Password setup

Generate the password hash locally. For example:

```bash
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash(input('Password: ')))"
```

Copy only the generated hash into `PERSONAL_AUTH_PASSWORD_HASH`. Use a long unique password that is not reused for any broker, bank, email, GitHub, or other account.

Generate `WEB_SESSION_SECRET` separately using a cryptographically secure random value. Do not reuse the password or password hash as the session secret.

## Free-tier constraint

No workflow may silently require a paid add-on. Cakrawala uses application-level authentication so personal access does not depend on a paid Vercel protection feature. If Vercel or another provider changes its free tier or starts requiring payment information, Cakrawala should fail visibly and keep the last known safe architecture rather than enabling billing automatically.
