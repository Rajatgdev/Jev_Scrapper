# Sentinel — Multi-User Design (Option C)

This is the blueprint for turning Sentinel from a single-user tool into a product
where anyone signs up, adds their own links, and gets their own emails. It is
design only — no code. Approve or amend this before we build the database (step A)
and auth (step B).

## Decisions locked in

These were chosen deliberately; the schema below follows from them.

- **Scheduling:** per-user. Each user picks the time of day their monitor runs.
- **Cost control:** each user is capped at a fixed number of links (default 10),
  because Firecrawl/OpenAI/Resend costs are ours to bear.
- **Auth:** email + password to start. Schema leaves room to add magic-link or
  OAuth login later without a migration.
- **Link sharing:** every link is private to its owner for now. The schema does
  not prevent two users watching the same URL; it just gives each their own row.
  True shared links (one scrape, many subscribers) is a later optimisation.

## The core idea, unchanged

The pipeline we already proved — scrape - diff - Jev per chunk - gate - one
email — does not change. What changes is the *wrapper* around it: instead of one
global `TARGETS` list and one `DIGEST_TO`, the daily job loops over users, and
for each user runs their links and emails their address. Everything inside
`run_for_url` stays exactly as it is today.

## The data model

Four tables. Names are lowercase; every table has an `id` primary key and
timestamps (`created_at`, and `updated_at` where edits happen).

### 1. `users`

Who can log in.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid / serial | primary key |
| email | text, unique | login identity; also where digests are sent |
| password_hash | text | bcrypt/argon2 hash — never the raw password |
| run_hour | int (0–23) | the hour their monitor runs, in their timezone |
| timezone | text | e.g. "Europe/Dublin"; so 8am means their 8am |
| is_active | bool | lets you disable an account without deleting it |
| created_at | timestamp | |

Notes:
- `password_hash` is the only auth field needed now. Magic links would later add
  a separate `login_tokens` table; OAuth would add `oauth_provider`/`oauth_id`
  columns. Neither disturbs what's here.
- `run_hour` + `timezone` together answer "when does this user's job run." We
  store the hour, not a full cron string, to keep the scheduler simple.

### 2. `links`

The pages a user watches. This replaces `targets.py`.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid / serial | primary key |
| user_id | fk - users.id | owner; cascade-delete with the user |
| title | text | display name |
| url | text | the page to scrape |
| question | text | the per-link relevance question for Jev |
| is_active | bool | pause a link without deleting it |
| created_at | timestamp | |

Notes:
- One user has many links; one link belongs to one user (one-to-many).
- The 10-link cap is enforced in application code on insert ("you've reached your
  link limit"), not as a database constraint — easier to change per-tier later.
- `url` is **not** globally unique — two users may watch the same page. It should
  be unique *per user* (a user can't add the same URL twice): a unique index on
  (user_id, url).
- Firecrawl stores its page snapshots keyed by URL against our API key. If two
  users watch the same URL, Firecrawl still holds one snapshot per URL — which is
  fine for now, but is exactly the seam where "shared links" would later let us
  scrape once and fan out to many subscribers.

### 3. `runs`

One row each time a user's monitor runs. The history/audit trail.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid / serial | primary key |
| user_id | fk - users.id | whose run this was |
| started_at | timestamp | when it began |
| finished_at | timestamp | when it ended (null while running) |
| survivor_count | int | how many changes passed the gate |
| digest | text | the summary text that was emailed |
| status | text | "ok" / "error" / "running" |
| trigger | text | "scheduled" or "manual" (the Run button) |

Notes:
- This is what the Digest page reads to show history, and what proves to a user
  what they were told and when.
- It also lets you show "last run" on the dashboard without re-running.

### 4. `verdicts` (optional in first build)

One row per changed chunk Jev judged, tied to a run. This is the fine-grained
audit trail and the future training data.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid / serial | primary key |
| run_id | fk - runs.id | which run produced it |
| link_id | fk - links.id | which page it came from |
| old_text | text | the paragraph before |
| new_text | text | the paragraph after |
| severity | text | Jev's choice: high/medium/low |
| severity_conf | float | Jev's confidence |
| relevant | float | Jev's relevance Noul |
| is_noise | float | Jev's noise Noul |
| kept | bool | did it pass the gate |

Notes:
- Nice to have, not required for launch. If we skip it at first, `runs.digest`
  still holds the human-readable result. Add this table when you want per-change
  history or want to tune thresholds against real labelled data.

## How the tables relate

```
users (1) ─────< (many) links
  │
  └──────< (many) runs (1) ─────< (many) verdicts >───── (many) links
```

- A user has many links and many runs.
- A run has many verdicts; each verdict points back to the link it came from.
- Delete a user - their links, runs, and verdicts cascade away.

## How a run works, per user

Today `run_daily(TARGETS)` loops a global list. Multi-user changes only the
wrapper:

```
run_for_user(user):
    links = active links where link.user_id == user.id
    open a run row (status "running", trigger "scheduled"|"manual")
    all_survivors = []
    for link in links:
        all_survivors += run_for_url(link.url, link.title, link.question)
        # ^ this function is UNCHANGED from today
    digest = summarise(all_survivors)          # one OpenAI call, skipped if empty
    if all_survivors: send_digest(digest, user.email, count)   # to THEIR email
    close the run row (survivor_count, digest, finished_at, status "ok")
```

Two things moved:
1. The link list comes from the database filtered by `user_id`, not `targets.py`.
2. The digest goes to `user.email`, not a global `DIGEST_TO`.

`run_for_url`, `differ`, `jev`, `summariser`, the gate — all untouched.

## How per-user scheduling works

Each user has `run_hour` + `timezone`. The scheduler wakes every hour and asks:
"which users have `run_hour` equal to the current hour in their timezone?" — then
runs `run_for_user` for each. Options for the scheduler itself (decided at build
time, not now):

- **Railway cron** hitting an internal endpoint every hour that does the "who's
  due this hour?" query. Simplest; fits what we have.
- A background worker/loop in the FastAPI app. More control, more to manage.

Either way the *design* is the same: hourly tick - find due users - run each.
The manual "Run monitor" button just calls `run_for_user(current_user)` on demand
with trigger "manual", bypassing the schedule.

## What changes in the code we already have

Mapping the migration so nothing is a surprise:

- `targets.py` - **deleted.** Its two seed rows become `links` rows (seed script
  or the first user's data).
- `routers/monitor.py` - target CRUD moves to a `links` router scoped to the
  logged-in user; `_targets` in-memory list is gone (the DB is the store now).
- `config.py` thresholds (`severity_conf_min` etc.) - stay global for now. They
  could become per-user columns later, but there's no reason yet.
- `emailer.send_digest` - takes the recipient as an argument instead of reading
  `DIGEST_TO` from config.
- `pipeline.run_daily` - becomes `run_for_user`, as above.
- `db/store.py` - the stub we've carried since day one finally gets implemented,
  against Neon.
- **New:** an auth layer (signup, login, session/token, password hashing) and a
  way every request knows "which user."

## What we build, in order

This design supports the planned sequence:

- **Step A — database.** Stand up Neon. Create the four tables. Implement
  `db/store.py`. Migrate targets - links. Make the existing endpoints read/write
  the DB instead of the in-memory list. Still effectively single-user (no login
  yet) — every link belongs to one seeded user. Proves the DB layer in isolation.
- **Step B — auth.** Add `users`, signup/login, password hashing, sessions, and
  scope every link/run to the logged-in user. Protect the endpoints (this also
  finally closes the public `/api/run` and `/api/targets` that anyone can hit
  today). Then wire per-user scheduling.

Doing A before B means the database is proven working before auth is layered on
top — one new thing at a time, same as every step so far.

## Open questions to settle before/while building

Not blockers for approving this design, but decisions that will come up:

1. **Password reset.** Email+password implies a "forgot password" flow eventually
   (another Resend email). Skip for v1, or build it with auth? (Leaning: skip for
   v1, add soon — it reuses Resend.)
2. **Email verification on signup.** Confirm the address is real before sending
   digests to it? (Leaning: yes, light version — it protects your Resend
   reputation.)
3. **What happens to a user over their link limit if the cap later drops?** Edge
   case; park it.
4. **Timezone capture.** Ask the user, or infer from the browser at signup?
   (Leaning: infer from browser, let them change it.)
5. **Verdicts table now or later?** (Leaning: later — `runs.digest` is enough to
   launch.)

## The one risk worth stating

The public endpoints today (`/api/run`, `/api/targets` CRUD) are unauthenticated.
The moment this is multi-user, that is a real hole — anyone could run anyone's
monitor or read/alter links. **Auth (step B) is what closes it, so B is not
optional polish; it's a security requirement before real users touch this.**
Until B ships, keep the deployed app's URL unshared.