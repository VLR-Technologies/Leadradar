import { apiRequest } from "@/lib/api/client";
import type {
  CategoriesResponse,
  Business,
  BusinessEnrichment,
  DiscoverBusinessesRequest,
  DiscoverBusinessesResponse,
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
