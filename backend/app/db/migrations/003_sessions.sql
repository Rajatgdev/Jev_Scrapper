-- Step B: auth. Sessions table for opaque server-side session tokens.
-- The cookie holds a random token; we store only its SHA-256 digest here, so a
-- database leak doesn't hand out valid sessions. Idle + absolute expiry, and a
-- revoked flag for logout / "log out everywhere".

CREATE TABLE IF NOT EXISTS sessions (
    id                 BIGSERIAL PRIMARY KEY,
    user_id            BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_digest       TEXT NOT NULL UNIQUE,        -- sha256 of the cookie token
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    idle_expires_at    TIMESTAMPTZ NOT NULL,        -- refreshed on use
    absolute_expires_at TIMESTAMPTZ NOT NULL,       -- hard ceiling
    revoked_at         TIMESTAMPTZ                   -- set on logout
);

CREATE INDEX IF NOT EXISTS idx_sessions_digest ON sessions(token_digest);
CREATE INDEX IF NOT EXISTS idx_sessions_user   ON sessions(user_id);