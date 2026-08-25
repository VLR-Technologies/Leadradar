from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResolvedLocation:
    country_code: str
    country: str
    region: str | None
    city: str
    region_query_names: tuple[str, ...]
    city_query_names: tuple[str, ...]
    boundary_relation_ids: tuple[int, ...] = ()

    @property
    def display_name(self) -> str:
        return ", ".join(
            part for part in (self.city, self.region, self.country) if part
        )
