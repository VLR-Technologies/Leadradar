import { apiRequest } from "@/lib/api/client";
import type { CityOption, CountryOption, RegionOption } from "@/types/location";

export function getCountries(): Promise<CountryOption[]> {
  return apiRequest<CountryOption[]>("/api/v1/locations/countries");
}

export function getRegions(countryCode: string): Promise<RegionOption[]> {
  const parameters = new URLSearchParams({ countryCode });
  return apiRequest<RegionOption[]>(`/api/v1/locations/regions?${parameters}`);
}

export function getCities(
  countryCode: string,
  region?: string | null,
): Promise<CityOption[]> {
  const parameters = new URLSearchParams({ countryCode });
  if (region) parameters.set("region", region);
  return apiRequest<CityOption[]>(`/api/v1/locations/cities?${parameters}`);
}
