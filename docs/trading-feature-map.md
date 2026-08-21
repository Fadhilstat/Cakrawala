# Trading Feature Map

Cakrawala studies useful workflow patterns from public trading terminals, including Metavulus, but
does not copy proprietary research, paid datasets, trade ideas, scoring systems, visual assets, or
private product logic. The implementation below is independently built from free and official data
where practical.

| Trading workflow need | Cakrawala implementation | Evidence or storage |
| --- | --- | --- |
| Realtime news monitor | News & Research search, theme filters, reading-priority score | Federal Reserve, BIS, and ECB official RSS |
| Daily research brief | Overview and Research Desk | Public market, macro, news, session, and positioning evidence |
| Economic calendar | Event Risk | Official BLS iCalendar schedule |
| Currency strength | Market Desk currency-strength view | ECB daily FX reference-rate history |
| Crypto breadth | Market Desk multi-asset breadth | Binance public BTC, ETH, BNB, and SOL daily market data |
| Exposure correlation | 30-day return correlation matrix | Derived from the same public crypto observations |
| Research risk regime | Transparent RISK ON, CAUTIOUS, or RISK OFF desk rule | Breadth and realized volatility, with thresholds shown in the UI |
| Retail/crowd positioning | Crowd Futures | Binance global long-short account ratio, open interest, funding |
| Institutional positioning | Institutional COT | CFTC TFF Futures-Only public dataset |
| Bias board | Transparent research-bias rules | Momentum, drawdown, volatility, crowding, funding, news attention |
| Market sessions | Asia, London, New York session awareness | IANA timezone database via Python `zoneinfo` |
| Market structure | Price, range, returns, momentum, volatility, drawdown | Binance spot price and volume |
| Macro dashboard | Indonesia & Macro | World Bank plus approved BPS/FRED expansion path |
| Risk calculator | Risk & Position Toolkit | Local deterministic calculation, no broker connection |
| Pip or tick calculator | Trader Toolkit | Local user inputs, no broker dependency |
| Position PnL | Trader Toolkit | Local entry, exit, quantity, and direction calculation |
| Compound illustration | Trader Toolkit | Deterministic user-entered assumption, never a return forecast |
| Prop-style risk budget | Trader Toolkit | User-entered daily and total loss limits |
| Equity illustration | Expectancy-based curve | User-entered historical win rate and R statistics |
| Pre-trade checklist | Trader Toolkit plus Execution Readiness | User checklist followed by source, model, freshness, and authorization gates |
| Trade planning | Owner Trade Plans | Private PostgreSQL, owner `sub`, append-only history |
| Journal review | Owner Journal | Result in R, setup, emotion, mistake tag, execution quality, lesson, optional screenshot URL |
| Journal statistics | Owner Journal review metrics | Win rate, average R, execution quality, and recurring mistake counts |
| Playbook | Owner Playbook | Private PostgreSQL, append-only history |
| Trading bot discovery | Bot & Tool Radar | Weekly primary-source research, sandbox-only candidates |

## Before trade

1. Check source health and freshness.
2. Read high-attention official news and upcoming scheduled releases.
3. Compare price structure with crowd futures and institutional positioning.
4. Review currency strength, market breadth, correlation, session, and volatility context.
5. Write a thesis and an explicit invalidation condition.
6. Calculate position size from account risk rather than desired profit.
7. Complete the checklist and continue only if model, policy, freshness, and authorization gates pass.

## During trade

Cakrawala's current portfolio version does not send live orders. The terminal can remain a research
and risk layer while execution stays at the user's chosen broker or exchange. This separation avoids
turning a public portfolio application into a credential-bearing execution service before security,
paper-trading, broker-specific controls, and audit requirements are proven.

The PnL, pip or tick value, and drawdown-budget tools are calculators. They use user-entered contract
and conversion assumptions and do not claim broker-specific precision unless those assumptions are
verified for the instrument being traded.

## After trade

The owner workspace records result in R, setup or playbook name, dominant emotion, primary mistake,
execution quality, notes, lesson, and an optional HTTPS screenshot reference. Historical rows remain
append-only. The review layer summarizes win rate, average R, average execution quality, and recurring
mistakes so improvement is based on batches of trades rather than one outcome.

Playbook entries preserve repeatable setups without rewriting historical journal records. Screenshot
storage itself is not hosted by the public app; Personal Mode stores only the optional URL supplied by
the owner.

## Source interpretation boundaries

ECB foreign-exchange rates are official reference rates for information purposes. They are useful
for relative currency-strength context but are not executable prices. Binance market observations
are public evidence, not a guarantee of the price available at another venue. CFTC positioning is
weekly reporting evidence and is never described as live institutional flow.

## What Cakrawala deliberately does not clone

- proprietary news analysis or paid research text
- proprietary sentiment, conviction, or crowd scores
- paid economic-calendar estimates or consensus data
- private trade ideas or recommendations
- screenshots, branding, layout assets, or exact visual design
- automatic installation of third-party trading bots
- automatic real-money order execution
- fake rate-cut probabilities when a defensible free futures or OIS methodology is unavailable

This keeps the project legally and technically independent while preserving the useful workflow
ideas behind a professional trading research terminal.
