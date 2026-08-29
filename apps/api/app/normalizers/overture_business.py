import json
from collections.abc import Mapping, Sequence
from typing import Any

from app.core.websites import classify_website_url
from app.models.business import Business, BusinessAddress, FieldProvenance
from app.normalizers.contact import normalize_email, normalize_phone, normalize_website_url

_INDIA_REGION_NAMES = {
    "IN-AP": "Andhra Pradesh",
    "IN-DL": "Delhi",
    "IN-GJ": "Gujarat",
    "IN-HR": "Haryana",
    "IN-KA": "Karnataka",
    "IN-KL": "Kerala",
    "IN-MH": "Maharashtra",
    "IN-RJ": "Rajasthan",
    "IN-TG": "Telangana",
    "IN-TS": "Telangana",
    "IN-TN": "Tamil Nadu",
    "IN-UP": "Uttar Pradesh",
    "IN-WB": "West Bengal",
}


def _decoded(value: Any, expected_type: type) -> Any:
    if isinstance(value, expected_type):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return expected_type()
        return decoded if isinstance(decoded, expected_type) else expected_type()
    return expected_type()


def _unique_strings(value: Any) -> tuple[str, ...]:
    items = _decoded(value, list)
    return tuple(
        dict.fromkeys(
            str(item).strip() for item in items if item is not None and str(item).strip()
        )
    )


def _address(
    value: Any,
    *,
    fallback_city: str,
    fallback_state: str | None,
    fallback_country: str,
) -> BusinessAddress:
    addresses = _decoded(value, list)
    item = next((candidate for candidate in addresses if isinstance(candidate, Mapping)), {})
    freeform = str(item.get("freeform") or "").strip() or None
    locality = str(item.get("locality") or "").strip() or None
    postcode = str(item.get("postcode") or "").strip() or None
    raw_region = str(item.get("region") or "").strip() or None
    state = _INDIA_REGION_NAMES.get(raw_region or "", raw_region) or fallback_state
    country_code = str(item.get("country") or "").strip().upper()
    country = fallback_country if country_code in {"", "IN"} else country_code
    formatted = ", ".join(
        dict.fromkeys(
            part
            for part in (freeform, locality or fallback_city, state, postcode, country)
            if part
        )
    ) or None
    return BusinessAddress(
        postcode=postcode,
        locality=locality,
        city=locality or fallback_city,
        state=state,
        country=country,
        formatted=formatted,
    )


def normalize_overture_business(
    row: Mapping[str, Any],
    *,
    category: str,
    fallback_city: str,
    fallback_state: str | None,
    fallback_country: str,
) -> Business:
    names = _decoded(row.get("names"), dict)
    categories = _decoded(row.get("categories"), dict)
    name = str(names.get("primary") or "").strip() or "Unnamed business"
    primary_category = str(categories.get("primary") or "").strip()
    alternates = categories.get("alternate")
    raw_categories = [primary_category]
    if isinstance(alternates, Sequence) and not isinstance(alternates, str):
        raw_categories.extend(str(value).strip() for value in alternates if value is not None)
    subcategories = tuple(
        dict.fromkeys(
            item.replace("_", " ").title()
            for item in raw_categories
            if item
        )
    )
    raw_phones = _unique_strings(row.get("phones"))
    normalized_phones = tuple(
        dict.fromkeys(value for item in raw_phones if (value := normalize_phone(item)))
    )
    emails = tuple(
        dict.fromkeys(
            value for item in _unique_strings(row.get("emails")) if (value := normalize_email(item))
        )
    )
    all_websites = tuple(
        dict.fromkeys(
            value
            for item in _unique_strings(row.get("websites"))
            if (value := normalize_website_url(item))
        )
    )
    raw_socials = tuple(
        dict.fromkeys(
            value
            for item in _unique_strings(row.get("socials"))
            if (value := normalize_website_url(item))
        )
    )
    websites = tuple(value for value in all_websites if classify_website_url(value) == "official")
    directories = tuple(
        dict.fromkeys(
            value
            for value in (*all_websites, *raw_socials)
            if classify_website_url(value) == "directory"
        )
    )
    socials = tuple(
        dict.fromkeys(
            value
            for value in (*all_websites, *raw_socials)
            if classify_website_url(value) == "social"
        )
    )
    confidence = row.get("confidence")
    numeric_confidence = float(confidence) if isinstance(confidence, int | float) else None
    provenance_confidence = (
        "high" if numeric_confidence is not None and numeric_confidence >= 0.7 else "medium"
    )
    provenance: dict[str, tuple[FieldProvenance, ...]] = {}
    for field_name, values in (
        ("phone", raw_phones),
        ("email", emails),
        ("website", websites),
        ("social_links", socials),
        ("directory_links", directories),
    ):
        if values:
            provenance[field_name] = tuple(
                FieldProvenance(
                    value=value,
                    source="overture",
                    confidence=provenance_confidence,
                    detail="Overture Maps Places",
                )
                for value in values
            )

    source_id = f"overture:{row.get('id', 'unknown')}"
    return Business(
        source_id=source_id,
        source="overture",
        name=name,
        category=category,
        address=_address(
            row.get("addresses"),
            fallback_city=fallback_city,
            fallback_state=fallback_state,
            fallback_country=fallback_country,
        ),
        latitude=(
            float(row["latitude"]) if isinstance(row.get("latitude"), int | float) else None
        ),
        longitude=(
            float(row["longitude"]) if isinstance(row.get("longitude"), int | float) else None
        ),
        phone=raw_phones[0] if raw_phones else None,
        email=emails[0] if emails else None,
        website=websites[0] if websites else None,
        opening_hours=None,
        subcategories=subcategories,
        phones=raw_phones,
        normalized_phones=normalized_phones,
        emails=emails,
        websites=websites,
        website_status="listed" if websites else "not_found",
        website_type="official" if websites else "none",
        directory_links=directories,
        social_links=socials,
        confidence=numeric_confidence,
        sources=("overture",),
        source_ids={"overture": (source_id,)},
        field_provenance=provenance,
        operating_status=str(row.get("operating_status") or "") or None,
    )
