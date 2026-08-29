export type BusinessSource = "overture" | "openstreetmap";
export type ProvenanceSource =
  | "overture"
  | "openstreetmap"
  | "official_website"
  | "search_provider";
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
  sourceUrl: string | null;
  sourceType: string | null;
}

export type LeadWebsiteStatus =
  | "not_found"
  | "candidate"
  | "listed"
  | "verified"
  | "unreachable"
  | "mismatch"
  | "unknown";

export type OpportunityLevel = "High" | "Medium" | "Low";
export type WebsiteType =
  | "official"
  | "directory"
  | "social"
  | "candidate"
  | "unknown"
  | "none";

export interface WebsiteAudit {
  reachable: boolean | null;
  usesHttps: boolean | null;
  redirectBehavior: string | null;
  mobileViewport: boolean | null;
  contactPagePresent: boolean | null;
  emailPresent: boolean | null;
  phonePresent: boolean | null;
  socialLinksPresent: boolean | null;
  titlePresent: boolean | null;
  metaDescriptionPresent: boolean | null;
  brokenResponseCount: number;
  label: string;
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
    whatsapp: EnrichedField;
  };
  reasonCode: EnrichmentReasonCode | null;
  message: string | null;
  visitedPages: string[];
  socialLinks: string[];
  directoryLinks: string[];
  whatsappNumbers: string[];
  contactPageUrl: string | null;
  websiteAudit: WebsiteAudit | null;
  leadScore: number;
  opportunityLevel: OpportunityLevel;
  opportunityReasons: string[];
}

export interface BusinessAddress {
  street: string | null;
  houseNumber: string | null;
  postcode: string | null;
  locality: string | null;
  district: string | null;
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
  leadId: string | null;
  subcategories: string[];
  phones: string[];
  normalizedPhones: string[];
  emails: string[];
  websites: string[];
  websiteStatus: LeadWebsiteStatus;
  websiteType: WebsiteType;
  directoryLinks: string[];
  socialLinks: string[];
  whatsappNumber: string | null;
  whatsappNumbers: string[];
  rating: number | null;
  reviewCount: number | null;
  ratingSource: string | null;
  confidence: number | null;
  sources: BusinessSource[];
  sourceIds: Record<string, string[]>;
  fieldProvenance: Record<string, FieldProvenance[]>;
  enrichmentStatus: EnrichmentStatus;
  websiteAudit: WebsiteAudit | null;
  leadScore: number;
  opportunityLevel: OpportunityLevel;
  opportunityReasons: string[];
  operatingStatus: string | null;
  scrapedAt: string | null;
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
  limit: number | "all";
  pageSize: number;
}

export interface DiscoveryQuery extends DiscoverBusinessesRequest {
  country: string;
}

export interface DiscoverBusinessesResponse {
  query: DiscoveryQuery;
  count: number;
  businesses: Business[];
  providers: DiscoveryProviderStatus[];
  warnings: string[];
  sessionId: string;
  page: number;
  pageSize: number;
  totalCount: number;
  totalPages: number;
  effectiveLimit: number;
  summary: SearchSummary;
  enrichmentProgress: EnrichmentProgress;
  expiresAt: string;
}

export interface DiscoveryProviderStatus {
  provider: string;
  displayName: string;
  status: "success" | "failed" | "timeout" | "skipped";
  count: number;
  acceptedCount: number;
  durationMs: number;
  message: string | null;
}

export interface CategoriesResponse {
  categories: BusinessCategory[];
}

export interface EnrichBusinessRequest {
  business: Business;
}

export type SearchFilter =
  | "all"
  | "phone"
  | "email"
  | "official_website"
  | "no_official_website"
  | "directory_social_only"
  | "opportunity_high"
  | "opportunity_medium"
  | "opportunity_low"
  | "enrichment_pending"
  | "enrichment_complete";

export interface SearchSummary {
  total: number;
  withPhone: number;
  withEmail: number;
  withOfficialWebsite: number;
  withoutOfficialWebsite: number;
  directoryOrSocialOnly: number;
  highOpportunity: number;
  mediumOpportunity: number;
  lowOpportunity: number;
}

export interface EnrichmentProgress {
  total: number;
  processed: number;
  pending: number;
  failed: number;
}

export interface EnrichSearchSessionResponse {
  sessionId: string;
  attempted: number;
  results: BusinessEnrichment[];
  enrichmentProgress: EnrichmentProgress;
}
