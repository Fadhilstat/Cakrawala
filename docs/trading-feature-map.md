# Trading Feature Map

Cakrawala studies useful workflow patterns from public trading terminals, including Metavulus, but
does not copy proprietary research, paid datasets, trade ideas, scoring systems, visual assets, or
private product logic. The implementation below is independently built from free and official data
where practical.

| Trading workflow need | Cakrawala implementation | Evidence or storage |
| --- | --- | --- |
| Realtime news monitor | News & Research search, theme filters, reading-priority score | Federal Reserve and BIS official RSS |
| Daily research brief | Overview and Research Desk | Public market, macro, news, session, and positioning evidence |
| Economic calendar | Event Risk | Official BLS iCalendar schedule |
| Retail/crowd positioning | Crowd Futures | Binance global long-short account ratio, open interest, funding |
| Institutional positioning | Institutional COT | CFTC TFF Futures-Only public dataset |
| Bias board | Transparent research-bias rules | Momentum, drawdown, volatility, crowding, funding, news attention |
| Market sessions | Asia, London, New York session awareness | IANA timezone database via Python `zoneinfo` |
| Market desk | Market Structure and Research Desk | Binance spot price/volume and derived descriptive analytics |
| Macro dashboard | Indonesia & Macro | World Bank plus approved BPS/FRED expansion path |
| Risk calculator | Risk & Position Toolkit | Local deterministic calculation, no broker connection |
| Equity illustration | Expectancy-based curve | User-entered historical win rate and R statistics |
| Pre-trade checklist | Execution Readiness | Source health, news evidence, model promotion, authorization gates |
| Trade planning | Owner Trade Plans | Private PostgreSQL, owner `sub`, append-only history |
| Journal | Owner Journal | Private PostgreSQL, append-only history |
| Playbook | Owner Playbook | Private PostgreSQL, append-only history |
| Trading bot discovery | Bot & Tool Radar | Weekly primary-source research, sandbox-only candidates |

## Before trade

1. Check source health and freshness.
2. Read high-attention official news and upcoming scheduled releases.
3. Compare price structure with crowd futures and institutional positioning.
4. Review market session and volatility context.
5. Write a thesis and an explicit invalidation condition.
6. Calculate position size from account risk rather than desired profit.
7. Continue only if the model, policy, and authorization gates are valid.

## During trade

Cakrawala's current portfolio version does not send live orders. The terminal can remain a research
and risk layer while execution stays at the user's chosen broker or exchange. This separation avoids
turning a public portfolio application into a credential-bearing execution service before security,
paper-trading, broker-specific controls, and audit requirements are proven.

## After trade

The owner workspace records the result in R, notes what happened, and captures a lesson. Playbook
entries can then preserve repeatable setups without editing past journal history.

## What Cakrawala deliberately does not clone

- proprietary news analysis or paid research text
- proprietary sentiment, conviction, or crowd scores
- paid economic-calendar estimates or consensus data
- private trade ideas or recommendations
- screenshots, branding, layout assets, or exact visual design
- automatic installation of third-party trading bots
- automatic real-money order execution

This keeps the project legally and technically independent while preserving the useful workflow
ideas behind a professional trading research terminal.
