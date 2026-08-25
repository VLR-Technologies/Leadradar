from collections.abc import Mapping
from typing import Any

from app.models.business import Business, BusinessAddress


def _first_value(tags: Mapping[str, str], *keys: str) -> str | None:
    for key in keys:
        value = tags.get(key)
        if value and value.strip():
            return value.strip()
    return None


def _format_address(
    *,
    street: str | None,
    house_number: str | None,
    postcode: str | None,
    city: str | None,
    state: str | None,
    country: str | None,
    full_address: str | None,
) -> str | None:
    if full_address:
        return full_address

    street_line = " ".join(part for part in (street, house_number) if part)
    city_line = " ".join(part for part in (postcode, city) if part)
    parts = [part for part in (street_line, city_line, state, country) if part]
    return ", ".join(parts) or None


def normalize_osm_business(
    element: Mapping[str, Any],
    *,
    category: str,
    fallback_city: str | None = None,
    fallback_country: str | None = None,
    include_raw_tags: bool = False,
) -> Business:
    element_type = str(element.get("type", "unknown"))
    element_id = str(element.get("id", "unknown"))
    raw_tags = element.get("tags")
    tags: dict[str, str] = (
        {str(key): str(value) for key, value in raw_tags.items()}
        if isinstance(raw_tags, Mapping)
        else {}
    )

    center = element.get("center") if isinstance(element.get("center"), Mapping) else {}
    latitude = element.get("lat", center.get("lat"))
    longitude = element.get("lon", center.get("lon"))

    street = _first_value(tags, "addr:street")
    house_number = _first_value(tags, "addr:housenumber")
    postcode = _first_value(tags, "addr:postcode")
    city = _first_value(tags, "addr:city", "addr:place") or fallback_city
    state = _first_value(tags, "addr:state")
    country = _first_value(tags, "addr:country") or fallback_country
    full_address = _first_value(tags, "addr:full")

    address = BusinessAddress(
        street=street,
        house_number=house_number,
        postcode=postcode,
        city=city,
        state=state,
        country=country,
        formatted=_format_address(
            street=street,
            house_number=house_number,
            postcode=postcode,
            city=city,
            state=state,
            country=country,
            full_address=full_address,
        ),
    )

    return Business(
        source_id=f"{element_type}:{element_id}",
        source="openstreetmap",
        name=_first_value(tags, "name", "brand", "operator") or "Unnamed business",
        category=category,
        address=address,
        latitude=float(latitude) if isinstance(latitude, int | float) else None,
        longitude=float(longitude) if isinstance(longitude, int | float) else None,
        phone=_first_value(tags, "phone", "contact:phone", "mobile", "contact:mobile"),
        email=_first_value(tags, "email", "contact:email"),
        website=_first_value(tags, "website", "contact:website", "url"),
        opening_hours=_first_value(tags, "opening_hours"),
        raw_tags=tags if include_raw_tags else {},
    )

