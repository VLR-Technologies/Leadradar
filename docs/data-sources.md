# Open data sources and attribution

LeadRadar's core discovery path uses only open/public sources. Coverage reflects what those sources publish; missing data is never presented as proof that a business or contact channel does not exist.

## Overture Maps Places

- Purpose: primary business-place discovery.
- Access: the public Overture release catalogue and GeoParquet data in public S3, queried through DuckDB.
- Project: [Overture Maps Foundation](https://overturemaps.org/).
- License and attribution: follow the license/attribution metadata for the Overture release being queried. LeadRadar preserves `overture` as a record and field-provenance source.

## OpenStreetMap

- Purpose: secondary business discovery and complementary public fields.
- Access: public Overpass endpoints, with bounded requests and failover.
- Copyright: © OpenStreetMap contributors.
- License: [Open Database License (ODbL)](https://www.openstreetmap.org/copyright).
- LeadRadar preserves `openstreetmap` as a record and field-provenance source.

## GeoNames India city index

- Purpose: local India-wide city autocomplete and approximate geographic search envelopes. It is not used as a business-data source.
- Source file: [`cities5000.zip`](https://download.geonames.org/export/dump/cities5000.zip), plus the GeoNames admin-code files.
- Attribution: [GeoNames](https://www.geonames.org/).
- License: [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/).
- Bundled artifact: `apps/api/app/data/india_cities.json` (6,531 India records in the generated artifact).
- Rebuild: from `apps/api`, run `python scripts/build_india_locations.py` while online.

The generated rectangles are population-scaled search envelopes around GeoNames coordinates, not administrative boundaries. LeadRadar retains its reviewed boxes/boundary IDs for known cities and clearly marks generated envelopes internally.

## Official business websites

Enrichment visits only candidate official domains. Known directories, booking/listing platforms, and social domains are classified separately and are not crawled. The bounded crawler respects robots rules, stays within the original registrable domain, rejects private/non-public network targets, and does not execute page scripts. Visible contacts, `mailto:`/`tel:` links, JSON-LD, and explicit numbered WhatsApp links retain page URL and extraction-method provenance.
