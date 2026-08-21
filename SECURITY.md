# Security Policy

Cakrawala separates public information from owner-only research data. Secrets never belong in
the repository, browser bundle, notebook output, or application logs.

## Reporting

Please report a suspected vulnerability privately to the repository owner. Do not include live
credentials, personal portfolio records, or sensitive tokens in a public issue.

## Core controls

- HTTPS-only provider access with an explicit host allowlist
- bounded timeouts, retries, and response sizes
- content-type and schema checks before analytical use
- separate public, ingestion, model-write, and personal database roles
- Google OIDC identity matched by the stable `sub` claim, never by email alone
- owner data excluded from shared caches
- deterministic signal policy, with the language model restricted to explanation
