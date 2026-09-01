# Supabase persistence

LeadRadar writes to Supabase only through the existing FastAPI backend. The Next.js
application continues to use `NEXT_PUBLIC_API_URL` and has no database credentials.

## Apply the schema

Open the Supabase SQL Editor and run the complete migration at
`supabase/migrations/202609010001_create_leadradar_persistence.sql`. It creates:

- `search_sessions`, keyed by the existing runtime `session_id`
- `leads`, keyed by the existing stable, deduplicated `lead_id`

Both tables have Row Level Security enabled. There are deliberately no `anon` or
`authenticated` policies, and their table grants are revoked. The trusted FastAPI
client uses a backend secret key (or the legacy service-role key), which operates as
`service_role` and can upsert the rows.

## Configure local environment files

`apps/web/.env.local` contains only:

```dotenv
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Copy `apps/api/.env.example` to `apps/api/.env`, retain the existing provider
configuration, then set:

```dotenv
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_SECRET_KEY=sb_secret_YOUR_BACKEND_SECRET
```

`SUPABASE_SERVICE_ROLE_KEY` is accepted as a legacy fallback name when
`SUPABASE_SECRET_KEY` is absent. Never put either privileged key in `apps/web`, a
`NEXT_PUBLIC_*` variable, source control, logs, or browser code.

When both Supabase values are blank, persistence is intentionally disabled and the
rest of LeadRadar works normally. Supplying only one value is a configuration error
and stops settings initialization with a clear message.

## Run locally

From the repository root, with the backend virtual environment already created and
its requirements installed:

```bash
npm run dev:api
```

In another terminal:

```bash
npm run dev:web
```

Open `http://localhost:3000` and run a search. FastAPI creates the same bounded
in-memory session used for paging, then upserts the session and every eligible lead.
A lead is eligible for the primary table when it has a stable `lead_id` and at least
one public phone, email, or official website. Enrichment upserts changed leads after
the runtime session has been updated, including leads that only become eligible after
enrichment.

If Supabase is temporarily unavailable, discovery/enrichment still succeeds. The API
logs a safe error without credentials, and session responses include a persistence
warning. This is deliberate graceful-degradation behavior; retrying the search or
enrichment performs the idempotent upsert again.

## Verify in the Supabase SQL Editor

Latest searches:

```sql
select session_id, category, country, region, city, result_count,
       eligible_lead_count, created_at, updated_at
from public.search_sessions
order by created_at desc
limit 20;
```

Latest leads:

```sql
select lead_id, business_name, category, city, phone, email, website,
       enrichment_status, search_session_id, last_seen_at, updated_at
from public.leads
order by last_seen_at desc
limit 50;
```

Lead count:

```sql
select count(*) as lead_count from public.leads;
```

Duplicate count by the stable conflict key (expected `0`):

```sql
select count(*) - count(distinct lead_id) as duplicate_count
from public.leads;
```

Latest enrichment updates:

```sql
select lead_id, business_name, phone, email, website, website_status,
       enrichment_status, enrichment_metadata, updated_at
from public.leads
where enrichment_status <> 'not_started'
order by updated_at desc
limit 50;
```

To verify repeat-search behavior, record `lead_count`, rerun the same search, then run
the count and duplicate queries again. Existing businesses should have a newer
`last_seen_at` instead of a second row with the same `lead_id`.
