import { apiBlobRequest, apiRequest } from "@/lib/api/client";
import type {
  CategoriesResponse,
  Business,
  BusinessEnrichment,
  DiscoverBusinessesRequest,
  DiscoverBusinessesResponse,
  EnrichSearchSessionResponse,
  SearchFilter,
} from "@/types/business";

export function getBusinessCategories(): Promise<CategoriesResponse> {
  return apiRequest<CategoriesResponse>("/api/v1/categories");
}

export function discoverBusinesses(
  request: DiscoverBusinessesRequest,
): Promise<DiscoverBusinessesResponse> {
  return apiRequest<DiscoverBusinessesResponse>("/api/v1/businesses/discover", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export function enrichBusiness(business: Business): Promise<BusinessEnrichment> {
  return apiRequest<BusinessEnrichment>("/api/v1/businesses/enrich", {
    method: "POST",
    body: JSON.stringify({ business }),
  });
}

export function enrichBusinesses(businesses: Business[]): Promise<{ results: BusinessEnrichment[] }> {
  return apiRequest<{ results: BusinessEnrichment[] }>("/api/v1/businesses/enrich-batch", {
    method: "POST",
    body: JSON.stringify({ businesses }),
  });
}

export function getSearchSession(
  sessionId: string,
  page: number,
  pageSize: number,
  filter: SearchFilter,
): Promise<DiscoverBusinessesResponse> {
  const parameters = new URLSearchParams({
    page: String(page),
    pageSize: String(pageSize),
    filter,
  });
  return apiRequest<DiscoverBusinessesResponse>(
    `/api/v1/businesses/search-sessions/${encodeURIComponent(sessionId)}?${parameters}`,
  );
}

export function enrichSearchSession(
  sessionId: string,
  options: { leadIds?: string[]; batchSize?: number; retryFailed?: boolean } = {},
): Promise<EnrichSearchSessionResponse> {
  return apiRequest<EnrichSearchSessionResponse>(
    `/api/v1/businesses/search-sessions/${encodeURIComponent(sessionId)}/enrich`,
    {
      method: "POST",
      body: JSON.stringify(options),
    },
  );
}

export function downloadSearchSessionExcel(
  sessionId: string,
  filter: SearchFilter,
): Promise<{ blob: Blob; filename: string | null }> {
  const parameters = new URLSearchParams({ filter });
  return apiBlobRequest(
    `/api/v1/businesses/search-sessions/${encodeURIComponent(sessionId)}/export?${parameters}`,
  );
}

export function downloadBusinessesExcel(
  businesses: Business[],
  searchLabel: string,
): Promise<{ blob: Blob; filename: string | null }> {
  return apiBlobRequest("/api/v1/businesses/export", {
    method: "POST",
    body: JSON.stringify({ businesses, searchLabel }),
  });
}
