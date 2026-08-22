# Security Policy

Cakrawala separates public information from owner-only research data. Secrets never belong in
the repository, browser bundle, notebook output, or application logs.

## Reporting

Please report a suspected vulnerability privately to the repository owner. Do not include live
credentials, personal portfolio records, password hashes, or sensitive tokens in a public issue.

## Core controls

- HTTPS-only provider access with an explicit host allowlist
- bounded timeouts, retries, and response sizes
- content-type and schema checks before analytical use
- separate public, ingestion, model-write, and personal database roles
- public Streamlit kept separate from the credential-gated personal Vercel application
- personal Vercel password stored only as a Werkzeug-compatible one-way hash
- separate high-entropy session secret stored only in the deployment environment
- CSRF-protected login form with no-store and noindex response headers
- secure, HTTP-only, SameSite session cookies
- fail-closed Vercel behavior when authentication configuration is incomplete
- stable personal owner ID separated from the display username
- owner data excluded from shared caches
- deterministic signal policy, with language models restricted to explanation and research

## Personal credential policy

The personal Vercel deployment requires `PERSONAL_AUTH_USERNAME`,
`PERSONAL_AUTH_PASSWORD_HASH`, and `WEB_SESSION_SECRET`. `PERSONAL_OWNER_ID` is recommended
when private storage is enabled so database ownership stays stable if the login name changes.

Never put the plaintext password in Vercel environment variables, repository files, logs, issue
comments, or screenshots. Generate the password hash locally. Use a unique password that is not
reused for GitHub, email, broker, banking, or any other account.

`/healthz` is intentionally public for deployment monitoring. All application pages, Dash layout
and callback endpoints, assets, and personal research routes require an authenticated session.
