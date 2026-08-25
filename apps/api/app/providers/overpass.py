import asyncio
import json
from collections import OrderedDict
from collections.abc import Sequence
from typing import Any

import httpx

from app.core.categories import BusinessCategory, OsmTagFilter
from app.models.business import Business
from app.models.location import ResolvedLocation
from app.normalizers.osm_business import normalize_osm_business
from app.providers.base import (
    LocationResolutionError,
    MalformedProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)


def _overpass_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _tag_selector(tag_filter: OsmTagFilter) -> str:
    key = _overpass_string(tag_filter.key)
    if tag_filter.value is None:
        return f"[{key}]"
    return f"[{key}={_overpass_string(tag_filter.value)}]"


def _named_boundary_queries(
    *,
    input_area: str,
    names: Sequence[str],
    extended_fallback: bool,
) -> str:
    queries: list[str] = []
    for name in names:
        encoded_name = _overpass_string(name)
        element_types = ("rel", "way") if extended_fallback else ("rel",)
        for element_type in element_types:
            for name_key in ("name", "name:en"):
                queries.append(
                    f'  {element_type}(area.{input_area})["boundary"="administrative"]'
                    f'[{_overpass_string(name_key)}={encoded_name}];'
                )
                if extended_fallback:
                    queries.append(
                        f'  {element_type}(area.{input_area})'
                        f'["place"~"^(city|town|municipality)$"]'
                        f'[{_overpass_string(name_key)}={encoded_name}];'
                    )
    return "\n".join(queries)


def _boundary_id_queries(boundaries: Sequence[dict[str, Any]]) -> str:
    relation_ids = [
        str(element["id"])
        for element in boundaries
        if element.get("type") == "relation"
    ]
    way_ids = [
        str(element["id"])
        for element in boundaries
        if element.get("type") == "way"
    ]
    return "\n".join(
        query
        for query in (
            f"  rel(id:{','.join(relation_ids)});" if relation_ids else "",
            f"  way(id:{','.join(way_ids)});" if way_ids else "",
        )
        if query
    )


def build_region_query(
    *,
    location: ResolvedLocation,
    extended_fallback: bool = False,
) -> str:
    country = _overpass_string(location.country_code)
    region_queries = _named_boundary_queries(
        input_area="country",
        names=location.region_query_names,
        extended_fallback=extended_fallback,
    )
    return f"""[out:json][timeout:25];
area[\"boundary\"=\"administrative\"][\"ISO3166-1\"={country}][\"admin_level\"=\"2\"]->.country;
(
{region_queries}
)->.regionBoundary;
.regionBoundary out ids;"""


def build_city_query(
    *,
    location: ResolvedLocation,
    region_boundaries: Sequence[dict[str, Any]] = (),
    extended_fallback: bool = False,
) -> str:
    if region_boundaries:
        region_boundary_queries = _boundary_id_queries(region_boundaries)
        scope_resolution = f"""(
{region_boundary_queries}
)->.regionBoundary;
.regionBoundary map_to_area->.regionArea;"""
        city_input_area = "regionArea"
    else:
        country = _overpass_string(location.country_code)
        scope_resolution = (
            'area["boundary"="administrative"]'
            f'["ISO3166-1"={country}]["admin_level"="2"]->.country;'
        )
        city_input_area = "country"

    city_boundary_queries = _named_boundary_queries(
        input_area=city_input_area,
        names=location.city_query_names,
        extended_fallback=extended_fallback,
    )
    return f"""[out:json][timeout:25];
{scope_resolution}
(
{city_boundary_queries}
)->.cityBoundary;
.cityBoundary out ids;"""


def build_business_query(
    *,
    boundaries: Sequence[dict[str, Any]],
    filters: Sequence[OsmTagFilter],
    limit: int,
) -> str:
    boundary_queries = _boundary_id_queries(boundaries)
    business_queries = "\n".join(
        f"  nwr{_tag_selector(tag_filter)}(area.searchArea);" for tag_filter in filters
    )

    return f"""[out:json][timeout:25];
(
{boundary_queries}
)->.cityBoundary;
.cityBoundary map_to_area->.searchArea;
(
{business_queries}
);
out center {limit};"""


class OverpassProvider:
    def __init__(
        self,
        *,
        base_url: str = "https://lz4.overpass-api.de/api/interpreter",
        timeout_seconds: float = 35.0,
        client: httpx.AsyncClient | None = None,
        rate_limit_retry_seconds: float = 30.0,
    ) -> None:
        self._base_url = base_url
        self._timeout = httpx.Timeout(timeout_seconds)
        self._client = client
        self._rate_limit_retry_seconds = rate_limit_retry_seconds
        self._boundary_cache: OrderedDict[
            tuple[str, str | None, tuple[str, ...]],
            tuple[dict[str, Any], ...],
        ] = OrderedDict()

    async def _execute_query(
        self,
        *,
        client: httpx.AsyncClient,
        query: str,
    ) -> list[dict[str, Any]]:
        response: httpx.Response | None = None
        for attempt in range(2):
            try:
                response = await client.post(
                    self._base_url,
                    data={"data": query},
                    headers={"User-Agent": "LeadRadar/0.1 (internal business discovery)"},
                )
            except httpx.TimeoutException as exc:
                raise ProviderTimeoutError("Overpass request timed out") from exc
            except httpx.HTTPError as exc:
                raise ProviderUnavailableError("Overpass request failed") from exc

            if response.status_code == 429 and attempt == 0:
                await asyncio.sleep(self._rate_limit_retry_seconds)
                continue

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in {408, 504}:
                    raise ProviderTimeoutError("Overpass request timed out") from exc
                raise ProviderUnavailableError("Overpass request failed") from exc
            break

        if response is None:
            raise ProviderUnavailableError("Overpass request failed")

        try:
            payload: Any = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise MalformedProviderResponseError("Overpass returned invalid JSON") from exc

        if not isinstance(payload, dict) or not isinstance(payload.get("elements"), list):
            raise MalformedProviderResponseError("Overpass response did not contain elements")
        if "timed out" in str(payload.get("remark", "")).casefold():
            raise ProviderTimeoutError("Overpass query timed out")

        return [
            element
            for element in payload["elements"]
            if isinstance(element, dict) and element.get("id") is not None
        ]

    async def discover(
        self,
        *,
        location: ResolvedLocation,
        category: BusinessCategory,
        limit: int,
    ) -> list[Business]:
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._timeout)
        try:
            cache_key = (
                location.country_code,
                location.region,
                location.city_query_names,
            )
            cached_boundaries = self._boundary_cache.get(cache_key)
            boundaries = list(cached_boundaries) if cached_boundaries else []
            if cached_boundaries:
                self._boundary_cache.move_to_end(cache_key)
            elif location.boundary_relation_ids:
                boundaries = [
                    {"type": "relation", "id": relation_id}
                    for relation_id in location.boundary_relation_ids
                ]

            if not boundaries:
                region_boundaries: list[dict[str, Any]] = []
                if location.region_query_names:
                    region_elements = await self._execute_query(
                        client=client,
                        query=build_region_query(location=location),
                    )
                    region_boundaries = [
                        element
                        for element in region_elements
                        if _is_location_marker(element)
                    ]
                    if not region_boundaries:
                        region_elements = await self._execute_query(
                            client=client,
                            query=build_region_query(
                                location=location,
                                extended_fallback=True,
                            ),
                        )
                        region_boundaries = [
                            element
                            for element in region_elements
                            if _is_location_marker(element)
                        ]
                    if not region_boundaries:
                        raise LocationResolutionError(
                            f"Unable to resolve {location.display_name} to a supported "
                            "OpenStreetMap search area."
                        )

                city_elements = await self._execute_query(
                    client=client,
                    query=build_city_query(
                        location=location,
                        region_boundaries=region_boundaries,
                    ),
                )
                boundaries = [
                    element
                    for element in city_elements
                    if _is_location_marker(element)
                ]
                if not boundaries:
                    city_elements = await self._execute_query(
                        client=client,
                        query=build_city_query(
                            location=location,
                            region_boundaries=region_boundaries,
                            extended_fallback=True,
                        ),
                    )
                    boundaries = [
                        element
                        for element in city_elements
                        if _is_location_marker(element)
                    ]
                if not boundaries:
                    raise LocationResolutionError(
                        f"Unable to resolve {location.display_name} to a supported "
                        "OpenStreetMap search area."
                    )
                self._boundary_cache[cache_key] = tuple(boundaries)
                self._boundary_cache.move_to_end(cache_key)
                if len(self._boundary_cache) > 128:
                    self._boundary_cache.popitem(last=False)

            business_query = build_business_query(
                boundaries=boundaries,
                filters=category.osm_filters,
                limit=limit,
            )
            elements = await self._execute_query(
                client=client,
                query=business_query,
            )
        finally:
            if owns_client:
                await client.aclose()

        return [
            normalize_osm_business(
                element,
                category=category.label,
                fallback_city=location.city,
                fallback_country=location.country,
            )
            for element in elements
        ]


def _is_location_marker(element: dict[str, Any]) -> bool:
    return element.get("type") in {"relation", "way"} and "tags" not in element
