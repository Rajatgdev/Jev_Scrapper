-- Sentinel multi-user schema, step A.
-- Four tables from the multi-user design doc. Still effectively single-user:
-- auth (step B) adds real signup/login; for now one seed user owns the links.

CREATE TABLE IF NOT EXISTS users (
    id            BIGSERIAL PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT,                       -- filled in step B; nullable for the seed user now
    run_hour      INT  NOT NULL DEFAULT 6,    -- hour of day their monitor runs
    timezone      TEXT NOT NULL DEFAULT 'Europe/Dublin',
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS links (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title      TEXT NOT NULL,
    url        TEXT NOT NULL,
    question   TEXT NOT NULL,
    is_active  BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, url)                      -- a user can't add the same URL twice
);

CREATE TABLE IF NOT EXISTS runs (
    id             BIGSERIAL PRIMARY KEY,
    user_id        BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    started_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at    TIMESTAMPTZ,
    survivor_count INT NOT NULL DEFAULT 0,
    digest         TEXT,
    status         TEXT NOT NULL DEFAULT 'running',   -- running | ok | error
    trigger        TEXT NOT NULL DEFAULT 'manual'     -- manual | scheduled
);

CREATE INDEX IF NOT EXISTS idx_links_user  ON links(user_id);
CREATE INDEX IF NOT EXISTS idx_runs_user   ON runs(user_id);