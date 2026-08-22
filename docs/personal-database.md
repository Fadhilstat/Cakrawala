# Personal Database Provisioning

Cakrawala keeps owner-only records in a separate PostgreSQL database. The application remains usable for public evidence and stateless personal research when the database is absent, but portfolio history, journal records, playbook entries, MT5 snapshots, positions, and imported deals stay unavailable until private storage is provisioned.

The database URL is a server-side secret. It must never be committed, printed, placed in a browser bundle, added to a public notebook, or included in screenshots.

## Zero-cost provider check

The application is provider-agnostic PostgreSQL. For the portfolio and personal-research stage, a provider must have a genuinely usable free option and must not require enabling paid resources.

As of 22 August 2026, Neon remains a suitable candidate because its official material documents a Free Plan, scale-to-zero compute, and PostgreSQL access without requiring a credit card for the free start. Recheck the provider terms before provisioning because free-tier limits can change.

Official references:

- `https://neon.com/blog/new-usage-based-pricing`
- `https://neon.com/blog/how-to-make-the-most-of-neons-free-plan`
- `https://neon.com/`

Supabase also offers a Free Plan with PostgreSQL, but its official pricing page states that inactive free projects can pause. That makes it a valid fallback, but it is less convenient for an owner terminal that may be opened irregularly.

Official reference:

- `https://supabase.com/pricing`

Provider choice does not change Cakrawala's storage boundary. The runtime receives only a PostgreSQL connection URL through `DATABASE_PERSONAL_URL`.

## Connection requirements

Use a dedicated database or schema for the owner-only application. The connection URL should use PostgreSQL and TLS. The migration tool rejects remote URLs that explicitly disable TLS and adds `sslmode=require` when a remote URL omits an SSL mode.

Recommended production connection properties:

```text
postgresql://<runtime-user>:<password>@<host>/<database>?sslmode=require
```

Do not use an administrator or project-owner credential as the long-lived application runtime credential. Create a dedicated runtime role with only the privileges Cakrawala needs after migrations have been applied.

## Migration workflow

Migrations live in `migrations/personal/` and are applied in numeric order. Migration history is recorded in `cakrawala_schema_migrations` with a SHA-256 checksum. If an applied migration file later changes, the migration runner fails instead of silently rewriting history.

The default command is read-only with respect to application migrations:

```bash
export DATABASE_PERSONAL_URL='postgresql://...'
python scripts/manage_personal_db.py --check
```

A check returns exit code `0` when all migrations are applied, `2` when migrations are pending, and `1` for an unsafe or invalid state.

Applying SQL requires an explicit flag:

```bash
python scripts/manage_personal_db.py --apply
```

The runner uses a PostgreSQL advisory lock so two migration processes do not intentionally apply the same migration set at the same time. Each migration and its history record are committed together. A failed migration is rolled back and its checksum is not recorded as applied.

## Current migration set

```text
001_init.sql
002_research_workspace.sql
003_journal_review_fields.sql
004_forex_command_center.sql
005_forex_sync_and_positions.sql
```

These migrations create the append-only owner research ledger, trade plans, journal, playbook, Forex account snapshots, imported deals, synchronized positions, and sync-batch history.

## Provisioning sequence

1. Create a free PostgreSQL project without enabling a paid add-on.
2. Create or obtain a migration credential and a separate least-privilege runtime credential when the provider supports it.
3. Run `python scripts/manage_personal_db.py --check` against the empty database.
4. Run `python scripts/manage_personal_db.py --apply` once the target has been confirmed.
5. Run the check again and require every migration to report `APPLIED`.
6. Store only the runtime connection URL as `DATABASE_PERSONAL_URL` in the private Vercel environment.
7. Exercise owner-only routes and verify private records never appear in public cache, public logs, or the public Streamlit surface.
8. Keep the migration credential outside the application runtime after provisioning.

## Failure policy

Cakrawala does not create synthetic personal records when storage is unavailable. Database connection failures, migration mismatches, missing credentials, or stale private snapshots must remain visible as unavailable or degraded states.

The migration tool also avoids printing the database URL. Connection errors are reported by exception type in the CLI so credentials embedded in provider error messages are not copied into normal terminal output.
