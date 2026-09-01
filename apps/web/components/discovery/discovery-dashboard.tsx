"use client";

import {
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Database,
  Download,
  Filter,
  LoaderCircle,
  Radar,
  SearchX,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { BusinessDetailDrawer } from "@/components/discovery/business-detail-drawer";
import { BusinessTable } from "@/components/discovery/business-table";
import { ResultSummary } from "@/components/discovery/result-summary";
import { SearchPanel } from "@/components/discovery/search-panel";
import {
  discoverBusinesses,
  downloadSearchSessionExcel,
  enrichSearchSession,
  getBusinessCategories,
  getSearchSession,
} from "@/lib/api/businesses";
import { ApiError } from "@/lib/api/client";
import { recordCallDecision } from "@/lib/api/calls";
import { getCities, getCountries, getRegions as getLocationRegions } from "@/lib/api/locations";
import type {
  Business,
  BusinessCategory,
  DiscoverBusinessesRequest,
  DiscoverBusinessesResponse,
  SearchFilter,
} from "@/types/business";
import type { CityOption, CountryOption, RegionOption } from "@/types/location";

const initialRequest: DiscoverBusinessesRequest = {
  countryCode: "IN",
  region: "Telangana",
  city: "Hyderabad",
  category: "Dentist",
  limit: 100,
  pageSize: 50,
};

const FILTERS: { value: SearchFilter; label: string }[] = [
  { value: "all", label: "All leads" },
  { value: "phone", label: "Phone available" },
  { value: "email", label: "Email available" },
  { value: "official_website", label: "Official website" },
  { value: "no_official_website", label: "No official website" },
  { value: "directory_social_only", label: "Directory/social only" },
  { value: "opportunity_high", label: "High opportunity" },
  { value: "opportunity_medium", label: "Medium opportunity" },
  { value: "opportunity_low", label: "Low opportunity" },
  { value: "enrichment_pending", label: "Enrichment pending" },
  { value: "enrichment_complete", label: "Enrichment complete" },
];

function businessKey(business: Business): string {
  return business.leadId ?? business.sourceId;
}

function pageNumbers(current: number, total: number): (number | "ellipsis")[] {
  if (total <= 7) return Array.from({ length: total }, (_, index) => index + 1);
  const values = new Set([1, total, current - 1, current, current + 1]);
  const ordered = [...values].filter((value) => value >= 1 && value <= total).sort((a, b) => a - b);
  const result: (number | "ellipsis")[] = [];
  ordered.forEach((value, index) => {
    if (index && value - ordered[index - 1] > 1) result.push("ellipsis");
    result.push(value);
  });
  return result;
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
  const [pageLoading, setPageLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [leadFilter, setLeadFilter] = useState<SearchFilter>("all");
  const [exporting, setExporting] = useState(false);
  const [batchEnriching, setBatchEnriching] = useState(false);
  const [enrichingSourceIds, setEnrichingSourceIds] = useState<Set<string>>(new Set());
  const [enrichmentErrors, setEnrichmentErrors] = useState<Record<string, string>>({});
  const [decisions, setDecisions] = useState<Record<string, "yes" | "no">>({});
  const locationRequestId = useRef(0);

  useEffect(() => {
    let active = true;
    Promise.all([getBusinessCategories(), getCountries(), getCities("IN")])
      .then(([categoryResponse, countryResponse, cityResponse]) => {
        if (!active) return;
        setCategories(categoryResponse.categories);
        setCountries(countryResponse.filter((country) => country.code === "IN"));
        setCities(cityResponse);
      })
      .catch((caught: unknown) => {
        if (active) setError(caught instanceof ApiError ? caught.message : "Discovery options could not be loaded.");
      })
      .finally(() => {
        if (active) setMetadataLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const closeDetails = useCallback(() => setSelectedBusiness(null), []);
  const selectedCountry = countries.find((country) => country.code === values.countryCode);

  async function handleCountryChange(countryCode: string) {
    const requestId = ++locationRequestId.current;
    const country = countries.find((item) => item.code === countryCode);
    setLocationOptionsLoading(true);
    setResult(null);
    setRegions([]);
    setCities([]);
    setValues((current) => ({ ...current, countryCode, region: null, city: "" }));
    try {
      if (country?.requiresRegion) {
        const regionOptions = await getLocationRegions(countryCode);
        const region = regionOptions[0]?.name ?? null;
        const cityOptions = region ? await getCities(countryCode, region) : [];
        if (requestId !== locationRequestId.current) return;
        setRegions(regionOptions);
        setCities(cityOptions);
        setValues((current) => ({ ...current, countryCode, region, city: cityOptions[0]?.name ?? "" }));
      } else {
        const cityOptions = await getCities(countryCode);
        if (requestId !== locationRequestId.current) return;
        setCities(cityOptions);
        const preferred = cityOptions.find((city) => city.name === "Hyderabad") ?? cityOptions[0];
        setValues((current) => ({
          ...current,
          countryCode,
          region: preferred?.region ?? null,
          city: preferred?.name ?? "",
        }));
      }
    } catch (caught: unknown) {
      if (requestId === locationRequestId.current) setError(caught instanceof ApiError ? caught.message : "Locations could not be loaded.");
    } finally {
      if (requestId === locationRequestId.current) setLocationOptionsLoading(false);
    }
  }

  async function handleRegionChange(region: string) {
    const requestId = ++locationRequestId.current;
    setLocationOptionsLoading(true);
    setValues((current) => ({ ...current, region, city: "" }));
    try {
      const cityOptions = await getCities(values.countryCode, region);
      if (requestId !== locationRequestId.current) return;
      setCities(cityOptions);
      setValues((current) => ({ ...current, region, city: cityOptions[0]?.name ?? "" }));
    } catch (caught: unknown) {
      if (requestId === locationRequestId.current) setError(caught instanceof ApiError ? caught.message : "Cities could not be loaded.");
    } finally {
      if (requestId === locationRequestId.current) setLocationOptionsLoading(false);
    }
  }

  async function loadPage(
    sessionId: string,
    page: number,
    pageSize: number,
    filter: SearchFilter,
  ) {
    setPageLoading(true);
    setError(null);
    try {
      const response = await getSearchSession(sessionId, page, pageSize, filter);
      setResult(response);
      setSelectedBusiness((selected) =>
        selected
          ? response.businesses.find((business) => businessKey(business) === businessKey(selected)) ?? null
          : null,
      );
    } catch (caught: unknown) {
      setError(caught instanceof ApiError ? caught.message : "This results page could not be loaded.");
    } finally {
      setPageLoading(false);
    }
  }

  async function runEnrichment(sessionId: string, page = 1, filter: SearchFilter = "all") {
    setBatchEnriching(true);
    try {
      await enrichSearchSession(sessionId, { batchSize: 10 });
      await loadPage(sessionId, page, values.pageSize, filter);
    } catch (caught: unknown) {
      setError(caught instanceof ApiError ? caught.message : "The enrichment batch could not finish.");
    } finally {
      setBatchEnriching(false);
    }
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    setSelectedBusiness(null);
    setLeadFilter("all");
    setEnrichmentErrors({});
    setDecisions({});
    try {
      const discovered = await discoverBusinesses(values);
      setResult(discovered);
      setLoading(false);
      void runEnrichment(discovered.sessionId);
    } catch (caught: unknown) {
      setError(caught instanceof ApiError ? caught.message : "Unable to reach the business data providers.");
    } finally {
      setLoading(false);
    }
  }

  async function handleFilterChange(filter: SearchFilter) {
    setLeadFilter(filter);
    if (result) await loadPage(result.sessionId, 1, result.pageSize, filter);
  }

  async function handlePageSizeChange(pageSize: number) {
    setValues((current) => ({ ...current, pageSize }));
    if (result) await loadPage(result.sessionId, 1, pageSize, leadFilter);
  }

  async function handleExport() {
    if (!result || result.totalCount === 0) return;
    setExporting(true);
    setError(null);
    try {
      const { blob, filename } = await downloadSearchSessionExcel(result.sessionId, leadFilter);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename ?? "leadradar-leads.xlsx";
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (caught: unknown) {
      setError(caught instanceof ApiError ? caught.message : "The Excel export could not be downloaded.");
    } finally {
      setExporting(false);
    }
  }

  function handleDecision(business: Business, value: "yes" | "no") {
    const key = businessKey(business);
    const isClearing = decisions[key] === value;
    setDecisions((current) =>
      current[key] === value
        ? Object.fromEntries(
            Object.entries(current).filter(([item]) => item !== key),
          )
        : { ...current, [key]: value },
    );
    if (!isClearing) {
      void recordCallDecision({
        lead_key: key,
        business_name: business.name ?? "",
        phone: business.phone ?? "",
        decision: value,
      }).catch((caught) => {
        console.error("Could not record call decision", caught);
      });
    }
  }

  async function handleEnrich(business: Business) {
    if (!result) return;
    const key = businessKey(business);
    setEnrichingSourceIds((current) => new Set(current).add(key));
    try {
      await enrichSearchSession(result.sessionId, {
        leadIds: business.leadId ? [business.leadId] : undefined,
        batchSize: 1,
        retryFailed: true,
      });
      await loadPage(result.sessionId, result.page, result.pageSize, leadFilter);
    } catch (caught: unknown) {
      setEnrichmentErrors((current) => ({
        ...current,
        [key]: caught instanceof ApiError ? caught.message : "This lead could not be enriched.",
      }));
    } finally {
      setEnrichingSourceIds((current) => {
        const next = new Set(current);
        next.delete(key);
        return next;
      });
    }
  }

  const showingStart = result && result.totalCount ? (result.page - 1) * result.pageSize + 1 : 0;
  const showingEnd = result ? Math.min(result.page * result.pageSize, result.totalCount) : 0;

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-[#dce5e0] bg-white/92 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-[1480px] items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-xl bg-[#177454] text-white shadow-[0_5px_14px_rgba(23,116,84,0.2)]"><Radar className="size-5" /></div>
            <div><p className="text-[15px] font-bold text-[#17211d]">Lead Radar</p><p className="text-[10px] font-semibold tracking-[0.08em] text-[#7b8780] uppercase">VLR Technologies</p></div>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-[#dae5df] bg-[#f8faf9] px-3 py-1.5 text-xs font-semibold text-[#536159]"><span className="size-2 rounded-full bg-[#2ca475]" />Session-based discovery</div>
        </div>
      </header>

      <main className="mx-auto max-w-[1480px] px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-7 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="mb-3 text-xs font-bold tracking-[0.09em] text-[#177454] uppercase">Business Discovery</p>
            <h1 className="text-3xl font-semibold tracking-[-0.04em] text-[#15201b] sm:text-[38px]">Discover businesses with <span className="text-[#177454]">digital opportunities.</span></h1>
            <p className="mt-3 max-w-2xl text-[15px] leading-6 text-[#647169]">Search open India-wide listings, inspect official presence, and export every filtered result—not only the visible page.</p>
          </div>
          <div className="hidden items-center gap-6 lg:flex"><span className="flex items-center gap-2 text-xs font-semibold text-[#65726b]"><ShieldCheck className="size-4 text-[#177454]" />Permitted public data</span><span className="flex items-center gap-2 text-xs font-semibold text-[#65726b]"><Database className="size-4 text-[#177454]" />Expiring memory only</span></div>
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

        {loading ? <div className="mt-5 flex items-center gap-3 rounded-xl border border-[#cfe4da] bg-[#f1faf6] px-4 py-3 text-sm font-medium text-[#2b634d]" role="status"><Radar className="size-4 animate-pulse" />Searching Overture Maps and OpenStreetMap in {values.city}…</div> : null}
        {error ? <div className="mt-5 flex items-start gap-3 rounded-xl border border-[#efd6d2] bg-[#fff7f5] px-4 py-3.5 text-sm text-[#873f35]" role="alert"><AlertCircle className="mt-0.5 size-4 shrink-0" /><div><p className="font-semibold">Request could not be completed</p><p className="mt-0.5">{error}</p></div></div> : null}
        {result?.warnings.map((warning) => <div key={warning} className="mt-3 rounded-xl border border-[#eadfbf] bg-[#fffaf0] px-4 py-3 text-sm font-medium text-[#765b25]">{warning}</div>)}

        {result ? (
          <div className="mt-8 space-y-6">
            <ResultSummary summary={result.summary} query={result.query} decisions={decisions} />
            <div className="grid gap-3 lg:grid-cols-2">
              {result.providers.map((provider) => (
                <div key={provider.provider} className="rounded-xl border border-[#dfe7e3] bg-white px-4 py-3 text-sm">
                  <div className="flex items-center justify-between"><span className="font-semibold text-[#2f3e36]">{provider.displayName}</span><span className="rounded-full bg-[#edf7f2] px-2.5 py-1 text-xs font-semibold text-[#176846]">{provider.status}</span></div>
                  <p className="mt-1 text-xs text-[#748078]">Raw {provider.count.toLocaleString()} · accepted {provider.acceptedCount.toLocaleString()} · {provider.durationMs.toLocaleString()} ms</p>
                </div>
              ))}
            </div>
            <div className="flex flex-col gap-3 rounded-2xl border border-[#dfe7e3] bg-white p-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="flex flex-wrap items-center gap-3">
                <label className="flex items-center gap-2 text-sm font-semibold text-[#425149]"><Filter className="size-4 text-[#177454]" />Filter<select value={leadFilter} onChange={(event) => void handleFilterChange(event.target.value as SearchFilter)} className="h-10 rounded-lg border border-[#d8e2dd] bg-white px-3 text-sm font-medium">{FILTERS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
                <label className="text-sm font-semibold text-[#425149]">Rows<select value={result.pageSize} onChange={(event) => void handlePageSizeChange(Number(event.target.value))} className="ml-2 h-10 rounded-lg border border-[#d8e2dd] bg-white px-3 text-sm font-medium">{[25, 50, 100].map((size) => <option key={size}>{size}</option>)}</select></label>
                <span className="text-xs font-medium text-[#748078]">Showing {showingStart.toLocaleString()}–{showingEnd.toLocaleString()} of {result.totalCount.toLocaleString()}</span>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-[#edf7f2] px-3 py-1.5 text-xs font-semibold text-[#176846]">{batchEnriching ? <LoaderCircle className="size-3.5 animate-spin" /> : null}Enrichment {result.enrichmentProgress.processed}/{result.enrichmentProgress.total}</span>
              </div>
              <div className="flex flex-wrap gap-2">
                <button type="button" onClick={() => void runEnrichment(result.sessionId, result.page, leadFilter)} disabled={batchEnriching || result.enrichmentProgress.pending === 0} className="inline-flex h-10 items-center gap-2 rounded-xl border border-[#bcd8ca] px-4 text-sm font-semibold text-[#176846] disabled:opacity-50"><Sparkles className="size-4" />Continue enrichment</button>
                <button type="button" onClick={handleExport} disabled={exporting || result.totalCount === 0} className="inline-flex h-10 items-center gap-2 rounded-xl bg-[#177454] px-4 text-sm font-semibold text-white disabled:bg-[#91aaa0]">{exporting ? <LoaderCircle className="size-4 animate-spin" /> : <Download className="size-4" />}Download all filtered</button>
              </div>
            </div>

            {pageLoading ? <div className="flex justify-center py-12" role="status"><LoaderCircle className="size-6 animate-spin text-[#177454]" /><span className="sr-only">Loading page</span></div> : result.businesses.length ? <BusinessTable businesses={result.businesses} enrichingSourceIds={enrichingSourceIds} enrichmentErrors={enrichmentErrors} decisions={decisions} onSelect={setSelectedBusiness} onEnrich={handleEnrich} onDecision={handleDecision} /> : <div className="rounded-2xl border border-dashed border-[#cfdad4] bg-white px-6 py-12 text-center"><SearchX className="mx-auto size-6 text-[#738078]" /><p className="mt-3 font-semibold">No businesses match this filter.</p></div>}

            {result.totalPages > 1 ? (
              <nav aria-label="Results pagination" className="flex flex-wrap items-center justify-center gap-1.5">
                <button type="button" aria-label="Previous page" disabled={result.page === 1 || pageLoading} onClick={() => void loadPage(result.sessionId, result.page - 1, result.pageSize, leadFilter)} className="flex size-9 items-center justify-center rounded-lg border border-[#d8e2dd] bg-white disabled:opacity-40"><ChevronLeft className="size-4" /></button>
                {pageNumbers(result.page, result.totalPages).map((item, index) => item === "ellipsis" ? <span key={`ellipsis-${index}`} className="px-1 text-[#748078]">…</span> : <button type="button" key={item} aria-current={item === result.page ? "page" : undefined} onClick={() => void loadPage(result.sessionId, item, result.pageSize, leadFilter)} className={`size-9 rounded-lg border text-sm font-semibold ${item === result.page ? "border-[#177454] bg-[#177454] text-white" : "border-[#d8e2dd] bg-white text-[#536159]"}`}>{item}</button>)}
                <button type="button" aria-label="Next page" disabled={result.page >= result.totalPages || pageLoading} onClick={() => void loadPage(result.sessionId, result.page + 1, result.pageSize, leadFilter)} className="flex size-9 items-center justify-center rounded-lg border border-[#d8e2dd] bg-white disabled:opacity-40"><ChevronRight className="size-4" /></button>
              </nav>
            ) : null}
            <p className="text-center text-xs leading-5 text-[#78857e]">Session expires at {new Date(result.expiresAt).toLocaleTimeString()}. “All available” means up to the configured safety cap, not a complete census.</p>
          </div>
        ) : null}

        {!result && !loading ? <section className="mt-8 rounded-2xl border border-[#dce6e1] bg-[#163e30] p-7 text-white"><h2 className="text-xl font-semibold">One clean view of the fields that matter first.</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-[#c9ddd4]">Lead Radar combines Overture Maps with OpenStreetMap, preserves provenance, and never treats missing source data as proof of absence.</p></section> : null}
      </main>
      <BusinessDetailDrawer business={selectedBusiness} onClose={closeDetails} />
    </div>
  );
}
