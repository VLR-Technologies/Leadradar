# Lead Radar architecture

Lead Radar Phase 1C keeps discovery, enrichment, transport, external providers, and UI concerns separate.

```text
Next.js dashboard
    ↓ typed HTTP client
FastAPI route
    ↓
BusinessDiscoveryService
    ↓
LocationResolver → ResolvedLocation
    ↓ provider protocol
OverpassProvider
    ↓
normalize_osm_business
    ↓
Business domain model → Pydantic response schema

Business selected by user
    ↓
BusinessEnrichmentService
    ↓
OfficialWebsiteEnrichmentProvider / BusinessSearchProvider
    ↓
provenance-aware deterministic merge
    ↓
updated frontend row + detail drawer
```

## Backend boundaries

- `api/routes` owns HTTP behavior and maps known application/provider failures to HTTP status codes.
- `services` validates categories, resolves country/region/city input, coordinates provider calls, and performs source-ID deduplication.
- `providers` owns external source communication. `BusinessProvider` is the seam for adding future permitted sources.
- `normalizers` converts provider-specific records to source-neutral domain models.
- `models` contains persistence-neutral domain objects.
- `schemas` owns the public JSON contract and camelCase serialization.
- `core` contains environment configuration and central catalogues.

This structure allows a persistence repository to be introduced between the service and route in Phase 2 without moving Overpass parsing into database code.

## Contact enrichment strategy

Discovery never triggers enrichment automatically. A row-level `Enrich` action submits the already-normalized business to `/api/v1/businesses/enrich`. The service preserves all OpenStreetMap contacts as provenance records, optionally asks a configured permitted search provider for a candidate only when the website is missing, inspects the candidate, and applies deterministic merge rules. The backend also exposes a batch contract capped at 20 with a small concurrency semaphore, but the Phase 1C UI intentionally remains single-lead and user-triggered.

`WebsiteEnrichmentProvider` fetches only static HTML with a clear `LeadRadar/0.1` user agent. It checks explicit robots rules, follows a small number of redirects, enforces a one-megabyte response cap, and inspects no more than the configured 1–5 pages. Contact/about/reach-us/enquiry links are discovered from paths and anchor text. Only the same registrable domain is followed. Private, loopback, link-local, non-HTTP, credential-bearing, and unusual-port URLs are rejected to limit server-side request forgery risk. Known social, search, directory, and booking platforms are displayed if OSM lists them but are not crawled.

Website verification is conservative. A successful HTTP response alone is insufficient: the combined page text must match the business name, or combine a meaningful partial name match with city or existing-contact evidence. A mismatched candidate contributes no phone or email. Static `tel:` and `mailto:` values receive high confidence; visible contact-section values receive medium confidence. Search candidates remain low confidence until independently verified.

The merge order is verified official website, then OpenStreetMap, then unverified search metadata. Conflicting values are retained in `alternatives` with their original source and confidence instead of being overwritten anonymously. Phone normalization handles Indian mobile country-code variants and preserves plausible STD-code landlines. Email normalization trims mailto parameters, lowercases domains, deduplicates, and rejects obvious placeholders.

Final status is assigned only by `determine_enrichment_status` in the service layer. Providers report facts such as reachability, verification, extracted contacts, and errors; they do not decide the aggregate UX state. The classifier compares the normalized pre-enrichment record with verified provider results:

- `completed`: every phone/email field that was missing before enrichment was filled.
- `partial`: a verified website or some additional contact information was obtained, but relevant missing contact fields remain.
- `no_data`: execution completed normally with no useful addition, including the disabled-search/no-website case.
- `failed`: execution was interrupted by a technical or provider error.

Website verification and enrichment status remain independent. A verified website with no new phone or email is `websiteStatus=verified` and `status=partial`; an inspected but unverified/mismatched candidate with no usable addition is `status=no_data`. Pre-existing OSM fields never make a technical error look partial and are never removed by an empty or failed attempt. Machine-readable reason codes are separate from safe user-facing messages.

`BusinessSearchProvider` is an interface only in this phase. The default disabled implementation returns no candidate, so missing-website enrichment produces a structured result rather than breaking discovery. No Google, Justdial, LinkedIn, or search-engine HTML scraping exists.

## International location strategy

The backend catalogue is the source of truth for Germany (`DE`), the United Kingdom (`GB`), the United States (`US`), and India (`IN`). Country records define whether region context is required, while city records provide canonical names, optional state associations, aliases, and permitted OSM lookup names.

`LocationResolver` converts a validated request into a provider-neutral `ResolvedLocation`. It canonicalizes country codes, enforces a state for United States searches, rejects known city/state mismatches, resolves aliases, and preserves arbitrary city input for future coverage.

The Overpass provider uses the resolved country ISO code to establish a country area. If region context is present, it resolves that administrative boundary first and scopes the city lookup inside it. The city boundary is then converted with `map_to_area` before business tags are queried. Administrative levels are intentionally not hardcoded because they differ across countries.

Known-good catalogue entries may carry a verified, stable OSM boundary relation ID; the four required integration cities currently do. This lets common searches move directly to the business query while country/state validation still happens in `LocationResolver`. Other catalogue and arbitrary cities use exact administrative-relation resolution. If the primary lookup returns no location marker, one broader fallback also considers closed boundary ways and place-tagged city/town/municipality objects within the same country or region scope. Once resolved, a separate bounded business query maps the trusted boundary IDs to an area and retrieves matching businesses. This avoids expensive combined Overpass query plans and never issues per-business requests. If resolution still cannot produce an area, the API returns a clear error rather than searching an arbitrary nearby location.

Resolved boundary IDs use a 128-entry in-process LRU cache, which reduces repeated metadata lookups without caching business results. A public-provider `429` response receives one policy-aware, bounded retry; other requests are not retried aggressively. Each user search remains request-based. No background crawl, result persistence, or indefinite business-result cache exists. Adding another country or alias does not require changing the API route, discovery service, provider protocol, or frontend types.

## API location metadata

The frontend obtains countries, regions, and suggested cities from `/api/v1/locations/*`. US country selection reveals a required state control, and its selected state filters the city suggestions. Other countries currently omit the irrelevant region field. The city control uses backend suggestions but remains free-text capable.

## Data semantics

A null website means only that the current OpenStreetMap record does not list a website. The UI labels that state “Not listed,” never “No website.” Listed, verified, unreachable, and mismatch states are distinct. Phone and email availability likewise describe current source/enrichment data, not proof of absence.

Enrichment failures and `no_data` outcomes never remove discovery records or existing OSM contacts. All enrichment is transient, manually triggered, and held in browser state; no database, background job, automatic outreach, lead score, website audit, or continuous crawler exists.
