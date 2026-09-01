# LeadRadar

LeadRadar is VLR Technologies' internal, India-first lead-discovery application. It combines real public business listings from Overture Maps Places and OpenStreetMap, preserves source provenance, safely inspects known official websites, highlights digital-service opportunities, persists eligible leads through FastAPI to Supabase, and exports complete filtered search sessions to Excel.

The discovery workflow uses free/open providers. Bounded, expiring in-memory API sessions remain the fast paging layer; optional Supabase persistence stores search metadata and eligible leads without exposing database credentials to the browser.

## How it works

```text
India search request
        |
        v
GeoNames-backed local autocomplete -> LocationResolver
(canonical city/state + reviewed box or generated search envelope)
        |
        v
BusinessDiscoveryService
   |                    |
   +-- Overture Maps    +-- OpenStreetMap / Overpass
       (primary)            (secondary)
        |                    |
        +--------+-----------+
                 v
 normalization -> conservative cross-source deduplication
                 v
 provenance-aware contact merge -> opportunity score
                 v
 bounded in-memory search session
                 v
 backend-only Supabase upsert + server pagination/filter/export
                 v
 controlled enrichment updates + detail drawer / Excel download
```

Provider failures are isolated. For example, an Overpass timeout is reported in `warnings` while valid Overture results remain usable. A discovery request fails only when no configured provider returns a usable response.

See [docs/architecture.md](docs/architecture.md) for provider, session, deduplication, enrichment, security, and scoring details, and [docs/data-sources.md](docs/data-sources.md) for licenses and attribution.

## Requirements

- Node.js 20+
- npm 10+
- Python 3.11+
- Internet access to the Overture public S3/STAC endpoints, public Overpass, and any official websites being inspected

DuckDB downloads its free `httpfs` extension on the first Overture query and caches it under `apps/api/.duckdb/extensions`. The directory is ignored by Git.

## Setup

### Backend — Windows PowerShell

```powershell
cd apps/api
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload
```

### Backend — macOS/Linux

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
cp .env.example .env
python -m uvicorn app.main:app --reload
```

The API is available at [http://localhost:8000](http://localhost:8000), with OpenAPI documentation at [http://localhost:8000/docs](http://localhost:8000/docs).

### Frontend

In a second terminal from the repository root:

```bash
npm install
```

Copy `apps/web/.env.example` to `apps/web/.env.local`, then run:

```bash
npm run dev:web
```

Open [http://localhost:3000](http://localhost:3000).

## Environment variables

Backend variables are documented in `apps/api/.env.example`:

- `OVERTURE_ENABLED`: enable the primary Overture provider; defaults to `true`.
- `OVERTURE_RELEASE`: `latest` or a pinned release such as `2026-07-22.0`.
- `OVERTURE_STAC_URL`: official STAC catalogue used to resolve `latest`.
- `OVERTURE_TIMEOUT_SECONDS`: total release/query timeout, 10–120 seconds.
- `OVERTURE_DUCKDB_EXTENSION_DIRECTORY`: project-local DuckDB extension cache.
- `OVERPASS_API_URL`: backward-compatible primary Overpass endpoint.
- `OVERPASS_API_URLS`: comma-separated failover endpoints, attempted sequentially with bounded retries.
- `OVERPASS_TIMEOUT_SECONDS`: timeout for each Overpass request, 5–120 seconds.
- `ENRICHMENT_HTTP_TIMEOUT_SECONDS`: official-site request timeout, 2–30 seconds.
- `ENRICHMENT_MAX_PAGES`: same-domain pages inspected per website, 1–5.
- `ENRICHMENT_BATCH_LIMIT`: businesses in one enrichment batch, 1–20.
- `ENRICHMENT_MAX_CONCURRENCY`: simultaneous website inspections, 1–5.
- `DISCOVERY_MAX_LIMIT`: safety cap used by **All available**; defaults to 2,000 and is not a completeness guarantee.
- `DISCOVERY_OVERSAMPLE_FACTOR`: bounded provider oversampling before deduplication; defaults to 1.4.
- `SEARCH_SESSION_TTL_SECONDS`: absolute in-memory result-session lifetime; defaults to 1,800 seconds.
- `MAX_ACTIVE_SEARCH_SESSIONS`: oldest-session eviction bound; defaults to 20.
- `MAX_CACHED_SEARCH_RECORDS`: process-wide in-memory record bound; defaults to 10,000.
- `DEFAULT_PAGE_SIZE` / `MAX_PAGE_SIZE`: pagination defaults and safety maximum (50 / 100).
- `SEARXNG_BASE_URL`: optional URL of a self-hosted SearXNG service. Leave blank to disable search discovery.
- `SEARCH_PROVIDER`: legacy descriptive setting; it does not enable a network provider by itself.
- `CORS_ORIGINS`: comma-separated frontend origins.
- `SUPABASE_URL`: backend Supabase project URL; leave blank with the key to disable persistence.
- `SUPABASE_SECRET_KEY`: backend-only Supabase secret key. `SUPABASE_SERVICE_ROLE_KEY` is accepted as a legacy fallback.

Frontend:

- `NEXT_PUBLIC_API_URL`: browser-visible API URL, normally `http://localhost:8000`.

No variable requires a secret for the core Overture + OSM flow. Supabase persistence is disabled when both Supabase settings are blank. Never commit local `.env` files. Apply the migration and follow the verification queries in [docs/supabase.md](docs/supabase.md).

## API

- `GET /health`
- `GET /api/v1/categories`
- `GET /api/v1/locations/countries`
- `GET /api/v1/locations/regions?countryCode=IN`
- `GET /api/v1/locations/cities?countryCode=IN`
- `GET /api/v1/locations/cities/search?countryCode=IN&q=hyd`
- `POST /api/v1/businesses/discover`
- `GET /api/v1/businesses/search-sessions/{sessionId}?page=1&pageSize=50&filter=all`
- `POST /api/v1/businesses/search-sessions/{sessionId}/enrich`
- `GET /api/v1/businesses/search-sessions/{sessionId}/export?filter=all`
- `POST /api/v1/businesses/enrich`
- `POST /api/v1/businesses/enrich-batch`
- `POST /api/v1/businesses/export`

Example India request:

```json
{
  "countryCode": "IN",
  "region": "Telangana",
  "city": "Hyderabad",
  "category": "Dentist",
  "limit": 100,
  "pageSize": 50
}
```

The UI offers 100, 200, 300, 400, 500, or **All available**. “All available” means up to the configured safety cap; it is not a complete census. Discovery returns the first page plus a session ID, exact filtered summary, total/page counts, expiry, enrichment progress, and provider raw/accepted counts. Subsequent pages and filters are server-side, so the browser never needs the whole result set.

The session export endpoint returns every result matching the current server filter, not only the visible page. The workbook distinguishes official websites from directory/social presence, includes WhatsApp only when explicitly published, and retains provenance columns and formula-injection-safe text. The older request-body export remains for compatibility.

## India-first coverage

The UI defaults to India / Hyderabad, Telangana / Dentist / 100. A bundled GeoNames `cities5000` index provides 6,531 India city records and state/district-aware autocomplete without calling a public geocoder on each keystroke. See the data-source document for CC BY 4.0 attribution and the reproducible build command.

Overture queries require a bounded rectangle. Reviewed city rectangles remain preferred; other indexed India cities receive population-scaled search envelopes around GeoNames coordinates. These are deliberately approximate query bounds, not municipal boundaries. Ambiguous city names require selecting a state-aware suggestion, and unsupported India input returns a clear validation error.

Indian phone handling preserves the public source value while producing a normalized representation for comparison. It supports `+91`, 10-digit mobile numbers, and plausible STD-code landline formats without inventing missing digits. Addresses support locality, district, state, and PIN code.

## Website enrichment and safety

Known official websites are checked first. If optional SearXNG finds a candidate, it remains low-confidence until the website content matches the business using name, city, or known-contact evidence.

The crawler uses bounded `httpx` requests and Python's HTML parser. It checks robots rules, stays on the same registrable domain, follows at most four redirects, reads at most 1 MB per response, and inspects obvious contact/about/support/location/branch pages. It rejects non-HTTP schemes, credentials, unusual ports, localhost, private/link-local IPs, cloud metadata addresses, external-domain redirects, and known directory/social/booking platforms. It never executes downloaded scripts or bypasses access controls. It can read nested JSON-LD contact fields while ordinary scripts remain ignored; WhatsApp is recorded only from an explicit numbered WhatsApp link.

The lightweight audit records reachability, HTTPS, redirects, mobile viewport metadata, contact page, published contacts/socials, title/meta description, and broken responses. Labels are evidence-based: `No website found`, `Website listed`, `Website verified`, `Website unreachable`, `Basic digital presence`, or `Potential improvement opportunity`. Missing website data means only “not found in current sources,” never proof that no website exists.

## Opportunity score

`leadScore` is an internal sales-opportunity heuristic, not a judgment of business quality. It is deterministic and capped at 0–100:

- public phone: +30
- public email: +8
- phone plus no verified website: +45
- no website and no phone: +22
- unreachable website: +45
- missing HTTPS/mobile viewport/contact page/title/meta description: +5 to +12 each
- listed but unaudited website: +12
- reported open operating status: +5
- strong basic website signals: −22
- no public phone, email, or social contact caps the score at 35

High is 70+, Medium is 40–69, and Low is below 40. Every score includes human-readable reasons.

## Optional functionality

- **Ratings:** modeled as `rating`, `reviewCount`, and `ratingSource`, but left `null` unless a legitimate configured source provides them. Overture confidence is never presented as a customer rating.
- **SearXNG:** supported only through `SEARXNG_BASE_URL` for a user-operated instance. It is disabled by default and core discovery continues without it.
- **Playwright:** intentionally not in the core dependency/runtime path. Static HTTP covers the implemented safe inspection flow, and the application starts without a browser. If a future approved adapter is added, install only Chromium inside the active project environment:

  ```bash
  python -m pip install playwright
  python -m playwright install chromium
  ```

  Browser use must remain a bounded fallback for a known official website, never a default for every lead.

## Tests and quality checks

Backend, from `apps/api` with the virtual environment active:

```bash
python -m pytest -q
python -m compileall -q app
```

Frontend, from the repository root:

```bash
npm run lint
npm run typecheck
npm run build
```

External services are mocked in unit tests. Tests do not query live Overture or Overpass. A controlled live smoke check should be run manually and sparingly when validating provider connectivity.

Windows PowerShell (one Overture result, no Overpass):

```powershell
$env:LEADRADAR_RUN_LIVE_TESTS="1"
python -m pytest tests/integration/test_overture_live.py -q
Remove-Item Env:LEADRADAR_RUN_LIVE_TESTS
```

macOS/Linux:

```bash
LEADRADAR_RUN_LIVE_TESTS=1 python -m pytest tests/integration/test_overture_live.py -q
```

## Manual Hyderabad test

1. Start the API and frontend.
2. Open `http://localhost:3000`.
3. Select `India`, choose `Hyderabad, Telangana`, select `Dentist`, and set `100`.
4. Choose **Find leads**. Page 1 appears from an expiring server-side search session, followed by the first controlled enrichment batch.
5. Review provider raw/accepted counts and enrichment progress. Use phone/email/official-site/directory/opportunity/enrichment filters as needed.
6. Open a row to inspect contacts, location, digital audit, score reasons, source IDs, and field provenance.
7. Change pages and page size, then select **Download all filtered**. The workbook contains the entire filtered session, not only the visible page.

Expected fields include business name/category, phones and normalized phones, emails, website/status, locality/city/district/state/PIN, coordinates, social links, optional rating fields, confidence, discovery sources and IDs, per-field provenance, enrichment state, audit signals, lead score, opportunity level/reasons, and scrape timestamp. When Supabase is configured, eligible rows also appear in `public.leads` and the search metadata appears in `public.search_sessions`.

## Responsible use and known limitations

LeadRadar is for VLR's internal, responsible use of open listings and public business contact details. Do not use it to bypass CAPTCHAs, authentication, rate limits, robots policies, or platform terms; do not collect unrelated personal data.

Coverage depends on the upstream open datasets and public business websites. Overture availability requires current release/schema compatibility and network access to its public S3 data. Public Overpass endpoints can be slow or unavailable. The static crawler cannot extract contacts rendered only by JavaScript. Runtime search sessions expire and disappear on API restart, while configured Supabase records remain persistent. Live ratings, scheduled crawling, automatic outreach, and Playwright fallback are intentionally absent or optional.
