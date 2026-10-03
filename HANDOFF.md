# Cakrawala Handoff

Updated: 3 October 2026

## Current working state

- Repository: `https://github.com/fadhilstat/cakrawala.git`
- Branch: `codex/corporate-terminal-ui`
- Base commit: `a62361e`
- Public runtime: Streamlit Community Cloud
- Public URL: `https://cakrawala-terminal.streamlit.app`
- Private runtime: Vercel deployment described in the deployment runbook
- Broker boundary: MT5 remains read-only and no order function is part of this milestone

The public deployment was reachable after a cold-start wake-up. The pre-change mobile audit
showed an expanded sidebar covering the content. The live snapshot reported four of nine public
sources available. Source degradation was visible and was not converted into a healthy state.

## Completed in this milestone

- Added a reusable public terminal design system in `app/assets/public_terminal.css`.
- Rebuilt the public header and workspace hierarchy for faster scanning.
- Grouped workspace labels without changing the underlying feature routes.
- Added an operational status strip with source availability, snapshot time, and safety boundary.
- Added a detailed system diagnostics panel that keeps source failures visible.
- Changed the default sidebar state to collapsed so mobile content is not blocked on load.
- Cached complete public snapshots for five minutes so workspace changes do not retry failed sources.
- Added responsive, keyboard-focus, and reduced-motion rules.
- Preserved the public-only application boundary and the no-order safety boundary.

## Known issues and risks

- Streamlit Community Cloud can sleep after inactivity, so continuous availability is not guaranteed.
- Several public providers can fail or respond slowly. The UI degrades visibly, but source reliability
  still needs separate provider-level work.
- The project mirror in `Cakrawala/Cakrawala-main` contains local data and MT5 changes that are not
  identical to GitHub `main`. It was intentionally left untouched and must be reconciled separately.
- The private Dash interface has not yet received the same visual design system.

## Runtime and resource notes

The milestone adds one static CSS asset and small HTML status components. It adds no service,
database, worker, container, model, or background process. Expected idle CPU and RAM impact is
negligible. The stylesheet is packaged with the existing `app` package.

## NEXT_ACTION

Audit the private Dash interface at desktop and mobile breakpoints, then apply the same design tokens
to `app/assets/terminal.css` without changing the authentication, private-data, or MT5 boundaries.
