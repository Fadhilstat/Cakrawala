CREATE TABLE IF NOT EXISTS raw_payloads (
    id BIGSERIAL PRIMARY KEY,
    provider TEXT NOT NULL,
    source_url TEXT NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    sha256 CHAR(64) NOT NULL UNIQUE,
    payload BYTEA NOT NULL
);

CREATE TABLE IF NOT EXISTS quarantine_payloads (
    id BIGSERIAL PRIMARY KEY,
    provider TEXT NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    reason TEXT NOT NULL,
    sha256 CHAR(64) NOT NULL,
    payload BYTEA NOT NULL
);
