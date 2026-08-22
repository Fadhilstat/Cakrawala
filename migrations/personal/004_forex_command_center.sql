CREATE TABLE IF NOT EXISTS forex_account_snapshots (
    id BIGSERIAL PRIMARY KEY,
    owner_sub TEXT NOT NULL,
    account_name TEXT NOT NULL,
    balance NUMERIC NOT NULL,
    equity NUMERIC NOT NULL,
    floating_pnl NUMERIC NOT NULL,
    margin_level_percent NUMERIC,
    captured_at TIMESTAMPTZ NOT NULL,
    source TEXT NOT NULL DEFAULT 'manual_or_bridge',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (owner_sub, account_name, captured_at)
);

CREATE TABLE IF NOT EXISTS forex_deals (
    id BIGSERIAL PRIMARY KEY,
    owner_sub TEXT NOT NULL,
    ticket TEXT NOT NULL,
    account_name TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
    volume NUMERIC NOT NULL CHECK (volume > 0),
    entry_price NUMERIC NOT NULL CHECK (entry_price > 0),
    exit_price NUMERIC CHECK (exit_price > 0),
    opened_at TIMESTAMPTZ NOT NULL,
    closed_at TIMESTAMPTZ,
    realized_pnl NUMERIC NOT NULL DEFAULT 0,
    commission NUMERIC NOT NULL DEFAULT 0,
    swap NUMERIC NOT NULL DEFAULT 0,
    result_r NUMERIC,
    source TEXT NOT NULL DEFAULT 'manual_or_bridge',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (owner_sub, account_name, ticket),
    CHECK (closed_at IS NULL OR closed_at >= opened_at)
);

CREATE INDEX IF NOT EXISTS idx_forex_deals_owner_closed
    ON forex_deals (owner_sub, closed_at DESC);

CREATE INDEX IF NOT EXISTS idx_forex_snapshots_owner_captured
    ON forex_account_snapshots (owner_sub, captured_at DESC);

DROP TRIGGER IF EXISTS forex_deals_immutable ON forex_deals;
CREATE TRIGGER forex_deals_immutable
BEFORE UPDATE OR DELETE ON forex_deals
FOR EACH ROW EXECUTE FUNCTION reject_research_history_mutation();
