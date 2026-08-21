CREATE TABLE IF NOT EXISTS trade_plans (
    id BIGSERIAL PRIMARY KEY,
    owner_sub TEXT NOT NULL,
    asset TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('LONG', 'SHORT', 'WAIT')),
    entry NUMERIC CHECK (entry > 0),
    stop NUMERIC CHECK (stop > 0),
    target NUMERIC CHECK (target > 0),
    risk_percent NUMERIC NOT NULL CHECK (risk_percent > 0 AND risk_percent <= 10),
    thesis TEXT NOT NULL,
    invalidation TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS trading_journal (
    id BIGSERIAL PRIMARY KEY,
    owner_sub TEXT NOT NULL,
    asset TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('LONG', 'SHORT')),
    result_r NUMERIC NOT NULL,
    notes TEXT NOT NULL,
    lesson TEXT NOT NULL,
    executed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS playbook_entries (
    id BIGSERIAL PRIMARY KEY,
    owner_sub TEXT NOT NULL,
    name TEXT NOT NULL,
    setup TEXT NOT NULL,
    entry_rules TEXT NOT NULL,
    risk_rules TEXT NOT NULL,
    exit_rules TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION reject_research_history_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'research history is append-only; create a new record instead';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trade_plans_immutable ON trade_plans;
CREATE TRIGGER trade_plans_immutable
BEFORE UPDATE OR DELETE ON trade_plans
FOR EACH ROW EXECUTE FUNCTION reject_research_history_mutation();

DROP TRIGGER IF EXISTS trading_journal_immutable ON trading_journal;
CREATE TRIGGER trading_journal_immutable
BEFORE UPDATE OR DELETE ON trading_journal
FOR EACH ROW EXECUTE FUNCTION reject_research_history_mutation();

DROP TRIGGER IF EXISTS playbook_entries_immutable ON playbook_entries;
CREATE TRIGGER playbook_entries_immutable
BEFORE UPDATE OR DELETE ON playbook_entries
FOR EACH ROW EXECUTE FUNCTION reject_research_history_mutation();
