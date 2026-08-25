export type BusinessSource = "openstreetmap";
export type ProvenanceSource = "openstreetmap" | "official_website" | "search_provider";
export type EnrichmentConfidence = "high" | "medium" | "low";
export type EnrichmentStatus =
  | "not_started"
  | "in_progress"
  | "completed"
  | "partial"
  | "no_data"
  | "failed";
export type EnrichmentReasonCode =
  | "ADDITIONAL_CONTACTS_FOUND"
  | "PARTIAL_CONTACTS_FOUND"
  | "WEBSITE_VERIFIED"
  | "SEARCH_PROVIDER_DISABLED"
  | "NO_WEBSITE_AVAILABLE"
  | "NO_CONTACT_DETAILS_FOUND"
  | "WEBSITE_MISMATCH"
  | "WEBSITE_TIMEOUT"
  | "WEBSITE_UNREACHABLE"
  | "WEBSITE_ACCESS_DENIED"
  | "DNS_ERROR"
  | "INVALID_URL"
  | "PARSER_ERROR"
  | "PROVIDER_ERROR";
export type WebsiteVerificationStatus =
  | "source_listed"
  | "verified"
  | "unreachable"
  | "mismatch"
  | "unknown";

export interface FieldProvenance {
  value: string;
  source: ProvenanceSource;
  confidence: EnrichmentConfidence;
}

export interface EnrichedField {
  primary: FieldProvenance | null;
  alternatives: FieldProvenance[];
}

export interface BusinessEnrichment {
  sourceId: string;
  status: EnrichmentStatus;
  websiteStatus: WebsiteVerificationStatus;
  fields: {
    phone: EnrichedField;
    email: EnrichedField;
    website: EnrichedField;
  };
  reasonCode: EnrichmentReasonCode | null;
  message: string | null;
  visitedPages: string[];
}

export interface BusinessAddress {
  street: string | null;
  houseNumber: string | null;
  postcode: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  formatted: string | null;
}

export interface Business {
  sourceId: string;
  source: BusinessSource;
  name: string;
  category: string | null;
  address: BusinessAddress;
  latitude: number | null;
  longitude: number | null;
  phone: string | null;
  email: string | null;
  website: string | null;
  openingHours: string | null;
  enrichment?: BusinessEnrichment;
}

export interface BusinessCategory {
  id: string;
  label: string;
}

export interface DiscoverBusinessesRequest {
  countryCode: string;
  region: string | null;
  city: string;
  category: string;
  limit: number;
}

export interface DiscoveryQuery extends DiscoverBusinessesRequest {
  country: string;
}

export interface DiscoverBusinessesResponse {
  query: DiscoveryQuery;
  count: number;
  businesses: Business[];
}

export interface CategoriesResponse {
  categories: BusinessCategory[];
}

export interface EnrichBusinessRequest {
  business: Business;
}
