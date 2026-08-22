# Personal Forex Desk

Personal Forex Desk is an owner-only research and review workspace for daily G10 foreign-exchange work. It combines official market evidence, private account history, deterministic analytics, and a separate private AI research workflow while keeping broker execution manual.

## Access boundary

The Vercel Dash deployment exposes the desk at `/personal/forex` only after the application credential gate verifies a valid personal session. Authorization is checked from the server-side session. The route uses `no-store` and `noindex` response controls and does not expose private trading records to Public Mode.

The login uses a username plus a one-way password hash stored in Vercel environment variables. The plaintext password is not stored in the repository or deployment configuration. If the credential configuration is incomplete, the personal Vercel application fails closed. No fallback identity or public bypass is provided.

## Forex Command Center

The private desk now follows the useful parts of professional trading terminals and open trading journals without copying their branding, proprietary scoring logic, or source code.

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

Migration `migrations/personal/004_forex_command_center.sql` adds two owner-scoped tables:

- `forex_account_snapshots` for balance, equity, floating P/L, margin level, capture time, account name, and source
- `forex_deals` for broker ticket, account, symbol, side, volume, entry and exit, timestamps, realized P/L, commission, swap, and optional R result

The `(owner_sub, account_name, ticket)` business key prevents duplicate deal ingestion. Account snapshots also have a unique owner, account, and capture-time key. Deal history is append-only after ingestion so later analytics can be reproduced from the original record.

The current web application reads these tables only when `DATABASE_PERSONAL_URL` is configured. Missing private storage does not weaken authentication and does not cause fabricated fallback data.

## MT5 and broker integration boundary

Cakrawala does not put MetaTrader or broker credentials inside Vercel. A direct MetaTrader 5 desktop-terminal dependency is also a poor fit for a Linux serverless request path. The safer design is a separate read-only collector or import workflow that runs where the trading terminal already exists, normalizes account snapshots and deal history, and sends only the required records to private storage through a narrowly scoped authenticated ingestion path.

The first production-safe options are:

1. manual CSV or JSON import for historical records
2. a local read-only collector for personal use
3. a later broker API adapter only when its authentication, licensing, rate limits, and account requirements have been confirmed

No option is allowed to expose a broker password, trading token, or private account data to the browser or public repository.

## Market evidence

The desk uses sources that are publicly accessible and do not require paid market-data credentials:

- ECB euro foreign-exchange reference rates for EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD, EURJPY, GBPJPY, and EURGBP. These are daily reference rates. They are not executable broker quotes.
- CFTC Traders in Financial Futures for weekly currency positioning. Asset-manager and leveraged-fund net positions are shown with the change from the previous report when available. This is positioning context, not live order flow.
- U.S. Bureau of Labor Statistics official release calendar for near-term U.S. macro event risk.
- Federal Reserve, BIS, and ECB official feeds for macro and central-bank headlines.
- A deterministic Asia, London, and New York session clock based on timezone-aware session definitions.

The 1D, 5D, and 20D changes on the pair board refer to ECB reference-rate observations. Five and twenty observations generally correspond to business-day releases, not five or twenty calendar days.

Every provider remains independently failure-tolerant. Missing evidence is shown as unavailable rather than replaced with synthetic values.

## Design research

The command-center design borrows product patterns, not code. The research set includes professional terminals and open-source journals that emphasize account-state visibility, watchlists, trade history, calendar review, execution-quality review, risk statistics, filtering, and multi-account workflows.

Patterns considered useful for Cakrawala include:

- account balance, equity, margin, and unrealized P/L visibility found in professional trade-watch panels
- symbol-level statistics and market context
- P/L calendar and equity-review patterns used by open trading journals
- execution-quality, risk, behavioral, and playbook review
- watchlists and alert-oriented workflows
- paper-first or read-only integration boundaries before any execution capability

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

The implemented market-evidence layer uses public official data without a paid market-data API. The personal Vercel project currently runs on the Vercel Hobby plan. Private storage or broker adapters must be selected separately and are only accepted into the zero-cost MVP when a genuinely free option is available without a mandatory paid upgrade.
