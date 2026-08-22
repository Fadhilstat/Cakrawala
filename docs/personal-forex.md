# Personal Forex Desk

Personal Forex Desk is an owner-only research workspace for daily G10 foreign-exchange review. It combines official market evidence with a private ChatGPT research workflow while keeping execution manual.

## Access boundary

The Vercel Dash deployment exposes the desk at `/personal/forex` only after the application credential gate verifies a valid personal session. Authorization is checked from the server-side session. The route does not depend on the public cache and does not expose the private portfolio, journal, trade plans, or playbook unless their separate storage is configured.

The login uses a username plus a one-way password hash stored in Vercel environment variables. The plaintext password is not stored in the repository or deployment configuration. If the credential configuration is incomplete, the personal Vercel application fails closed. No fallback identity or public bypass is provided.

## Market evidence

The desk uses sources that are publicly accessible and do not require paid credentials:

- ECB euro foreign-exchange reference rates for EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD, EURJPY, GBPJPY, and EURGBP. These are daily reference rates. They are not executable broker quotes.
- CFTC Traders in Financial Futures for weekly currency positioning. Asset-manager and leveraged-fund net positions are shown with the change from the previous report when available. This is positioning context, not live order flow.
- U.S. Bureau of Labor Statistics official release calendar for near-term U.S. macro event risk.
- Federal Reserve, BIS, and ECB official feeds for macro and central-bank headlines.
- A deterministic Asia, London, and New York session clock based on timezone-aware session definitions.

The 1D, 5D, and 20D changes on the pair board refer to ECB reference-rate observations. Five and twenty observations generally correspond to business-day releases, not five or twenty calendar days.

Every provider remains independently failure-tolerant. Missing evidence is shown as unavailable rather than replaced with synthetic values.

## Private Daily Forex Council

A scheduled ChatGPT task prepares a private brief each morning around 08:00 WIB. It acts through separate research roles:

1. G10 FX Macro Strategist
2. Central Bank and Rates Analyst
3. FX Market and Technical Analyst
4. CFTC Positioning Analyst
5. Event and Catalyst Analyst
6. Risk Manager
7. Chief FX Editor

The council uses current accessible primary sources, separates facts from inference, flags stale or conflicting evidence, and may conclude that the best action is to wait. Pair views are research biases rather than orders or guaranteed predictions.

The scheduled brief stays in the user's private ChatGPT workflow. Cakrawala does not put the personal brief in the public GitHub repository and does not embed an OpenAI API key in the application.

## Trading boundary

Cakrawala does not place forex orders, connect to a broker, or claim that ECB reference prices are tradable quotes. Before any manual trade, the owner should confirm the broker's current price, spread, liquidity, event risk, thesis, invalidation, and risk size.

AI research cannot override model-health, freshness, authorization, or risk controls. No AI role is allowed to promise returns or convert weak evidence into a forced trade.

## Cost boundary

The implemented desk uses public official data without a paid market-data API. The AI council uses a ChatGPT scheduled task rather than an OpenAI API integration, so the Cakrawala application does not create separate OpenAI API usage charges. Platform account limits and terms still apply to the services used.
