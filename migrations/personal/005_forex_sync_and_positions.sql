ALTER TABLE forex_deals
ADD COLUMN IF NOT EXISTS fee NUMERIC NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS forex_position_snapshots (
    id BIGSERIAL PRIMARY KEY,
    owner_sub TEXT NOT NULL,
    account_name TEXT NOT NULL,
    ticket TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
    volume NUMERIC NOT NULL CHECK (volume > 0),
    entry_price NUMERIC NOT NULL CHECK (entry_price > 0),
    current_price NUMERIC NOT NULL CHECK (current_price > 0),
    stop_loss NUMERIC CHECK (stop_loss > 0),
    take_profit NUMERIC CHECK (take_profit > 0),
    floating_pnl NUMERIC NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL,
    source TEXT NOT NULL DEFAULT 'mt5_local_bridge',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (owner_sub, account_name, ticket, captured_at)
);

CREATE TABLE IF NOT EXISTS forex_sync_batches (
    id BIGSERIAL PRIMARY KEY,
    owner_sub TEXT NOT NULL,
    account_name TEXT NOT NULL,
    source TEXT NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL,
    snapshot_count INTEGER NOT NULL CHECK (snapshot_count >= 0),
    position_count INTEGER NOT NULL CHECK (position_count >= 0),
    deal_count INTEGER NOT NULL CHECK (deal_count >= 0),
    inserted_position_count INTEGER NOT NULL CHECK (inserted_position_count >= 0),
    inserted_deal_count INTEGER NOT NULL CHECK (inserted_deal_count >= 0),
    payload_hash TEXT NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (owner_sub, payload_hash)
);

CREATE INDEX IF NOT EXISTS idx_forex_positions_owner_captured
    ON forex_position_snapshots (owner_sub, captured_at DESC);

CREATE INDEX IF NOT EXISTS idx_forex_sync_owner_received
    ON forex_sync_batches (owner_sub, received_at DESC);

DROP TRIGGER IF EXISTS forex_positions_immutable ON forex_position_snapshots;
CREATE TRIGGER forex_positions_immutable
BEFORE UPDATE OR DELETE ON forex_position_snapshots
FOR EACH ROW EXECUTE FUNCTION reject_research_history_mutation();

DROP TRIGGER IF EXISTS forex_sync_batches_immutable ON forex_sync_batches;
CREATE TRIGGER forex_sync_batches_immutable
BEFORE UPDATE OR DELETE ON forex_sync_batches
FOR EACH ROW EXECUTE FUNCTION reject_research_history_mutation();
