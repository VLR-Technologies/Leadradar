# LeadRadar architecture

LeadRadar 0.2 is an India-first, multi-provider pipeline. Each layer depends on source-neutral models rather than an upstream provider's raw shape.

```text
Next.js dashboard
    |
    | typed JSON / XLSX
    v
FastAPI routes
    |
    +-- BusinessDiscoveryService
    |      +-- LocationResolver
    |      +-- OvertureMapsProvider -- DuckDB/httpfs --> public GeoParquet
    |      +-- OverpassProvider ---------------------> public Overpass
    |      +-- source normalizers
    |      +-- cross-source deduplication/contact merge
    |      +-- LeadOpportunityScorer
    |
    +-- SearchSessionStore
    |      +-- bounded + expiring process memory
    |      +-- server pagination, filters, summary, progress
    |      +-- complete filtered export view
    |
    +-- SupabasePersistenceService
    |      +-- backend-only PostgREST client
    |      +-- search-session upsert
    |      +-- eligible-lead upsert by stable lead_id
    |      +-- post-enrichment updates
    |
    +-- BusinessEnrichmentService
    |      +-- optional SearXNG candidate discovery
    |      +-- WebsiteEnrichmentProvider
    |      +-- verification, contact merge, audit, rescoring
    |
    +-- ExcelExportService --> in-memory .xlsx stream
```

Discovery results are cached in a bounded process-local session for a configurable absolute TTL (default 30 minutes), then expired. The store also evicts oldest sessions to enforce active-session and total-record bounds. API restart loses runtime sessions, but the optional backend-only Supabase layer retains search metadata and eligible lead rows.

## Boundaries

- `app/api/routes` owns HTTP validation, response schemas, safe error mapping, and streaming downloads.
- `app/services` orchestrates providers, deduplicates, enriches, scores, and exports. It does not parse provider payloads.
- `app/providers` owns external communication and provider-specific retry/timeout behavior.
- `app/normalizers` maps Overture/OSM payloads and public contact strings into domain objects.
- `app/models` is the source-neutral domain contract.
- `app/schemas` is the camelCase public API contract.
- `app/core` centralizes settings, the bundled India location index, website classification, and category mappings.
- `app/db` owns database mapping, eligibility enforcement, PostgREST communication, upserts, and safe persistence errors.

## Persistence and failure isolation

The Next.js application still talks only to FastAPI. FastAPI uses `SUPABASE_URL` and a
backend-only secret key to upsert `search_sessions` by `session_id` and `leads` by the
existing deduplicated `lead_id`. Variable lists and provider/enrichment metadata remain
JSONB so the source-neutral model is not flattened or discarded.

The primary `leads` table accepts only normalized records with a stable lead ID and at
least one public phone, email, or official website. Non-contactable candidates remain
available in the runtime session for controlled enrichment. When enrichment establishes
a contact path, the updated record becomes eligible and is upserted.

Persistence deliberately degrades gracefully: provider results and runtime sessions
remain usable if Supabase fails, a safe error is logged, and the session receives a
persistence warning. Database writes are idempotent, so a later retry refreshes the row.
RLS is enabled with no browser policies; `anon` and `authenticated` grants are revoked.

## Discovery providers and failure isolation

`BusinessProvider` requires a name, display name, and async `discover` operation. The service invokes all configured providers concurrently and records provider status (`success`, `timeout`, `failed`, or `skipped`), duration, raw count, deduplicated accepted count, and safe message. Each provider receives one bounded oversampled target; there is no per-result request loop.

Overture is primary. `OVERTURE_RELEASE=latest` resolves the official STAC `latest` value once per process. DuckDB then reads only the Places GeoParquet files and projects only required fields. The SQL filters alternate mapped `categories.primary` values, `bbox.xmin`, `bbox.ymin`, operating status, and result limit; DuckDB/Parquet can push those predicates down rather than downloading the worldwide dataset. The `httpfs` extension is installed into a project-local ignored cache. Queries use reviewed city boxes where present and population-scaled generated search envelopes elsewhere.

OpenStreetMap remains complementary. Overpass uses a resolved country/region/city boundary, central category tags, configurable failover endpoints, bounded timeouts, one policy-aware 429 retry, and no per-business discovery requests. It does not run continuous or massive public extraction.

A failed/skipped provider contributes no rows but does not discard another provider's success. When every provider fails or is skipped, the API returns a typed 502 response. Non-fatal failures are returned as warnings alongside partial results.

## Normalization and provenance

The domain `Business` supports:

- stable `lead_id`, provider `source_id`, all `sources`, and grouped `source_ids`
- primary and alternative phones/emails/websites
- normalized phones for comparison while retaining original public strings
- structured Indian address components and coordinates
- categories/subcategories, operating status, hours, confidence, and social links
- official website type/status, separate directory links, and explicit WhatsApp values
- nullable rating/review fields
- per-field provenance records (`value`, `source`, `confidence`, source page URL, and extraction type)
- enrichment state, website audit, scrape timestamp, score, level, and reasons

Overture, OSM, official website, and search-provider values retain distinct provenance. A provider confidence value is not a customer rating. Ratings remain null because neither configured core provider supplies a legitimate review rating in this implementation.

## Deduplication

Provider IDs alone cannot deduplicate across datasets. The deduplicator builds conservative evidence from:

- Unicode/case/punctuation-normalized business name
- haversine coordinate distance
- normalized phone overlap
- website registrable-domain overlap
- tokenized address/locality similarity
- category and locality context

To avoid an all-pairs comparison at 500+ results, it first blocks candidates by normalized name/address, phone, website domain, and adjacent coordinate buckets. The conservative match predicate then runs only inside candidate blocks.

Exact/near-exact names at very close coordinates can merge without contacts. Strong phone/domain evidence can support a fuzzy name match. Materially separated locations do not merge even when a chain shares a domain, preventing separate branches from collapsing. A merged lead prefers Overture as its base record, unions source IDs and contact arrays deterministically, and retains every field's provenance. The stable lead ID is a hash of the canonical merged identity.

## Enrichment and official-site verification

The browser receives page 1 before automatic enrichment begins. A session enrichment endpoint selects at most 20 leads per call and uses a semaphore (default four). Priority is: phone plus no official site; phone plus official site but no email; then other leads missing useful channels. Terminal outcomes are not retried unless explicitly requested. Results update the same session used by pages and exports.

Priority is existing Overture data, existing OSM data, known website, optional search candidate, then verified website contacts. `SearxngBusinessSearchProvider` queries only a configured self-hosted JSON endpoint and rejects known directory/social/search domains. A result is merely a low-confidence candidate. The website crawler must verify business name plus city or known-contact evidence before extracted contacts can win the merge.

The static crawler inspects the homepage and bounded same-domain contact/about/reach/enquiry/support/location/branch links. It extracts explicit public `tel:`, `mailto:`, visible business contact strings, nested JSON-LD contact fields, explicitly numbered WhatsApp links, social profiles, directory links, and the contact page URL. Ordinary scripts remain ignored. Placeholder, asset, test, tracking, and no-reply email values are rejected; addresses are never synthesized.

## Crawl security and responsible access

Every initial URL and redirect is revalidated. Only HTTP/HTTPS on ports 80/443 is allowed. Credentials, private/loopback/link-local/non-global IPs, `.local`, cross-domain redirects, and known directory/social/booking platforms are blocked. DNS is resolved before access to reduce SSRF risk. Requests have strict timeouts, redirect/page/response-size limits, HTML MIME checks, explicit cleanup, and a descriptive user agent.

The provider reads robots rules and does not bypass access denial, authentication, CAPTCHA, rate limits, or anti-bot measures. Only public business contact information is in scope. HTML is parsed as text; scripts are not executed. Playwright is intentionally not installed or invoked by the core pipeline.

## Website audit and scoring

`WebsiteAudit` stores observations, not vague claims: reachability, HTTPS, redirect behavior, mobile viewport metadata, contact page, email/phone/social presence, title/meta description, and unsuccessful responses.

`score_lead` converts contact availability and audit facts into an internal opportunity score. It rewards callable leads with missing/unreachable/weak digital presence, reduces the score when basic site signals are strong, and caps leads with no contact channel at 35. Thresholds are High ≥70, Medium 40–69, Low <40. Reasons are returned with every score. The score is not business quality, legitimacy, revenue, or customer sentiment.

## API behavior

Discovery:

```text
POST /api/v1/businesses/discover
  -> page 1 + session ID + exact summary/totals + providers + warnings + expiry

GET /api/v1/businesses/search-sessions/{id}?page=&pageSize=&filter=
  -> one filtered page + exact filtered summary/totals
```

Enrichment:

```text
POST /api/v1/businesses/enrich
POST /api/v1/businesses/enrich-batch  (maximum 20)
POST /api/v1/businesses/search-sessions/{id}/enrich  (maximum 20)
  -> verified fields + alternatives + provenance + audit + score
```

Export:

```text
POST /api/v1/businesses/export  (1–500 current leads)
GET /api/v1/businesses/search-sessions/{id}/export?filter=
  -> application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
```

The workbook is created entirely in memory. Text beginning with spreadsheet formula characters is prefixed safely, NULs are removed, and only valid HTTP/HTTPS website values become hyperlinks.

## Frontend state and workflow

The Next.js dashboard is India-first and consumes backend location/category catalogues. City keystrokes query only the local API's bundled GeoNames index through an accessible debounced combobox. After discovery it displays provider raw/accepted counts, source-neutral missing-data language, exact server summary cards, one result page, and bounded enrichment progress. Filters, pagination, and Excel export are server-side. The detail drawer distinguishes official websites, directory/social presence, WhatsApp, contacts, location, audit, opportunity reasons, and source-page provenance.

No database credential, browser profile, cookie, or lead record is stored by the Next.js application. Runtime search-session state stays in bounded API-process memory until expiry/eviction/restart; configured Supabase persistence is written only by FastAPI.

## Known limits

- Generated GeoNames search envelopes are approximate and can under- or over-include the administrative city area.
- “All available” means up to the configured safety cap and available upstream coverage, not a complete census.
- Overture and OSM coverage/contact completeness vary; missing means only absent from current sources.
- Public Overpass and business websites can throttle, time out, change markup, or deny access.
- Static HTML inspection does not cover JavaScript-only contact content.
- SearXNG is optional and must be self-hosted/configured.
- Ratings/reviews remain null without a legitimate source.
- Playwright fallback, scheduled crawling, outreach, and paid/restricted data integrations are intentionally not implemented.
