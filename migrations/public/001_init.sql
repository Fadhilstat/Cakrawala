CREATE TABLE IF NOT EXISTS source_health (
    provider TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    checked_at TIMESTAMPTZ NOT NULL,
    detail TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS predictions (
    id BIGSERIAL PRIMARY KEY,
    role TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL,
    target_time TIMESTAMPTZ NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
