# Personal Forex Desk

Personal Forex Desk is an owner-only research and review workspace for daily G10 foreign-exchange work. It combines official market evidence, private account history, deterministic analytics, and a separate private AI research workflow while keeping broker execution manual.

## Access boundary

The Vercel Dash deployment exposes the desk at `/personal/forex` only after the application credential gate verifies a valid personal session. Authorization is checked from the server-side session. The route uses `no-store` and `noindex` response controls and does not expose private trading records to Public Mode.

The login uses a username plus a one-way password hash stored in Vercel environment variables. The plaintext password is not stored in the repository or deployment configuration. If the credential configuration is incomplete, the personal Vercel application fails closed. No fallback identity or public bypass is provided.

## Forex Command Center

The private desk follows useful patterns from professional trading terminals and open trading journals without copying proprietary branding, scoring logic, or source code.

When private account snapshots and deal history exist, the command center can show:

- current balance, equity, floating P/L, and margin level from the latest private account snapshot
- closed P/L for the current UTC day
- monitored G10 pair health chips backed by the official ECB board
- closed-trade count, win rate, profit factor, expectancy, average R, and closed-deal maximum drawdown
- executed trade history with symbol, side, volume, entry, exit, status, timestamps, and net P/L
- a daily P/L calendar for the current month
- P/L breakdown by symbol
- market-session state, upcoming U.S. macro risk, CFTC positioning, and official central-bank or macro headlines

Empty broker data remains an explicit empty state. The interface never generates sample balances, fictional trades, or synthetic performance numbers to make the dashboard look populated.

## Private storage contract

Migration `migrations/personal/004_forex_command_center.sql` creates owner-scoped account and closed-deal storage. Migration `migrations/personal/005_forex_sync_and_positions.sql` extends the private contract with broker fee support, open-position snapshots, and immutable sync-batch audit records.

The main private records are:

- `forex_account_snapshots` for balance, equity, floating P/L, margin level, capture time, account name, and source
- `forex_position_snapshots` for the latest read-only open-position state, including entry, current price, stop, target, and floating P/L
- `forex_deals` for normalized closed positions, realized P/L, commission, swap, broker fee, and optional R result
- `forex_sync_batches` for idempotency, ingestion counts, payload hashes, and sync audit history

The `(owner_sub, account_name, ticket)` business key prevents duplicate closed-position ingestion. Snapshot tables use owner, account, ticket, and capture-time keys where appropriate. Historical records are append-only so later analytics can be reproduced from the records that were actually ingested.

The web application reads these tables only when `DATABASE_PERSONAL_URL` is configured. Missing private storage does not weaken authentication and does not trigger fabricated fallback data.

## Read-only MT5 sync

MetaTrader 5 remains local. Cakrawala does not install the desktop terminal in Vercel and does not store the broker password in the web application.

The local collector is `scripts/mt5_readonly_sync.py`. It uses only read-oriented MetaTrader 5 Python calls:

- `initialize()` to connect to the already installed local terminal
- `account_info()` for account state
- `positions_get()` for open positions
- `history_deals_get()` for historical deals
- `shutdown()` when collection finishes

The implementation does not call `order_send()` or any other order-placement function.

The collector normalizes simple completed positions before upload. It deliberately skips complex reversal and close-by histories that cannot be reconstructed conservatively from the current normalization rules. Partial closes are accepted only after the total entry and exit volume balances. This is safer than forcing an apparently complete trade from ambiguous broker history.

Official MetaTrader 5 Python documentation used for this integration was confirmed accessible during implementation:

- https://www.mql5.com/en/docs/python_metatrader5
- https://www.mql5.com/en/docs/python_metatrader5/mt5initialize_py
- https://www.mql5.com/en/docs/python_metatrader5/mt5accountinfo_py
- https://www.mql5.com/en/docs/python_metatrader5/mt5positionsget_py
- https://www.mql5.com/en/docs/python_metatrader5/mt5historydealsget_py
- https://pypi.org/project/MetaTrader5/

The documentation and the official PyPI package page were confirmed accessible again on
2026-08-23. The local package is pinned through the `mt5` optional dependency so the
collector build and the local connection test use the same reviewed runtime version.

### Local setup

Install the `MetaTrader5` package only on the Windows machine where the MT5 terminal is
available. It is intentionally not a Vercel runtime dependency.

Create an isolated environment and install the reviewed MT5 dependency:

```text
python -m venv .venv-mt5
.venv-mt5\Scripts\python.exe -m pip install ".[mt5]"
```

Keep the intended broker terminal open and log in inside MetaTrader 5. Cakrawala connects
to that existing terminal session and does not need the broker password. Do not place an
account password in a command, environment variable, project file, screenshot, or support
message.

Set these variables on the collector machine:

```text
CAKRAWALA_FOREX_SYNC_URL=https://<private-vercel-host>/personal/forex/sync
CAKRAWALA_FOREX_SYNC_TOKEN=<long-random-ingest-token>
```

Set the corresponding token only in the private Vercel environment as `PERSONAL_FOREX_INGEST_TOKEN`. The token must never be committed, printed, placed in browser JavaScript, or copied into public notebooks.

A safe first run is:

```text
.venv-mt5\Scripts\python.exe scripts\mt5_readonly_sync.py --dry-run --terminal-path "C:\Program Files\MetaTrader 5\terminal64.exe"
```

The dry run reports only record counts. It does not print the account number, balance,
position details, or deal history, and it does not upload private data. If MT5 reports an
authorization failure, return to the selected terminal, verify the intended account is
logged in, then repeat the dry run.

If the collector reports a connection timeout, open the exact broker terminal selected in
the command. Finish any update, first-run screen, or login dialog and wait until the broker
connection is active before retrying. When several MT5 installations are present, do not
assume the generic terminal and the broker-branded terminal share the same saved session.

After verifying the counts locally, run the collector without `--dry-run` to upload the normalized snapshot.

### Sync endpoint safeguards

`POST /personal/forex/sync` is separate from browser-session authentication because it is intended for the local collector. It is protected by a dedicated bearer token and remains unavailable when the token, owner identity, or private database configuration is missing.

The endpoint also enforces:

- HTTPS on the collector side
- constant-time bearer-token comparison
- JSON-only requests
- a bounded request size
- bounded position and deal counts
- timezone-aware timestamps
- finite numeric values
- duplicate ticket checks inside each payload
- freshness checks for the snapshot timestamp
- payload hashing and idempotent batch detection
- database business keys for duplicate protection
- no database connection string or secret returned to the client

A repeated identical payload is recorded as a duplicate batch rather than creating repeated trading history.

## Market evidence

The desk uses sources that are publicly accessible and do not require paid market-data credentials:

- ECB euro foreign-exchange reference rates for EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD, EURJPY, GBPJPY, and EURGBP. These are daily reference rates, not executable broker quotes.
- CFTC Traders in Financial Futures for weekly currency positioning. Asset-manager and leveraged-fund net positions are shown with the change from the previous report when available. This is positioning context, not live order flow.
- U.S. Bureau of Labor Statistics official release calendar for near-term U.S. macro event risk.
- Federal Reserve, BIS, and ECB official feeds for macro and central-bank headlines.
- A deterministic Asia, London, and New York session clock based on timezone-aware session definitions.

The 1D, 5D, and 20D changes on the pair board refer to ECB reference-rate observations. Five and twenty observations generally correspond to business-day releases, not five or twenty calendar days.

Every provider remains independently failure-tolerant. Missing evidence is shown as unavailable rather than replaced with synthetic values.

## Design research

The command-center design borrows product patterns, not code. The research set includes professional terminals and open-source journals that emphasize account-state visibility, watchlists, trade history, calendar review, execution-quality review, risk statistics, filtering, and multi-account workflows.

Patterns considered useful for Cakrawala include account balance and equity visibility, symbol-level statistics, daily review, behavioral review, playbook adherence, alert-oriented workflows, and a read-only integration boundary before any execution capability.

Features that depend on paid data, broker-specific subscriptions, proprietary analytics, or unsafe credential handling are not part of the zero-cost MVP.

## Private Daily Forex Council

A scheduled ChatGPT task can prepare a private brief each morning. It acts through separate research roles for macro, central banks and rates, technical context, positioning, event risk, risk challenge, and final synthesis.

The council uses current accessible primary sources, separates facts from inference, flags stale or conflicting evidence, and may conclude that the best action is to wait. Pair views are research biases rather than guaranteed predictions.

The scheduled brief stays in the user's private ChatGPT workflow. Cakrawala does not put the personal brief in the public GitHub repository and does not embed an OpenAI API key in the application.

## Model boundary

The Chronos-Bolt FX sandbox remains research-only. Its first recorded walk-forward validation did not beat the configured last-value benchmark across the tested pairs, so it is not promoted into the command center as a production signal.

No AI or forecasting model may override freshness, authorization, data-quality, model-health, or risk controls. A weak model result remains visible as a failed research gate rather than being tuned away or presented as trading edge.

## Trading boundary

Cakrawala does not place forex orders, connect the Vercel request path directly to a trading terminal, or claim that ECB reference prices are tradable quotes. Before any manual trade, the owner should confirm the broker's current bid and ask, spread, liquidity, event risk, thesis, invalidation, and risk size.

## Cost boundary

The implemented market-evidence layer uses public official data without a paid market-data API. The personal Vercel project currently runs on the Vercel Hobby plan. The MT5 collector uses the existing local terminal and standard Python tooling. Private storage or future broker adapters are accepted into the zero-cost MVP only when they have a genuinely free operating path without a mandatory paid upgrade.

