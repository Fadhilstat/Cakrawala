# Personal Forex Risk and System Workspaces

The owner-only forex workspace now separates four jobs that should not be mixed into one crowded screen:

- `/personal/forex` for current trading context and synchronized account history
- `/personal/forex/review` for post-trade analytics
- `/personal/forex/risk` for deterministic personal risk review
- `/personal/forex/system` for infrastructure health and operating setup

## Risk review

The risk page evaluates the latest synchronized private account state against the non-secret policy in `configs/personal_forex.yaml`.

The initial policy checks daily closed P/L, current floating P/L, closed-deal drawdown, margin level, open-position count, missing stop losses, and snapshot freshness. Daily closed P/L uses the configured workspace timezone, which is `Asia/Jakarta` by default.

The output is one of `NO DATA`, `SAFE`, `CAUTION`, or `LOCKED`. This state is a review gate for the owner. It does not send an order, cancel an order, modify a stop, or prevent the broker terminal from accepting an order.

The closed-deal drawdown ratio is intentionally described as an imported-history measure. It is not presented as a complete broker equity drawdown because the private database does not yet contain every historical intratrade equity observation.

## Infrastructure and setup

The system page checks the current accessibility of the official ECB FX reference-rate provider, BLS release calendar, a representative CFTC TFF currency report, and official macro feeds. A source failure is reported as degraded rather than replaced with synthetic content.

Private infrastructure checks show only configuration state. Secret values are never rendered. The page can report whether owner authentication, the private database, the dedicated MT5 ingest token, and the stable owner ID are configured. When private storage is available, it also reports the age of the latest account snapshot.

The same workspace displays monitored pairs, integration boundaries, and risk policy from `configs/personal_forex.yaml`. This file contains operating policy only and must not contain credentials.

## Default operating policy

The default policy is intentionally conservative for an early personal research terminal. It is a starting point for disciplined review rather than a claim that these thresholds are universally optimal.

Current defaults include:

- 1 percent maximum planned risk per trade
- 3 percent daily closed-loss review limit
- 2 percent floating-loss review limit
- 8 percent imported closed-deal drawdown review limit
- 150 percent minimum margin-level review threshold
- five simultaneous open positions
- zero open positions without a stop loss
- a 15 minute private account snapshot freshness threshold

Changes to these limits should be made deliberately in the repository, reviewed, tested, and merged rather than adjusted impulsively during a live trading session.
