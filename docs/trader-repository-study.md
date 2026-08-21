# Trader Repository Architecture Study

This note records architecture patterns studied from public trading repositories. Cakrawala does not
copy strategies, private signals, visual assets, or source code merely because a repository is public.
License, operational risk, and project scope are checked before a pattern is adopted.

## References reviewed on 21 August 2026

### Nocturna Trading System

Repository: `Yog-Sotho/Nocturna-Trading-System`
License: MIT

The repository documents an event-driven trading engine with separate strategy, market-data, order,
and risk managers. Recent public development also introduced an EventBus and OrderStateMachine.
Its documentation includes emergency-stop behavior, state persistence, backtesting, Monte Carlo
analysis, and portfolio risk controls.

Cakrawala adapts only the following ideas:

- explicit readiness states instead of implicit UI state;
- a separate risk gate before any future execution layer;
- an emergency-stop state that overrides every other readiness condition;
- clear separation between research evidence, model evidence, risk, and execution authorization;
- persistent history for owner research records rather than mutable past decisions.

Cakrawala does not adopt Nocturna's autonomous profit claims, broker integration, paid Polygon data,
strategy names, order endpoints, or execution logic.

### NautilusTrader

Repository: `nautechsystems/nautilus_trader`
License: LGPL-3.0

The project is used as an architecture benchmark for event-driven modularity, adapters, explicit
state, and separation between research and runtime concerns. Cakrawala does not copy its source into
the MIT core. Direct future library use would require a separate licensing and integration review.

### Freqtrade

Repository: `freqtrade/freqtrade`
License: GPL-3.0

Freqtrade is useful as a benchmark for separating strategy code, historical data, backtesting,
dry-run operation, live runtime, and model-related workflows. Public commits on 21 August 2026 also
show active work on prediction-history repair and downtime resilience.

Cakrawala uses those ideas as engineering lessons only. GPL source is not copied into the MIT
application.

### Hummingbot

Repository: `hummingbot/hummingbot`
License: Apache-2.0

Hummingbot is useful as a reference for connector isolation, service boundaries, and the operational
complexity of execution infrastructure. Cakrawala keeps all exchange credentials and live order
execution outside the public MVP. Any future connector experiment must start in an isolated paper or
sandbox environment.

## Resulting Cakrawala design

The Dash migration applies these lessons without turning the portfolio project into an autonomous
trading bot:

```text
public sources
    |
    v
validated evidence service
    |
    v
research and model layers
    |
    v
execution readiness guard
    |
    +-- BLOCKED
    +-- OBSERVE
    +-- PAPER READY
    +-- OWNER READY
```

`OWNER READY` is a readiness state, not an order. Cakrawala has no public route that sends a real
trade. If a future execution adapter is ever added, it must have an independent security review,
paper-trading phase, least-privilege credentials, withdrawal disabled, audit logs, and an emergency
stop.

## Reuse policy

1. Study architecture and failure modes first.
2. Confirm repository license before copying any code.
3. Prefer independent implementation for Cakrawala's MIT core.
4. Never import a third-party strategy merely because its backtest looks strong.
5. Treat historical performance, README claims, and screenshots as unverified until independently
   reproduced.
6. New trading repositories enter the weekly radar as observe, sandbox candidate, or exclude.
7. Production dependencies never change automatically from the research radar.
