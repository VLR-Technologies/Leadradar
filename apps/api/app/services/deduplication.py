import hashlib
import math
import re
import unicodedata
from dataclasses import replace
from difflib import SequenceMatcher
from urllib.parse import urlsplit

from app.models.business import Business, BusinessAddress, FieldProvenance
from app.normalizers.contact import normalize_email, normalize_phone, normalize_website_url

_BUSINESS_SUFFIXES = {
    "and",
    "co",
    "company",
    "india",
    "limited",
    "llp",
    "ltd",
    "private",
    "pvt",
    "the",
}
_SOURCE_PRIORITY = {"overture": 0, "openstreetmap": 1}


def normalize_business_name(value: str) -> str:
    ascii_value = "".join(
        character
        for character in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(character)
    )
    words = re.findall(r"[a-z0-9]+", ascii_value.casefold())
    meaningful = [word for word in words if word not in _BUSINESS_SUFFIXES]
    return " ".join(meaningful or words)


def _similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, left, right).ratio() if left and right else 0.0


def _distance_metres(left: Business, right: Business) -> float | None:
    if None in {left.latitude, left.longitude, right.latitude, right.longitude}:
        return None
    latitude_1 = math.radians(float(left.latitude))
    latitude_2 = math.radians(float(right.latitude))
    delta_latitude = latitude_2 - latitude_1
    delta_longitude = math.radians(float(right.longitude) - float(left.longitude))
    haversine = (
        math.sin(delta_latitude / 2) ** 2
        + math.cos(latitude_1)
        * math.cos(latitude_2)
        * math.sin(delta_longitude / 2) ** 2
    )
    return 6_371_000 * 2 * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))


def _address_text(business: Business) -> str:
    return " ".join(
        part
        for part in (
            business.address.formatted,
            business.address.street,
            business.address.house_number,
            business.address.locality,
            business.address.city,
            business.address.postcode,
        )
        if part
    ).casefold()


def _website_domains(business: Business) -> set[str]:
    domains: set[str] = set()
    for value in (business.website, *business.websites):
        normalized = normalize_website_url(value or "")
        if normalized and (host := urlsplit(normalized).hostname):
            domains.add(host.casefold().removeprefix("www."))
    return domains


def _phone_values(business: Business) -> set[str]:
    return {
        normalized
        for value in (business.phone, *business.phones)
        if value and (normalized := normalize_phone(value))
    }


def businesses_match(left: Business, right: Business) -> bool:
    if left.source == right.source and left.source_id == right.source_id:
        return True
    left_name = normalize_business_name(left.name)
    right_name = normalize_business_name(right.name)
    name_similarity = _similarity(left_name, right_name)
    if name_similarity < 0.58:
        return False

    distance = _distance_metres(left, right)
    address_similarity = _similarity(_address_text(left), _address_text(right))
    shared_phone = bool(_phone_values(left) & _phone_values(right))
    shared_domain = bool(_website_domains(left) & _website_domains(right))

    if distance is not None:
        if distance <= 60 and name_similarity >= 0.72:
            return True
        if distance <= 180 and name_similarity >= 0.90:
            return True
        if shared_phone and distance <= 300 and name_similarity >= 0.72:
            return True
        return shared_domain and distance <= 200 and name_similarity >= 0.78

    if shared_phone and name_similarity >= 0.88 and address_similarity >= 0.55:
        return True
    if shared_domain and name_similarity >= 0.92 and address_similarity >= 0.65:
        return True
    return name_similarity >= 0.96 and address_similarity >= 0.82


def _unique(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = value.strip()
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return tuple(result)


def _merged_address(businesses: list[Business]) -> BusinessAddress:
    ranked = sorted(
        businesses,
        key=lambda item: (
            -sum(
                bool(value)
                for value in (
                    item.address.formatted,
                    item.address.street,
                    item.address.house_number,
                    item.address.postcode,
                    item.address.locality,
                    item.address.district,
                    item.address.city,
                    item.address.state,
                    item.address.country,
                )
            ),
            _SOURCE_PRIORITY.get(item.source, 99),
        ),
    )

    def first(field_name: str) -> str | None:
        return next(
            (
                value
                for item in ranked
                if (value := getattr(item.address, field_name)) is not None
            ),
            None,
        )

    return BusinessAddress(
        street=first("street"),
        house_number=first("house_number"),
        postcode=first("postcode"),
        locality=first("locality"),
        district=first("district"),
        city=first("city"),
        state=first("state"),
        country=first("country"),
        formatted=first("formatted"),
    )


def _merged_provenance(
    businesses: list[Business],
) -> dict[str, tuple[FieldProvenance, ...]]:
    result: dict[str, tuple[FieldProvenance, ...]] = {}
    fields = {field for business in businesses for field in business.field_provenance}
    for field_name in fields:
        values: list[FieldProvenance] = []
        seen: set[tuple[str, str]] = set()
        for business in businesses:
            for item in business.field_provenance.get(field_name, ()):
                key = (item.value.casefold(), item.source)
                if key not in seen:
                    seen.add(key)
                    values.append(item)
        result[field_name] = tuple(values)
    return result


def merge_businesses(businesses: list[Business]) -> Business:
    ranked = sorted(businesses, key=lambda item: _SOURCE_PRIORITY.get(item.source, 99))
    primary = ranked[0]
    phones = _unique(
        [value for item in ranked for value in (item.phone, *item.phones) if value]
    )
    normalized_phones = _unique(
        [value for phone in phones if (value := normalize_phone(phone))]
    )
    emails = _unique(
        [
            value
            for item in ranked
            for email in (item.email, *item.emails)
            if email and (value := normalize_email(email))
        ]
    )
    websites = _unique(
        [
            value
            for item in ranked
            for website in (item.website, *item.websites)
            if website and (value := normalize_website_url(website))
        ]
    )
    socials = _unique([value for item in ranked for value in item.social_links])
    directories = _unique([value for item in ranked for value in item.directory_links])
    whatsapp_numbers = _unique(
        [value for item in ranked for value in item.whatsapp_numbers]
    )
    sources = tuple(dict.fromkeys(item.source for item in ranked))
    source_ids: dict[str, tuple[str, ...]] = {}
    for source in sources:
        source_ids[source] = _unique(
            [
                source_id
                for item in ranked
                for source_id in (
                    item.source_ids.get(source, ())
                    or ((item.source_id,) if item.source == source else ())
                )
            ]
        )
    identity = "|".join(
        f"{source}:{source_id}"
        for source in sorted(source_ids)
        for source_id in sorted(source_ids[source])
    )
    lead_id = "lead:" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
    confidence_values = [item.confidence for item in ranked if item.confidence is not None]
    return replace(
        primary,
        lead_id=lead_id,
        address=_merged_address(ranked),
        category=next((item.category for item in ranked if item.category), None),
        subcategories=_unique([value for item in ranked for value in item.subcategories]),
        latitude=next((item.latitude for item in ranked if item.latitude is not None), None),
        longitude=next((item.longitude for item in ranked if item.longitude is not None), None),
        phone=phones[0] if phones else None,
        phones=phones,
        normalized_phones=normalized_phones,
        email=emails[0] if emails else None,
        emails=emails,
        website=websites[0] if websites else None,
        websites=websites,
        website_status="listed" if websites else "not_found",
        website_type="official" if websites else "none",
        directory_links=directories,
        social_links=socials,
        whatsapp_number=whatsapp_numbers[0] if whatsapp_numbers else None,
        whatsapp_numbers=whatsapp_numbers,
        opening_hours=next(
            (item.opening_hours for item in ranked if item.opening_hours), None
        ),
        confidence=max(confidence_values) if confidence_values else None,
        sources=sources,
        source_ids=source_ids,
        field_provenance=_merged_provenance(ranked),
        operating_status=next(
            (item.operating_status for item in ranked if item.operating_status), None
        ),
        raw_tags={},
    )


def _identity_representatives(group: list[Business]) -> tuple[Business, ...]:
    representatives: dict[tuple[str, str], Business] = {}
    for member in group:
        representatives.setdefault((member.source, member.source_id), member)
    return tuple(representatives.values())


def _blocking_keys(business: Business) -> tuple[str, ...]:
    keys: set[str] = set()
    name = normalize_business_name(business.name)
    if name:
        keys.add(f"name:{name}")
    address = " ".join(re.findall(r"[a-z0-9]+", _address_text(business)))
    if address:
        keys.add(f"address:{address}")
    keys.update(f"phone:{value}" for value in _phone_values(business))
    keys.update(f"domain:{value}" for value in _website_domains(business))
    if business.latitude is not None and business.longitude is not None:
        latitude_bucket = math.floor(float(business.latitude) / 0.003)
        longitude_bucket = math.floor(float(business.longitude) / 0.003)
        for latitude_offset in (-1, 0, 1):
            for longitude_offset in (-1, 0, 1):
                keys.add(
                    f"geo:{latitude_bucket + latitude_offset}:"
                    f"{longitude_bucket + longitude_offset}"
                )
    return tuple(keys)


def deduplicate_businesses(businesses: list[Business]) -> list[Business]:
    groups: list[list[Business]] = []
    blocks: dict[str, set[int]] = {}
    for business in businesses:
        candidate_groups = sorted(
            {
                group_index
                for key in _blocking_keys(business)
                for group_index in blocks.get(key, ())
            }
        )
        match_index = next(
            (
                group_index
                for group_index in candidate_groups
                if all(
                    businesses_match(business, item)
                    for item in _identity_representatives(groups[group_index])
                )
            ),
            None,
        )
        if match_index is None:
            match_index = len(groups)
            groups.append([business])
        else:
            groups[match_index].append(business)
        for key in _blocking_keys(business):
            blocks.setdefault(key, set()).add(match_index)
    return [merge_businesses(group) for group in groups]
