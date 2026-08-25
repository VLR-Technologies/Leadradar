import { LoaderCircle, Search } from "lucide-react";
import type { FormEvent } from "react";

import type { BusinessCategory, DiscoverBusinessesRequest } from "@/types/business";
import type { CityOption, CountryOption, RegionOption } from "@/types/location";

interface SearchPanelProps {
  values: DiscoverBusinessesRequest;
  categories: BusinessCategory[];
  countries: CountryOption[];
  regions: RegionOption[];
  cities: CityOption[];
  countryRequiresRegion: boolean;
  metadataLoading: boolean;
  locationOptionsLoading: boolean;
  loading: boolean;
  onChange: (values: DiscoverBusinessesRequest) => void;
  onCountryChange: (countryCode: string) => void;
  onRegionChange: (region: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}

const fieldClassName =
  "mt-2 h-12 w-full rounded-xl border border-[#d8e2dd] bg-white px-3.5 text-[15px] font-medium text-[#203029] shadow-[0_1px_1px_rgba(16,40,29,0.02)] transition placeholder:text-[#8b9892] hover:border-[#bdccc5] focus:border-[#177454] focus:ring-4 focus:ring-[#177454]/10 focus:outline-none disabled:cursor-not-allowed disabled:bg-[#f2f5f3]";

export function SearchPanel({
  values,
  categories,
  countries,
  regions,
  cities,
  countryRequiresRegion,
  metadataLoading,
  locationOptionsLoading,
  loading,
  onChange,
  onCountryChange,
  onRegionChange,
  onSubmit,
}: SearchPanelProps) {
  const update = <Key extends keyof DiscoverBusinessesRequest>(
    key: Key,
    value: DiscoverBusinessesRequest[Key],
  ) => onChange({ ...values, [key]: value });

  return (
    <form
      onSubmit={onSubmit}
      className="rounded-2xl border border-[#dfe7e3] bg-white p-5 shadow-[0_12px_38px_rgba(30,57,45,0.06)] sm:p-6"
    >
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold tracking-[-0.01em] text-[#18231e]">
            Search parameters
          </h2>
          <p className="mt-1 text-sm leading-5 text-[#68766f]">
            Define the market and business profile you want to explore.
          </p>
        </div>
        <span className="hidden rounded-full bg-[#edf7f2] px-3 py-1.5 text-xs font-semibold text-[#177454] sm:inline-flex">
          Live OSM data
        </span>
      </div>

      <div
        className={
          countryRequiresRegion
            ? "grid gap-4 md:grid-cols-2 xl:grid-cols-[0.8fr_1fr_1fr_1.15fr_0.7fr_auto] xl:items-end"
            : "grid gap-4 md:grid-cols-2 xl:grid-cols-[0.8fr_1fr_1.2fr_0.7fr_auto] xl:items-end"
        }
      >
        <label className="block text-sm font-semibold text-[#3d4c45]">
          Country
          <select
            className={fieldClassName}
            value={values.countryCode}
            onChange={(event) => onCountryChange(event.target.value)}
            disabled={loading || metadataLoading}
            required
          >
            {countries.map((country) => (
              <option key={country.code} value={country.code}>
                {country.name}
              </option>
            ))}
          </select>
        </label>

        {countryRequiresRegion ? (
          <label className="block text-sm font-semibold text-[#3d4c45]">
            Region / State
            <select
              className={fieldClassName}
              value={values.region ?? ""}
              onChange={(event) => onRegionChange(event.target.value)}
              disabled={loading || locationOptionsLoading || regions.length === 0}
              required
            >
              {regions.map((region) => (
                <option key={region.name} value={region.name}>
                  {region.name}
                </option>
              ))}
            </select>
          </label>
        ) : null}

        <label className="block text-sm font-semibold text-[#3d4c45]">
          City
          <input
            className={fieldClassName}
            list="lead-radar-city-options"
            value={values.city}
            onChange={(event) => update("city", event.target.value)}
            placeholder={locationOptionsLoading ? "Loading cities…" : "Search or enter a city"}
            required
            minLength={1}
            maxLength={120}
            disabled={loading || metadataLoading || locationOptionsLoading}
          />
          <datalist id="lead-radar-city-options">
            {cities.map((city) => (
              <option key={`${city.name}-${city.region ?? ""}`} value={city.name} />
            ))}
          </datalist>
        </label>

        <label className="block text-sm font-semibold text-[#3d4c45]">
          Business category
          <select
            className={fieldClassName}
            value={values.category}
            onChange={(event) => update("category", event.target.value)}
            disabled={loading || metadataLoading || categories.length === 0}
            required
          >
            {metadataLoading ? <option>Loading categories…</option> : null}
            {categories.map((category) => (
              <option key={category.id} value={category.label}>
                {category.label}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-sm font-semibold text-[#3d4c45]">
          Maximum results
          <input
            className={fieldClassName}
            type="number"
            inputMode="numeric"
            min={1}
            max={500}
            value={values.limit}
            onChange={(event) => update("limit", Number(event.target.value))}
            required
            disabled={loading}
          />
        </label>

        <button
          type="submit"
          disabled={
            loading ||
            metadataLoading ||
            locationOptionsLoading ||
            categories.length === 0 ||
            countries.length === 0 ||
            (countryRequiresRegion && !values.region)
          }
          className="inline-flex h-12 items-center justify-center gap-2 rounded-xl bg-[#177454] px-5 text-sm font-semibold whitespace-nowrap text-white shadow-[0_7px_18px_rgba(23,116,84,0.2)] transition hover:bg-[#105f45] focus:ring-4 focus:ring-[#177454]/20 focus:outline-none disabled:cursor-not-allowed disabled:bg-[#91aaa0] disabled:shadow-none xl:min-w-33"
        >
          {loading ? (
            <>
              <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
              Searching
            </>
          ) : (
            <>
              <Search aria-hidden="true" className="size-4" strokeWidth={2.2} />
              Find leads
            </>
          )}
        </button>
      </div>
    </form>
  );
}
