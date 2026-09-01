-- LeadRadar persistence schema. Apply this file with the Supabase SQL Editor
-- or the Supabase CLI before enabling backend persistence.

create table if not exists public.search_sessions (
    session_id text primary key,
    category text not null,
    country_code text not null,
    country text not null,
    region text,
    city text not null,
    location jsonb not null default '{}'::jsonb,
    requested_limit text not null,
    effective_limit integer not null check (effective_limit > 0),
    providers jsonb not null default '[]'::jsonb,
    warnings jsonb not null default '[]'::jsonb,
    result_count integer not null default 0 check (result_count >= 0),
    eligible_lead_count integer not null default 0 check (eligible_lead_count >= 0),
    expires_at timestamptz not null,
    created_at timestamptz not null,
    updated_at timestamptz not null default now()
);

create table if not exists public.leads (
    lead_id text primary key,
    source_id text not null,
    source_provider text not null,
    sources jsonb not null default '[]'::jsonb,
    source_ids jsonb not null default '{}'::jsonb,
    business_name text not null,
    category text,
    subcategories jsonb not null default '[]'::jsonb,
    country text,
    region text,
    city text,
    address text,
    address_details jsonb not null default '{}'::jsonb,
    latitude double precision,
    longitude double precision,
    phone text,
    phones jsonb not null default '[]'::jsonb,
    normalized_phones jsonb not null default '[]'::jsonb,
    email text,
    emails jsonb not null default '[]'::jsonb,
    website text,
    websites jsonb not null default '[]'::jsonb,
    website_status text not null default 'not_found',
    website_type text not null default 'none',
    directory_links jsonb not null default '[]'::jsonb,
    social_links jsonb not null default '[]'::jsonb,
    whatsapp_number text,
    whatsapp_numbers jsonb not null default '[]'::jsonb,
    opening_hours text,
    rating double precision,
    review_count integer,
    rating_source text,
    confidence double precision,
    field_provenance jsonb not null default '{}'::jsonb,
    enrichment_status text not null default 'not_started',
    enrichment_metadata jsonb not null default '{}'::jsonb,
    source_metadata jsonb not null default '{}'::jsonb,
    lead_score integer not null default 0,
    opportunity_level text not null default 'Low',
    opportunity_reasons jsonb not null default '[]'::jsonb,
    search_session_id text references public.search_sessions(session_id) on delete set null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    last_seen_at timestamptz not null default now()
);

create index if not exists search_sessions_created_at_idx
    on public.search_sessions (created_at desc);
create index if not exists leads_last_seen_at_idx
    on public.leads (last_seen_at desc);
create index if not exists leads_search_session_id_idx
    on public.leads (search_session_id);
create index if not exists leads_location_category_idx
    on public.leads (country, region, city, category);

create or replace function public.set_leadradar_updated_at()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists search_sessions_set_updated_at on public.search_sessions;
create trigger search_sessions_set_updated_at
before update on public.search_sessions
for each row execute function public.set_leadradar_updated_at();

drop trigger if exists leads_set_updated_at on public.leads;
create trigger leads_set_updated_at
before update on public.leads
for each row execute function public.set_leadradar_updated_at();

-- FastAPI is the sole application data-access boundary. Browser roles get no
-- table privileges or policies; the backend secret/service-role key bypasses RLS.
alter table public.search_sessions enable row level security;
alter table public.leads enable row level security;

revoke all on table public.search_sessions from anon, authenticated;
revoke all on table public.leads from anon, authenticated;
grant select, insert, update, delete on table public.search_sessions to service_role;
grant select, insert, update, delete on table public.leads to service_role;

revoke execute on function public.set_leadradar_updated_at() from public;
grant execute on function public.set_leadradar_updated_at() to service_role;
