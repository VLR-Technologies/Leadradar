"use client";

import { AlertCircle, Database, Radar, SearchX, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { BusinessDetailDrawer } from "@/components/discovery/business-detail-drawer";
import { BusinessTable } from "@/components/discovery/business-table";
import { ResultSummary } from "@/components/discovery/result-summary";
import { SearchPanel } from "@/components/discovery/search-panel";
import {
  discoverBusinesses,
  enrichBusiness,
  getBusinessCategories,
} from "@/lib/api/businesses";
import { ApiError } from "@/lib/api/client";
import {
  getCities,
  getCountries,
  getRegions as getLocationRegions,
} from "@/lib/api/locations";
import type {
  Business,
  BusinessCategory,
  BusinessEnrichment,
  DiscoverBusinessesRequest,
  DiscoverBusinessesResponse,
} from "@/types/business";
import type { CityOption, CountryOption, RegionOption } from "@/types/location";

const initialRequest: DiscoverBusinessesRequest = {
  countryCode: "DE",
  region: null,
  city: "Berlin",
  category: "Dentist",
  limit: 100,
};

const preferredCities: Record<string, string> = {
  DE: "Berlin",
  GB: "London",
  US: "San Francisco",
  IN: "Hyderabad",
};

function chooseCity(cities: CityOption[], countryCode: string): string {
  const preferredCity = preferredCities[countryCode];
  return cities.find((city) => city.name === preferredCity)?.name ?? cities[0]?.name ?? "";
}

function mergeEnrichment(
  business: Business,
  enrichment: BusinessEnrichment,
): Business {
  return {
    ...business,
    phone: enrichment.fields.phone.primary?.value ?? business.phone,
    email: enrichment.fields.email.primary?.value ?? business.email,
    website: enrichment.fields.website.primary?.value ?? business.website,
    enrichment,
  };
}

export function DiscoveryDashboard() {
  const [categories, setCategories] = useState<BusinessCategory[]>([]);
  const [countries, setCountries] = useState<CountryOption[]>([]);
  const [regions, setRegions] = useState<RegionOption[]>([]);
  const [cities, setCities] = useState<CityOption[]>([]);
  const [metadataLoading, setMetadataLoading] = useState(true);
  const [locationOptionsLoading, setLocationOptionsLoading] = useState(false);
  const [values, setValues] = useState(initialRequest);
  const [result, setResult] = useState<DiscoverBusinessesResponse | null>(null);
  const [selectedBusiness, setSelectedBusiness] = useState<Business | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [enrichingSourceIds, setEnrichingSourceIds] = useState<Set<string>>(
    new Set(),
  );
  const [enrichmentErrors, setEnrichmentErrors] = useState<Record<string, string>>({});
  const locationRequestId = useRef(0);

  useEffect(() => {
    let active = true;
    Promise.all([
      getBusinessCategories(),
      getCountries(),
      getCities(initialRequest.countryCode),
    ])
      .then(([categoryResponse, countryResponse, cityResponse]) => {
        if (!active) return;
        setCategories(categoryResponse.categories);
        setCountries(countryResponse);
        setCities(cityResponse);
        if (
          !categoryResponse.categories.some(
            (category) => category.label === initialRequest.category,
          )
        ) {
          setValues((current) => ({
            ...current,
            category: categoryResponse.categories[0]?.label ?? "",
          }));
        }
      })
      .catch((caught: unknown) => {
        if (!active) return;
        setError(
          caught instanceof ApiError
            ? caught.message
            : "Discovery options could not be loaded. Please refresh and try again.",
        );
      })
      .finally(() => {
        if (active) setMetadataLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const closeDetails = useCallback(() => setSelectedBusiness(null), []);
  const selectedCountry = countries.find(
    (country) => country.code === values.countryCode,
  );

  async function handleCountryChange(countryCode: string) {
    const requestId = ++locationRequestId.current;
    const country = countries.find((item) => item.code === countryCode);
    setLocationOptionsLoading(true);
    setError(null);
    setResult(null);
    setSelectedBusiness(null);
    setEnrichmentErrors({});
    setRegions([]);
    setCities([]);
    setValues((current) => ({
      ...current,
      countryCode,
      region: null,
      city: "",
    }));

    try {
      if (country?.requiresRegion) {
        const regionOptions = await getLocationRegions(countryCode);
        const region =
          regionOptions.find((item) => item.name === "California")?.name ??
          regionOptions[0]?.name ??
          null;
        const cityOptions = region ? await getCities(countryCode, region) : [];
        if (requestId !== locationRequestId.current) return;
        setRegions(regionOptions);
        setCities(cityOptions);
        setValues((current) => ({
          ...current,
          countryCode,
          region,
          city: chooseCity(cityOptions, countryCode),
        }));
      } else {
        const cityOptions = await getCities(countryCode);
        if (requestId !== locationRequestId.current) return;
        setCities(cityOptions);
        setValues((current) => ({
          ...current,
          countryCode,
          region: null,
          city: chooseCity(cityOptions, countryCode),
        }));
      }
    } catch (caught: unknown) {
      if (requestId !== locationRequestId.current) return;
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Location options could not be loaded. Please try another country.",
      );
    } finally {
      if (requestId === locationRequestId.current) {
        setLocationOptionsLoading(false);
      }
    }
  }

  async function handleRegionChange(region: string) {
    const requestId = ++locationRequestId.current;
    const countryCode = values.countryCode;
    setLocationOptionsLoading(true);
    setError(null);
    setResult(null);
    setSelectedBusiness(null);
    setEnrichmentErrors({});
    setCities([]);
    setValues((current) => ({ ...current, region, city: "" }));
    try {
      const cityOptions = await getCities(countryCode, region);
      if (requestId !== locationRequestId.current) return;
      setCities(cityOptions);
      setValues((current) => ({
        ...current,
        region,
        city: chooseCity(cityOptions, countryCode),
      }));
    } catch (caught: unknown) {
      if (requestId !== locationRequestId.current) return;
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Cities for this region could not be loaded. Please try again.",
      );
    } finally {
      if (requestId === locationRequestId.current) {
        setLocationOptionsLoading(false);
      }
    }
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setSelectedBusiness(null);
    setEnrichmentErrors({});
    try {
      setResult(await discoverBusinesses(values));
    } catch (caught: unknown) {
      setResult(null);
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Unable to reach the business data provider. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleEnrich(business: Business) {
    const sourceId = business.sourceId;
    setEnrichingSourceIds((current) => new Set(current).add(sourceId));
    setEnrichmentErrors((current) => {
      const next = { ...current };
      delete next[sourceId];
      return next;
    });
    try {
      const enrichment = await enrichBusiness(business);
      const enrichedBusiness = mergeEnrichment(business, enrichment);
      setResult((current) =>
        current
          ? {
              ...current,
              businesses: current.businesses.map((item) =>
                item.sourceId === sourceId ? enrichedBusiness : item,
              ),
            }
          : current,
      );
      setSelectedBusiness((current) =>
        current?.sourceId === sourceId ? enrichedBusiness : current,
      );
    } catch (caught: unknown) {
      setEnrichmentErrors((current) => ({
        ...current,
        [sourceId]:
          caught instanceof ApiError
            ? caught.message
            : "This lead could not be enriched. Try again later.",
      }));
    } finally {
      setEnrichingSourceIds((current) => {
        const next = new Set(current);
        next.delete(sourceId);
        return next;
      });
    }
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-[#dce5e0] bg-white/92 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-[1480px] items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="relative flex size-9 items-center justify-center overflow-hidden rounded-xl bg-[#177454] text-white shadow-[0_5px_14px_rgba(23,116,84,0.2)]">
              <Radar aria-hidden="true" className="size-5" strokeWidth={2} />
            </div>
            <div>
              <p className="text-[15px] font-bold tracking-[-0.02em] text-[#17211d]">Lead Radar</p>
              <p className="text-[10px] font-semibold tracking-[0.08em] text-[#7b8780] uppercase">VLR Technologies</p>
            </div>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-[#dae5df] bg-[#f8faf9] px-3 py-1.5 text-xs font-semibold text-[#536159]">
            <span className="size-2 rounded-full bg-[#2ca475] shadow-[0_0_0_3px_rgba(44,164,117,0.12)]" />
            Discovery + Enrichment
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1480px] px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
        <div className="mb-7 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="mb-3 text-xs font-bold tracking-[0.09em] text-[#177454] uppercase">Business Discovery</p>
            <h1 className="text-3xl font-semibold tracking-[-0.04em] text-[#15201b] sm:text-[38px] sm:leading-[1.12]">
              Discover businesses with
              <span className="text-[#177454]"> digital opportunities.</span>
            </h1>
            <p className="mt-3 max-w-2xl text-[15px] leading-6 text-[#647169] sm:text-base">
              Explore real business records across supported international markets, then enrich selected leads from their official websites.
            </p>
          </div>
          <div className="hidden items-center gap-6 pb-1 lg:flex">
            <div className="flex items-center gap-2 text-xs font-semibold text-[#65726b]"><ShieldCheck className="size-4 text-[#177454]" />Permitted public data</div>
            <div className="flex items-center gap-2 text-xs font-semibold text-[#65726b]"><Database className="size-4 text-[#177454]" />No data stored</div>
          </div>
        </div>

        <SearchPanel
          values={values}
          categories={categories}
          countries={countries}
          regions={regions}
          cities={cities}
          countryRequiresRegion={selectedCountry?.requiresRegion ?? false}
          metadataLoading={metadataLoading}
          locationOptionsLoading={locationOptionsLoading}
          loading={loading}
          onChange={setValues}
          onCountryChange={handleCountryChange}
          onRegionChange={handleRegionChange}
          onSubmit={handleSubmit}
        />

        {loading ? (
          <div className="mt-5 flex items-center gap-3 rounded-xl border border-[#cfe4da] bg-[#f1faf6] px-4 py-3 text-sm font-medium text-[#2b634d]" role="status">
            <Radar aria-hidden="true" className="size-4 animate-pulse" />
            Searching businesses in {values.city}… Overpass may take a few moments.
          </div>
        ) : null}

        {error ? (
          <div className="mt-5 flex items-start gap-3 rounded-xl border border-[#efd6d2] bg-[#fff7f5] px-4 py-3.5 text-sm text-[#873f35]" role="alert">
            <AlertCircle aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
            <div><p className="font-semibold">Discovery could not be completed</p><p className="mt-0.5 text-[#98594f]">{error}</p></div>
          </div>
        ) : null}

        {result && result.businesses.length > 0 ? (
          <div className="mt-8 space-y-6">
            <ResultSummary businesses={result.businesses} query={result.query} />
            <BusinessTable
              businesses={result.businesses}
              enrichingSourceIds={enrichingSourceIds}
              enrichmentErrors={enrichmentErrors}
              onSelect={setSelectedBusiness}
              onEnrich={handleEnrich}
            />
          </div>
        ) : null}

        {result && result.businesses.length === 0 ? (
          <div className="mt-8 rounded-2xl border border-dashed border-[#cfdad4] bg-white px-6 py-14 text-center">
            <div className="mx-auto flex size-12 items-center justify-center rounded-2xl bg-[#eef4f1] text-[#62736a]"><SearchX className="size-5" /></div>
            <h2 className="mt-4 text-lg font-semibold text-[#223029]">No businesses found for this search</h2>
            <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-[#6c7972]">Try a nearby city, another category, or a broader result limit. OpenStreetMap coverage varies by location.</p>
          </div>
        ) : null}

        {!result && !loading ? (
          <section className="mt-8 grid gap-4 lg:grid-cols-[1.5fr_1fr]">
            <div className="relative overflow-hidden rounded-2xl border border-[#dce6e1] bg-[#163e30] p-6 text-white shadow-[0_12px_34px_rgba(21,61,47,0.12)] sm:p-7">
              <div className="absolute -right-10 -bottom-20 size-64 rounded-full border border-white/10" />
              <div className="absolute right-5 -bottom-18 size-48 rounded-full border border-white/10" />
              <div className="relative max-w-xl">
                <span className="inline-flex items-center rounded-full bg-white/10 px-3 py-1.5 text-xs font-semibold text-[#d9eee5]">Source intelligence</span>
                <h2 className="mt-5 text-xl font-semibold tracking-[-0.025em]">One clean view of the fields that matter first.</h2>
                <p className="mt-2 text-sm leading-6 text-[#c9ddd4]">Lead Radar normalizes business identity, location, website, phone, and email from OpenStreetMap without treating missing source data as a verified absence.</p>
              </div>
            </div>
            <div className="rounded-2xl border border-[#dfe7e3] bg-white p-6">
              <p className="text-xs font-bold tracking-[0.08em] text-[#738078] uppercase">Current source</p>
              <div className="mt-4 flex items-center gap-3">
                <div className="flex size-11 items-center justify-center rounded-xl bg-[#eaf7f1] text-[#177454]"><Database className="size-5" /></div>
                <div><p className="font-semibold text-[#223029]">OpenStreetMap</p><p className="mt-0.5 text-xs text-[#738078]">Live via Overpass API</p></div>
              </div>
              <div className="mt-5 h-px bg-[#e6ece9]" />
              <p className="mt-4 text-xs leading-5 text-[#77837c]">Discovery stays fast. Official website inspection only runs when you choose Enrich for a lead.</p>
            </div>
          </section>
        ) : null}
      </main>

      <BusinessDetailDrawer business={selectedBusiness} onClose={closeDetails} />
    </div>
  );
}
