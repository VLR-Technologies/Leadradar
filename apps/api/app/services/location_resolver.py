from app.core.locations import (
    CityDefinition,
    CountryDefinition,
    RegionDefinition,
    get_country,
)
from app.models.location import ResolvedLocation


class LocationValidationError(ValueError):
    pass


class UnsupportedCountryError(LocationValidationError):
    pass


class RegionRequiredError(LocationValidationError):
    pass


class UnsupportedRegionError(LocationValidationError):
    pass


class CityRegionMismatchError(LocationValidationError):
    pass


class AmbiguousCityError(LocationValidationError):
    pass


class UnsupportedCityError(LocationValidationError):
    pass


def _unique_names(*values: str) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = value.strip()
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return tuple(result)


def _find_region(
    country: CountryDefinition,
    value: str,
) -> RegionDefinition | None:
    key = value.strip().casefold()
    return next(
        (
            region
            for region in country.regions
            if key
            in {
                region.name.casefold(),
                *(alias.casefold() for alias in region.aliases),
            }
        ),
        None,
    )


def _find_city(
    country: CountryDefinition,
    city: str,
    region: str | None,
) -> CityDefinition | None:
    city_key = city.strip().casefold()
    candidates = [
        item
        for item in country.cities
        if region is None
        or item.region is None
        or item.region.casefold() == region.casefold()
    ]
    matches = [
        item
        for item in candidates
        if city_key
        in {
                item.name.casefold(),
                *(alias.casefold() for alias in item.aliases),
        }
    ]
    return max(matches, key=lambda item: item.population, default=None)


class LocationResolver:
    def resolve(
        self,
        *,
        country_code: str,
        city: str,
        region: str | None = None,
    ) -> ResolvedLocation:
        normalized_code = country_code.strip().upper()
        country = get_country(normalized_code)
        if country is None:
            raise UnsupportedCountryError(
                f"Country is not available in this release: {normalized_code}"
            )

        requested_region = region.strip() if region else None
        if country.requires_region and not requested_region:
            raise RegionRequiredError(f"Region is required for {country.name} searches.")

        region_definition = (
            _find_region(country, requested_region) if requested_region else None
        )
        if country.requires_region and requested_region and region_definition is None:
            raise UnsupportedRegionError(
                f"Unsupported region for {country.name}: {requested_region}"
            )

        resolved_region = region_definition.name if region_definition else requested_region
        if resolved_region is None:
            city_key = city.strip().casefold()
            matching_regions = {
                item.region
                for item in country.cities
                if item.region
                and city_key
                in {
                    item.name.casefold(),
                    *(alias.casefold() for alias in item.aliases),
                }
            }
            if len(matching_regions) > 1:
                choices = ", ".join(sorted(matching_regions))
                raise AmbiguousCityError(
                    f"{city.strip()} exists in multiple states ({choices}). Select a city suggestion with its state."
                )
        city_definition = _find_city(country, city, resolved_region)

        if city_definition is None:
            known_city = _find_city(country, city, None)
            if (
                known_city
                and known_city.region
                and resolved_region
                and known_city.region.casefold() != resolved_region.casefold()
            ):
                raise CityRegionMismatchError(
                    f"{known_city.name} is catalogued in {known_city.region}, "
                    f"not {resolved_region}."
                )
            if country.code == "IN":
                raise UnsupportedCityError(
                    f"City is not available in the bundled India location index: {city.strip()}"
                )

        resolved_city = city_definition.name if city_definition else city.strip()
        if resolved_region is None and city_definition is not None:
            resolved_region = city_definition.region
        city_query_names = _unique_names(
            resolved_city,
            *(city_definition.aliases if city_definition else ()),
            *(city_definition.osm_names if city_definition else ()),
        )
        region_query_names = (
            _unique_names(
                resolved_region,
                *(region_definition.aliases if region_definition else ()),
            )
            if resolved_region
            else ()
        )

        return ResolvedLocation(
            country_code=country.code,
            country=country.name,
            region=resolved_region,
            city=resolved_city,
            region_query_names=region_query_names,
            city_query_names=city_query_names,
            boundary_relation_ids=(
                city_definition.boundary_relation_ids if city_definition else ()
            ),
            bounding_box=(city_definition.bounding_box if city_definition else None),
        )
