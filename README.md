# Lead Radar

Lead Radar is VLR Technologies' internal business lead-discovery platform. Phase 1C finds real businesses through OpenStreetMap, displays their contact fields in a sales-oriented table, and lets a user inspect a selected business's known official website for public phone and email details.

This phase intentionally contains no database, authentication, AI, lead scoring, outreach, automatic mass enrichment, or commercial-platform scraping.

## Architecture

```text
Next.js dashboard
        ↓
FastAPI API
        ↓
Business Discovery Service
        ↓
Location Resolver → Resolved Location
        ↓
OpenStreetMap / Overpass Provider
        ↓
OSM Normalizer → Business domain model

Manual Enrich action
        ↓
Business Enrichment Service
        ↓
Official Website Provider + optional Search Provider interface
        ↓
Provenance-aware merge → updated row and detail drawer
```

Frontend and backend live in separate workspaces under `apps/web` and `apps/api`. The provider protocol and domain model keep the discovery service independent from Overpass and ready for future persistence. See [docs/architecture.md](docs/architecture.md) for the boundaries and location strategy.

## Requirements

- Node.js 20 or newer
- npm 10 or newer
- Python 3.12 or newer

## Environment setup

The repository-level `.env.example` documents every variable. Each app also has its own focused example.

```bash
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env.local
```

Variables:

- `OVERPASS_API_URL`: Overpass interpreter endpoint.
- `OVERPASS_TIMEOUT_SECONDS`: upstream request timeout, between 5 and 120 seconds.
- `CORS_ORIGINS`: comma-separated browser origins allowed by FastAPI.
- `ENRICHMENT_HTTP_TIMEOUT_SECONDS`: per-request official website timeout, between 2 and 30 seconds.
- `ENRICHMENT_MAX_PAGES`: maximum same-domain HTML pages inspected per business, between 1 and 5.
- `ENRICHMENT_BATCH_LIMIT`: maximum businesses accepted by the batch API, capped at 20.
- `ENRICHMENT_MAX_CONCURRENCY`: maximum simultaneous businesses in a batch, capped at 5.
- `SEARCH_PROVIDER`: optional permitted search-provider name. Leave blank to disable website discovery.
- `NEXT_PUBLIC_API_URL`: browser-visible FastAPI base URL.

No secrets are required for OpenStreetMap discovery or enrichment of an OSM-listed official website. No search API implementation or credential is enabled by default.

## Backend setup

From the repository root:

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

The API runs at [http://localhost:8000](http://localhost:8000), with interactive API documentation at [http://localhost:8000/docs](http://localhost:8000/docs).

Run backend tests from `apps/api` with:

```bash
source .venv/bin/activate
pytest
```

## Frontend setup

In a second terminal, from the repository root:

```bash
npm install
npm run dev:web
```

The dashboard runs at [http://localhost:3000](http://localhost:3000).

Quality checks:

```bash
npm run lint
npm run build
```

## Root development scripts

After the dependencies and Python environment are installed:

```bash
npm run dev:api
npm run dev:web
```

Run each command in its own terminal. The API script uses the active Python environment.

## API endpoints

- `GET /health` — API health response.
- `GET /api/v1/categories` — application-level category catalogue.
- `GET /api/v1/locations/countries` — supported countries and region requirements.
- `GET /api/v1/locations/regions?countryCode=US` — supported regions for a country.
- `GET /api/v1/locations/cities?countryCode=US&region=California` — suggested cities, optionally filtered by region.
- `POST /api/v1/businesses/discover` — validated business discovery request.
- `POST /api/v1/businesses/enrich` — manually inspect one business's known or permitted-provider candidate website.
- `POST /api/v1/businesses/enrich-batch` — bounded backend batch contract for up to 20 businesses; the current UI intentionally uses single-row enrichment.

Example request:

```json
{
  "countryCode": "US",
  "region": "California",
  "city": "San Francisco",
  "category": "Cafe",
  "limit": 100
}
```

Germany remains compatible through the new canonical contract:

```json
{
  "countryCode": "DE",
  "region": null,
  "city": "Berlin",
  "category": "Dentist",
  "limit": 100
}
```

Limits must be between 1 and 500. Country codes are canonical ISO-style values. United States requests require a region/state so ambiguous city names are scoped safely.

Example enrichment request:

```json
{
  "business": {
    "sourceId": "node:123456",
    "source": "openstreetmap",
    "name": "ABC Dental Clinic",
    "category": "Dentist",
    "address": {
      "city": "Hyderabad",
      "state": "Telangana",
      "country": "India"
    },
    "latitude": 17.4,
    "longitude": 78.4,
    "phone": null,
    "email": null,
    "website": "https://abcdental.in",
    "openingHours": null
  }
}
```

Enrichment results keep a primary value and provenance-preserving alternatives for phone, email, and website. Sources are `openstreetmap`, `official_website`, or `search_provider`; confidence is deterministic (`high`, `medium`, or `low`).

### Enrichment status semantics

Enrichment status describes the result of the manual enrichment attempt, not the business's overall contact coverage:

- `completed` — the attempt succeeded and filled all contact fields that were missing before enrichment.
- `partial` — the attempt succeeded and produced a useful but incomplete improvement, including verified-website-only results.
- `no_data` — the attempt completed normally but found no useful additional information. This includes the safe default where no website is listed and no search provider is configured.
- `failed` — a genuine technical or provider problem prevented the attempt from completing, such as a timeout, DNS failure, refused access, invalid URL, parsing problem, or provider exception.

`no_data` is not a failure. Existing OpenStreetMap phone, email, and website values remain visible regardless of the enrichment outcome. The response also contains a camelCase `reasonCode` and a safe user-facing `message`; low-level exception details are never returned.

## Supported countries and location flow

- Germany (`DE`)
- United Kingdom (`GB`)
- United States (`US`)
- India (`IN`)

```text
Country
    ↓
Region/state when required
    ↓
City
    ↓
Business category
    ↓
Overpass discovery
```

The dashboard loads country, state, and suggested city options from the backend rather than maintaining separate frontend catalogues. The city input still accepts free text, so the catalogue improves common searches without making arbitrary future cities impossible.

The initial city suggestions include:

- Germany: Berlin, Hamburg, Munich, Frankfurt, Cologne, Stuttgart, Düsseldorf, Leipzig, Dortmund, Dresden, Hannover, Nuremberg, and Bremen.
- United Kingdom: London, Manchester, Birmingham, Liverpool, Leeds, Glasgow, Edinburgh, Bristol, Sheffield, Newcastle upon Tyne, Nottingham, Cardiff, and Belfast.
- United States: New York, Los Angeles, Chicago, Houston, Phoenix, Philadelphia, San Antonio, San Diego, Dallas, San Jose, San Francisco, Seattle, Boston, Miami, Austin, Denver, and Washington, with state associations.
- India: Hyderabad, Bengaluru, Mumbai, Delhi, Chennai, Pune, Kolkata, Ahmedabad, Jaipur, Kochi, Gurugram, Noida, Visakhapatnam, Coimbatore, and Surat.

Aliases such as Munich/München, Cologne/Köln, Nuremberg/Nürnberg, Bangalore/Bengaluru, Bombay/Mumbai, Calcutta/Kolkata, Madras/Chennai, and Cochin/Kochi are resolved centrally by the backend.

## Supported categories

- Restaurant
- Cafe
- Dentist
- Doctor / Clinic
- Law Firm
- Accountant
- Consulting
- Real Estate Agency
- Hotel
- Beauty Salon
- Barber
- Gym / Fitness
- Car Repair
- Retail Store
- Construction
- Travel Agency
- Education / Training

The central backend catalogue maps these application labels to one or more OSM tag filters. Raw OSM syntax is not exposed in the UI category selector.

## Data-source note

OpenStreetMap coverage varies. “Website not listed” means only that the website field is absent from the current OSM record; it does not mean the business has no website. “Verified” appears only after the user manually enriches a lead and the page matches the business using conservative name, location, or known-contact evidence.

Official website inspection fetches the homepage and at most a few likely contact/about pages. It stays on the same registrable domain, checks explicit robots rules, rejects private/internal addresses and known directory/social/booking platforms, does not execute JavaScript, and caps response size. It does not scrape Google Search, Google Maps, Justdial, LinkedIn, or search-engine HTML.

Discovery and enrichment remain request-based. Nothing is scheduled, continuously crawled, or stored. Enriched values and terminal row states live only in frontend state until Phase 2 persistence is designed. City-boundary coverage, OSM contact coverage, static-HTML availability, and public website behavior vary by business.
