-- Step: per-user API keys. Each user brings their own OpenAI + Firecrawl keys.
-- We store only the Fernet CIPHERTEXT (encrypted in the app), plus a masked
-- last4 for display and version/key_id labels for future key rotation.
-- One row per (user, provider).

CREATE TABLE IF NOT EXISTS user_keys (
    id             BIGSERIAL PRIMARY KEY,
    user_id        BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider       TEXT NOT NULL,                 -- 'openai' | 'firecrawl'
    ciphertext     TEXT NOT NULL,                 -- Fernet-encrypted API key
    crypto_version TEXT NOT NULL DEFAULT 'fernet-v1',
    key_id         TEXT NOT NULL DEFAULT 'v1',    -- which master key encrypted it
    last4          TEXT NOT NULL DEFAULT '',      -- masked display hint only
    status         TEXT NOT NULL DEFAULT 'active',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, provider)
);

CREATE INDEX IF NOT EXISTS idx_user_keys_user ON user_keys(user_id);