CREATE TABLE IF NOT EXISTS portfolio_transactions (
    id BIGSERIAL PRIMARY KEY,
    owner_sub TEXT NOT NULL,
    asset TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
    quantity NUMERIC NOT NULL CHECK (quantity > 0),
    price NUMERIC NOT NULL CHECK (price >= 0),
    executed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION reject_ledger_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'portfolio transaction ledger is append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS portfolio_transactions_immutable ON portfolio_transactions;
CREATE TRIGGER portfolio_transactions_immutable
BEFORE UPDATE OR DELETE ON portfolio_transactions
FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();
