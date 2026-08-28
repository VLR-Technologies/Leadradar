import { LoaderCircle, Search } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";

import { searchCities } from "@/lib/api/locations";
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
  const listboxId = useId();
  const requestId = useRef(0);
  const [suggestions, setSuggestions] = useState<CityOption[]>(cities);
  const [suggestionsOpen, setSuggestionsOpen] = useState(false);
  const [citySearchLoading, setCitySearchLoading] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  useEffect(() => {
    if (!values.city || values.city.length < 2) {
      return;
    }
    const currentRequest = ++requestId.current;
    const timer = window.setTimeout(() => {
      void searchCities(
        values.countryCode,
        values.city,
        countryRequiresRegion ? values.region : null,
      )
        .then((results) => {
          if (currentRequest !== requestId.current) return;
          setSuggestions(results);
          setActiveIndex(-1);
        })
        .catch(() => {
          if (currentRequest === requestId.current) setSuggestions([]);
        })
        .finally(() => {
          if (currentRequest === requestId.current) setCitySearchLoading(false);
        });
    }, 250);
    return () => window.clearTimeout(timer);
  }, [cities, countryRequiresRegion, values.city, values.countryCode, values.region]);

  const update = <Key extends keyof DiscoverBusinessesRequest>(
    key: Key,
    value: DiscoverBusinessesRequest[Key],
  ) => onChange({ ...values, [key]: value });

  function selectCity(city: CityOption) {
    onChange({ ...values, city: city.name, region: city.region });
    setSuggestionsOpen(false);
    setActiveIndex(-1);
    setCitySearchLoading(false);
  }

  function handleCityKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      setSuggestionsOpen(false);
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setSuggestionsOpen(true);
      setActiveIndex((current) => Math.min(current + 1, suggestions.length - 1));
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((current) => Math.max(current - 1, 0));
      return;
    }
    if (event.key === "Enter" && suggestionsOpen && activeIndex >= 0) {
      event.preventDefault();
      selectCity(suggestions[activeIndex]);
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      className="rounded-2xl border border-[#dfe7e3] bg-white p-5 shadow-[0_12px_38px_rgba(30,57,45,0.06)] sm:p-6"
    >
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold tracking-[-0.01em] text-[#18231e]">Search parameters</h2>
          <p className="mt-1 text-sm leading-5 text-[#68766f]">
            Search India-wide public listings. “All available” is bounded by the server safety cap.
          </p>
        </div>
        <span className="hidden rounded-full bg-[#edf7f2] px-3 py-1.5 text-xs font-semibold text-[#177454] sm:inline-flex">Overture + OSM</span>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-[0.7fr_1.25fr_1.1fr_0.72fr_auto] xl:items-end">
        <label className="block text-sm font-semibold text-[#3d4c45]">
          Country
          <select
            className={fieldClassName}
            value={values.countryCode}
            onChange={(event) => onCountryChange(event.target.value)}
            disabled={loading || metadataLoading}
            required
          >
            {countries.map((country) => <option key={country.code} value={country.code}>{country.name}</option>)}
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
              {regions.map((region) => <option key={region.name} value={region.name}>{region.name}</option>)}
            </select>
          </label>
        ) : null}

        <label className="relative block text-sm font-semibold text-[#3d4c45]">
          City
          <div className="relative">
            <input
              className={`${fieldClassName} pr-10`}
              value={values.city}
              onChange={(event) => {
                onChange({ ...values, city: event.target.value, region: null });
                setCitySearchLoading(event.target.value.length >= 2);
                setSuggestionsOpen(true);
              }}
              onFocus={() => setSuggestionsOpen(true)}
              onBlur={() => window.setTimeout(() => setSuggestionsOpen(false), 120)}
              onKeyDown={handleCityKeyDown}
              placeholder="Type at least 2 letters"
              role="combobox"
              aria-autocomplete="list"
              aria-expanded={suggestionsOpen}
              aria-controls={listboxId}
              aria-activedescendant={activeIndex >= 0 ? `${listboxId}-${activeIndex}` : undefined}
              required
              minLength={2}
              maxLength={120}
              disabled={loading || metadataLoading || locationOptionsLoading}
            />
            {citySearchLoading ? <LoaderCircle className="absolute top-6 right-3.5 size-4 animate-spin text-[#177454]" aria-label="Searching cities" /> : null}
          </div>
          {suggestionsOpen && values.city.length >= 2 ? (
            <ul
              id={listboxId}
              role="listbox"
              className="absolute z-30 mt-1 max-h-72 w-full overflow-y-auto rounded-xl border border-[#d8e2dd] bg-white p-1.5 shadow-[0_16px_40px_rgba(20,48,35,0.15)]"
            >
              {suggestions.map((city, index) => (
                <li
                  id={`${listboxId}-${index}`}
                  key={city.id ?? `${city.name}-${city.region}-${city.district}`}
                  role="option"
                  aria-selected={index === activeIndex}
                >
                  <button
                    type="button"
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => selectCity(city)}
                    className={`w-full rounded-lg px-3 py-2.5 text-left ${index === activeIndex ? "bg-[#edf7f2]" : "hover:bg-[#f5f8f6]"}`}
                  >
                    <span className="block text-sm font-semibold text-[#213129]">{city.name}</span>
                    <span className="mt-0.5 block text-xs font-medium text-[#728078]">{[city.district, city.region].filter(Boolean).join(", ")}</span>
                  </button>
                </li>
              ))}
              {!citySearchLoading && suggestions.length === 0 ? (
                <li className="px-3 py-3 text-xs font-medium text-[#748078]">No indexed India city matches. Choose a listed suggestion.</li>
              ) : null}
            </ul>
          ) : null}
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
            {categories.map((category) => <option key={category.id} value={category.label}>{category.label}</option>)}
          </select>
        </label>

        <label className="block text-sm font-semibold text-[#3d4c45]">
          Result limit
          <select
            className={fieldClassName}
            value={String(values.limit)}
            onChange={(event) => update("limit", event.target.value === "all" ? "all" : Number(event.target.value))}
            disabled={loading}
          >
            {[100, 200, 300, 400, 500].map((limit) => <option key={limit} value={limit}>{limit}</option>)}
            <option value="all">All available</option>
          </select>
        </label>

        <button
          type="submit"
          disabled={loading || metadataLoading || locationOptionsLoading || !values.region || categories.length === 0 || countries.length === 0}
          className="inline-flex h-12 items-center justify-center gap-2 rounded-xl bg-[#177454] px-5 text-sm font-semibold whitespace-nowrap text-white shadow-[0_7px_18px_rgba(23,116,84,0.2)] transition hover:bg-[#105f45] focus:ring-4 focus:ring-[#177454]/20 focus:outline-none disabled:cursor-not-allowed disabled:bg-[#91aaa0] disabled:shadow-none xl:min-w-33"
        >
          {loading ? <><LoaderCircle aria-hidden="true" className="size-4 animate-spin" />Searching</> : <><Search aria-hidden="true" className="size-4" strokeWidth={2.2} />Find leads</>}
        </button>
      </div>
    </form>
  );
}
