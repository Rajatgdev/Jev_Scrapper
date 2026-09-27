-- Seed the single existing user and their two links (migrated from targets.py).
-- Idempotent: re-running won't duplicate. The email is a placeholder the real
-- account owner replaces (or step B overwrites when signup lands).

INSERT INTO users (email, run_hour, timezone)
VALUES ('owner@sentinel.local', 6, 'Europe/Dublin')
ON CONFLICT (email) DO NOTHING;

INSERT INTO links (user_id, title, url, question)
SELECT u.id, v.title, v.url, v.question
FROM users u
CROSS JOIN (VALUES
    ('Revenue — Customs Prohibitions & Restrictions',
     'https://www.revenue.ie/en/tax-professionals/tdm/customs/prohibitions-restrictions/index.aspx',
     'Is this change about customs rules affecting chemical products?'),
    ('Irish Government News',
     'https://www.gov.ie/en/news/',
     'Is this change about new or amended regulations affecting importers or exporters?')
) AS v(title, url, question)
WHERE u.email = 'owner@sentinel.local'
ON CONFLICT (user_id, url) DO NOTHING;