"use client";

import {
  Building2,
  CalendarClock,
  Check,
  ExternalLink,
  Globe2,
  Mail,
  MapPin,
  MessageCircle,
  Phone,
  Share2,
  TrendingUp,
  X,
} from "lucide-react";
import { useEffect } from "react";

import { businessLocation, displayWebsite, safeWebsiteUrl } from "@/lib/format";
import type {
  Business,
  EnrichedField,
  EnrichmentStatus,
  FieldProvenance,
  ProvenanceSource,
  LeadWebsiteStatus,
  WebsiteVerificationStatus,
} from "@/types/business";

interface BusinessDetailDrawerProps {
  business: Business | null;
  onClose: () => void;
}

const provenanceLabels: Record<ProvenanceSource, string> = {
  overture: "Overture Maps",
  openstreetmap: "OpenStreetMap",
  official_website: "Official website",
  search_provider: "Search provider",
};

const enrichmentStatusLabels: Record<EnrichmentStatus, string> = {
  not_started: "Not enriched",
  in_progress: "Enriching…",
  completed: "Enriched",
  partial: "Partially enriched",
  no_data: "No new contacts found",
  failed: "Failed",
};

function enrichmentStatusClass(status: EnrichmentStatus): string {
  if (status === "failed") return "bg-[#fff0ed] text-[#98483c]";
  if (status === "no_data") return "bg-[#f0f3f2] text-[#66736c]";
  return "bg-[#edf7f2] text-[#176846]";
}

function ProvenanceNote({
  field,
  fallback,
}: {
  field?: EnrichedField;
  fallback?: FieldProvenance[];
}) {
  const primary = field?.primary ?? fallback?.[0] ?? null;
  const alternatives = field?.alternatives ?? fallback?.slice(1) ?? [];
  if (!primary) return null;
  return (
    <div className="mt-2 space-y-1">
      <p className="text-[11px] font-medium text-[#78867e]">
        Source: {provenanceLabels[primary.source]} · {primary.confidence} confidence
        {primary.sourceType ? ` · ${primary.sourceType.replaceAll("_", " ")}` : ""}
      </p>
      {primary.sourceUrl ? (
        <a href={primary.sourceUrl} target="_blank" rel="noreferrer noopener" className="block truncate text-[11px] text-[#177454] hover:underline">Source page</a>
      ) : null}
      {alternatives.length ? (
        <p className="text-[11px] leading-4 text-[#89948e]">
          Alternative: {alternatives.map((item) => `${item.value} (${provenanceLabels[item.source]})`).join(", ")}
        </p>
      ) : null}
    </div>
  );
}

function auditSignal(value: boolean | null): string {
  return value === null ? "Not checked" : value ? "Yes" : "No";
}

function Availability({ available }: { available: boolean }) {
  return available ? (
    <span className="inline-flex items-center gap-1 rounded-full bg-[#e9f8f1] px-2.5 py-1 text-xs font-semibold text-[#176846]">
      <Check className="size-3" /> Available
    </span>
  ) : (
    <span className="rounded-full bg-[#f1f3f2] px-2.5 py-1 text-xs font-semibold text-[#707c75]">Not available</span>
  );
}

function websiteStatusLabel(
  status: WebsiteVerificationStatus | undefined,
  leadStatus: LeadWebsiteStatus,
): string {
  if (status === "verified") return "Verified";
  if (status === "unreachable") return "Unreachable";
  if (status === "mismatch") return "Needs review";
  if (leadStatus === "unreachable") return "Unreachable";
  return leadStatus === "listed" ? "Listed" : "Not found in current sources";
}

export function BusinessDetailDrawer({ business, onClose }: BusinessDetailDrawerProps) {
  useEffect(() => {
    if (!business) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [business, onClose]);

  if (!business) return null;

  const websiteHref = safeWebsiteUrl(business.website);
  const enrichment = business.enrichment;
  const enrichmentLabel = enrichmentStatusLabels[business.enrichmentStatus];
  const enrichedSource = Object.values(business.fieldProvenance).some((items) =>
    items.some((item) => item.source === "official_website"),
  );

  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="presentation">
      <button
        type="button"
        aria-label="Close business details"
        className="absolute inset-0 bg-[#0c1e16]/32 backdrop-blur-[1px]"
        onClick={onClose}
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby="business-detail-title"
        className="relative flex h-full w-full max-w-[540px] flex-col overflow-y-auto bg-white shadow-[-18px_0_60px_rgba(10,34,24,0.16)]"
      >
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-[#e3e9e6] bg-white/95 px-5 py-4 backdrop-blur sm:px-7">
          <div>
            <p className="text-xs font-bold tracking-[0.08em] text-[#177454] uppercase">Business profile</p>
            <p className="mt-0.5 text-xs text-[#7b8780]">Contact details and field provenance</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            autoFocus
            className="flex size-9 items-center justify-center rounded-xl border border-[#dfe7e3] text-[#536159] transition hover:bg-[#f4f7f5] hover:text-[#17211d] focus:ring-4 focus:ring-[#177454]/10 focus:outline-none"
            aria-label="Close details"
          >
            <X className="size-4" />
          </button>
        </div>

        <div className="flex-1 px-5 py-6 sm:px-7 sm:py-7">
          <div className="flex items-start gap-4">
            <div className="flex size-13 shrink-0 items-center justify-center rounded-2xl bg-[#e9f7f1] text-lg font-bold text-[#177454]">
              {business.name.slice(0, 1).toUpperCase()}
            </div>
            <div className="min-w-0">
              <h2 id="business-detail-title" className="text-xl leading-7 font-semibold tracking-[-0.025em] text-[#17211d]">{business.name}</h2>
              <p className="mt-1 text-sm font-medium text-[#68756e]">{business.category ?? "Uncategorized business"}</p>
              {business.enrichmentStatus !== "not_started" ? (
                <span className={`mt-2 inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold ${enrichmentStatusClass(business.enrichmentStatus)}`}>
                  {enrichmentLabel}
                </span>
              ) : null}
              <div className="mt-3 flex items-center gap-2">
                <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${business.opportunityLevel === "High" ? "bg-[#fff0e8] text-[#a64d20]" : business.opportunityLevel === "Medium" ? "bg-[#fff8df] text-[#896a12]" : "bg-[#edf7f2] text-[#176846]"}`}>
                  {business.opportunityLevel} opportunity
                </span>
                <span className="text-xs font-semibold text-[#68756e]">Score {business.leadScore}/100</span>
              </div>
            </div>
          </div>

          <section className="mt-7" aria-labelledby="contact-heading">
            <h3 id="contact-heading" className="text-sm font-semibold text-[#1e2a24]">Contact information</h3>
            <div className="mt-3 space-y-3">
              <div className="flex gap-3 rounded-xl border border-[#e5ebe8] px-4 py-3.5">
                <Phone className="mt-0.5 size-4 shrink-0 text-[#6f7e76]" />
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-[#849087]">Phone</p>
                  {business.phone ? (
                    <a href={`tel:${business.phone}`} className="mt-1 block break-words text-sm font-semibold text-[#177454] hover:underline">{business.phone}</a>
                  ) : (
                    <p className="mt-1 text-sm font-medium text-[#2a3831]">Not found in current sources</p>
                  )}
                  <ProvenanceNote field={enrichment?.fields.phone} fallback={business.fieldProvenance.phone} />
                </div>
              </div>

              <div className="flex gap-3 rounded-xl border border-[#e5ebe8] px-4 py-3.5">
                <Mail className="mt-0.5 size-4 shrink-0 text-[#6f7e76]" />
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-[#849087]">Email</p>
                  {business.email ? (
                    <a href={`mailto:${business.email}`} className="mt-1 block break-all text-sm font-semibold text-[#177454] hover:underline">{business.email}</a>
                  ) : (
                    <p className="mt-1 text-sm font-medium text-[#2a3831]">Not found in current sources</p>
                  )}
                  <ProvenanceNote field={enrichment?.fields.email} fallback={business.fieldProvenance.email} />
                </div>
              </div>

              <div className="flex gap-3 rounded-xl border border-[#e5ebe8] px-4 py-3.5">
                <Globe2 className="mt-0.5 size-4 shrink-0 text-[#6f7e76]" />
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-[#849087]">Official website</p>
                  {business.website && websiteHref ? (
                    <a href={websiteHref} target="_blank" rel="noreferrer noopener" className="mt-1 flex items-center gap-1.5 break-all text-sm font-semibold text-[#177454] hover:underline">
                      {displayWebsite(business.website)} <ExternalLink className="size-3.5 shrink-0" />
                    </a>
                  ) : (
                    <p className="mt-1 text-sm font-medium text-[#2a3831]">Not found in current sources</p>
                  )}
                  <ProvenanceNote field={enrichment?.fields.website} fallback={business.fieldProvenance.website} />
                </div>
              </div>
              <div className="flex gap-3 rounded-xl border border-[#e5ebe8] px-4 py-3.5">
                <MessageCircle className="mt-0.5 size-4 shrink-0 text-[#6f7e76]" />
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-[#849087]">WhatsApp</p>
                  {business.whatsappNumber ? (
                    <a href={`https://wa.me/${business.whatsappNumber.replace(/\D/g, "")}`} target="_blank" rel="noreferrer noopener" className="mt-1 block text-sm font-semibold text-[#177454] hover:underline">{business.whatsappNumber}</a>
                  ) : <p className="mt-1 text-sm font-medium text-[#2a3831]">No explicit WhatsApp link found</p>}
                  <ProvenanceNote field={enrichment?.fields.whatsapp} fallback={business.fieldProvenance.whatsapp} />
                </div>
              </div>
              <div className="flex gap-3 rounded-xl border border-[#e5ebe8] px-4 py-3.5">
                <Globe2 className="mt-0.5 size-4 shrink-0 text-[#6f7e76]" />
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-[#849087]">Directory presence</p>
                  {business.directoryLinks.length ? business.directoryLinks.map((link) => (
                    <a key={link} href={link} target="_blank" rel="noreferrer noopener" className="mt-1 block truncate text-sm font-semibold text-[#8a6712] hover:underline">{displayWebsite(link)}</a>
                  )) : <p className="mt-1 text-sm font-medium text-[#2a3831]">Not found in current sources</p>}
                </div>
              </div>
              <div className="flex gap-3 rounded-xl border border-[#e5ebe8] px-4 py-3.5">
                <Share2 className="mt-0.5 size-4 shrink-0 text-[#6f7e76]" />
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-[#849087]">Social links</p>
                  {business.socialLinks.length ? (
                    <div className="mt-1 space-y-1">
                      {business.socialLinks.map((link) => (
                        <a key={link} href={link} target="_blank" rel="noreferrer noopener" className="block truncate text-sm font-semibold text-[#177454] hover:underline">
                          {displayWebsite(link)}
                        </a>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-1 text-sm font-medium text-[#2a3831]">Not found in current sources</p>
                  )}
                </div>
              </div>
            </div>
          </section>

          <section className="mt-8" aria-labelledby="location-heading">
            <h3 id="location-heading" className="text-sm font-semibold text-[#1e2a24]">Location</h3>
            <div className="mt-3 rounded-xl border border-[#e5ebe8] p-4">
              <div className="flex gap-3">
                <MapPin className="mt-0.5 size-4 shrink-0 text-[#6f7e76]" />
                <p className="text-sm leading-5 font-medium text-[#2a3831]">{businessLocation(business)}</p>
              </div>
              <dl className="mt-4 grid grid-cols-2 gap-4 border-t border-[#e8edea] pt-4 text-xs">
                <div><dt className="font-semibold text-[#849087]">Locality</dt><dd className="mt-1 font-medium text-[#34423b]">{business.address.locality ?? "Not found"}</dd></div>
                <div><dt className="font-semibold text-[#849087]">City</dt><dd className="mt-1 font-medium text-[#34423b]">{business.address.city ?? "Not found"}</dd></div>
                <div><dt className="font-semibold text-[#849087]">District</dt><dd className="mt-1 font-medium text-[#34423b]">{business.address.district ?? "Not found"}</dd></div>
                <div><dt className="font-semibold text-[#849087]">State</dt><dd className="mt-1 font-medium text-[#34423b]">{business.address.state ?? "Not found"}</dd></div>
                <div><dt className="font-semibold text-[#849087]">PIN code</dt><dd className="mt-1 font-medium text-[#34423b]">{business.address.postcode ?? "Not found"}</dd></div>
                <div><dt className="font-semibold text-[#849087]">Country</dt><dd className="mt-1 font-medium text-[#34423b]">{business.address.country ?? "Not found"}</dd></div>
                <div><dt className="font-semibold text-[#849087]">Coordinates</dt><dd className="mt-1 font-medium text-[#34423b]">{business.latitude?.toFixed(5) ?? "—"}, {business.longitude?.toFixed(5) ?? "—"}</dd></div>
              </dl>
            </div>
          </section>

          {business.enrichmentStatus !== "not_started" ? (
            <section className="mt-8" aria-labelledby="enrichment-heading">
              <h3 id="enrichment-heading" className="text-sm font-semibold text-[#1e2a24]">Enrichment</h3>
              <p className="mt-1 text-xs leading-5 text-[#748078]">
                Enrichment checks available public sources for additional business contact details.
              </p>
              <dl className="mt-3 rounded-xl border border-[#e1e8e4] bg-[#f8faf9] px-4 py-1">
                <div className="flex items-start justify-between gap-4 border-b border-[#e4eae7] py-3.5">
                  <dt className="text-xs font-semibold text-[#849087]">Status</dt>
                  <dd className="text-right text-sm font-semibold text-[#2f3e36]">{enrichmentLabel}</dd>
                </div>
                <div className="flex items-start justify-between gap-4 py-3.5">
                  <dt className="text-xs font-semibold text-[#849087]">Reason</dt>
                  <dd className="max-w-80 text-right text-sm leading-5 font-medium text-[#536159]">
                    {enrichment?.message ?? "The current search session contains this enrichment outcome."}
                  </dd>
                </div>
              </dl>
            </section>
          ) : null}

          <section className="mt-8" aria-labelledby="opportunity-heading">
            <h3 id="opportunity-heading" className="flex items-center gap-2 text-sm font-semibold text-[#1e2a24]"><TrendingUp className="size-4 text-[#177454]" />Opportunity analysis</h3>
            <p className="mt-1 text-xs leading-5 text-[#748078]">Internal sales opportunity only; this is not a business-quality rating.</p>
            <ul className="mt-3 space-y-2 rounded-xl border border-[#e5ebe8] p-4 text-sm text-[#45534c]">
              {business.opportunityReasons.length ? business.opportunityReasons.map((reason) => (
                <li key={reason} className="flex gap-2"><span className="mt-2 size-1.5 shrink-0 rounded-full bg-[#2ca475]" />{reason}</li>
              )) : <li>No scoring reasons are available.</li>}
            </ul>
          </section>

          <section className="mt-8" aria-labelledby="presence-heading">
            <h3 id="presence-heading" className="text-sm font-semibold text-[#1e2a24]">Digital presence</h3>
            <p className="mt-1 text-xs leading-5 text-[#748078]">
              Listed means present in source data. Verified is only shown after official website inspection.
            </p>
            <div className="mt-4 divide-y divide-[#e7ece9] rounded-xl border border-[#e1e8e4] px-4">
              <div className="flex items-center justify-between py-3.5 text-sm font-medium text-[#3b4942]"><span>Official website</span><span className="rounded-full bg-[#edf6f1] px-2.5 py-1 text-xs font-semibold text-[#326a53]">{websiteStatusLabel(enrichment?.websiteStatus, business.websiteStatus)}</span></div>
              <div className="flex items-center justify-between py-3.5 text-sm font-medium text-[#3b4942]"><span>Directory/social presence</span><Availability available={Boolean(business.directoryLinks.length || business.socialLinks.length)} /></div>
              <div className="flex items-center justify-between py-3.5 text-sm font-medium text-[#3b4942]"><span>WhatsApp</span><Availability available={Boolean(business.whatsappNumber)} /></div>
              <div className="flex items-center justify-between py-3.5 text-sm font-medium text-[#3b4942]"><span>Email</span><Availability available={Boolean(business.email)} /></div>
              <div className="flex items-center justify-between py-3.5 text-sm font-medium text-[#3b4942]"><span>Phone</span><Availability available={Boolean(business.phone)} /></div>
              <div className="flex items-center justify-between py-3.5 text-sm font-medium text-[#3b4942]"><span>Audit</span><span className="text-xs font-semibold text-[#536159]">{business.websiteAudit?.label ?? "Not audited"}</span></div>
              <div className="flex items-center justify-between py-3.5 text-sm font-medium text-[#3b4942]"><span>Rating</span><span className="text-xs font-semibold text-[#536159]">{business.rating !== null ? `${business.rating}${business.reviewCount !== null ? ` (${business.reviewCount})` : ""}` : "Not available"}</span></div>
            </div>
            {business.websiteAudit ? (
              <dl className="mt-3 grid grid-cols-2 gap-x-5 gap-y-3 rounded-xl border border-[#e5ebe8] bg-[#f8faf9] p-4 text-xs">
                <div><dt className="font-semibold text-[#849087]">Reachable</dt><dd className="mt-1 font-medium text-[#34423b]">{auditSignal(business.websiteAudit.reachable)}</dd></div>
                <div><dt className="font-semibold text-[#849087]">HTTPS</dt><dd className="mt-1 font-medium text-[#34423b]">{auditSignal(business.websiteAudit.usesHttps)}</dd></div>
                <div><dt className="font-semibold text-[#849087]">Mobile viewport</dt><dd className="mt-1 font-medium text-[#34423b]">{auditSignal(business.websiteAudit.mobileViewport)}</dd></div>
                <div><dt className="font-semibold text-[#849087]">Contact page</dt><dd className="mt-1 font-medium text-[#34423b]">{auditSignal(business.websiteAudit.contactPagePresent)}</dd></div>
                <div><dt className="font-semibold text-[#849087]">Page title</dt><dd className="mt-1 font-medium text-[#34423b]">{auditSignal(business.websiteAudit.titlePresent)}</dd></div>
                <div><dt className="font-semibold text-[#849087]">Meta description</dt><dd className="mt-1 font-medium text-[#34423b]">{auditSignal(business.websiteAudit.metaDescriptionPresent)}</dd></div>
                <div><dt className="font-semibold text-[#849087]">Social links</dt><dd className="mt-1 font-medium text-[#34423b]">{auditSignal(business.websiteAudit.socialLinksPresent)}</dd></div>
                <div><dt className="font-semibold text-[#849087]">Broken responses</dt><dd className="mt-1 font-medium text-[#34423b]">{business.websiteAudit.brokenResponseCount}</dd></div>
              </dl>
            ) : null}
          </section>

          <section className="mt-8" aria-labelledby="source-heading">
            <h3 id="source-heading" className="text-sm font-semibold text-[#1e2a24]">Source information</h3>
            <div className="mt-4 rounded-xl bg-[#f5f8f6] p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-[#2d3b34]"><Building2 className="size-4 text-[#177454]" />{[...business.sources.map((source) => source === "overture" ? "Overture Maps" : "OpenStreetMap"), ...(enrichedSource ? ["Official Website"] : [])].join(" + ")}</div>
              <dl className="mt-4 grid grid-cols-2 gap-4 text-xs">
                <div><dt className="font-semibold text-[#849087]">Lead ID</dt><dd className="mt-1 break-all font-medium text-[#34423b]">{business.leadId ?? business.sourceId}</dd></div>
                <div><dt className="font-semibold text-[#849087]">Opening hours</dt><dd className="mt-1 font-medium text-[#34423b]">{business.openingHours ?? "Not found"}</dd></div>
                <div><dt className="font-semibold text-[#849087]">Pages inspected</dt><dd className="mt-1 font-medium text-[#34423b]">{enrichment?.visitedPages.length ?? 0}</dd></div>
                <div><dt className="font-semibold text-[#849087]">Enrichment storage</dt><dd className="mt-1 font-medium text-[#34423b]">Session only</dd></div>
              </dl>
              {Object.keys(business.sourceIds).length ? (
                <div className="mt-4 border-t border-[#e3eae6] pt-4 text-xs">
                  <p className="font-semibold text-[#849087]">Provider IDs</p>
                  {Object.entries(business.sourceIds).map(([source, ids]) => (
                    <p key={source} className="mt-1 break-all font-medium text-[#34423b]">
                      {source === "overture" ? "Overture Maps" : "OpenStreetMap"}: {ids.join(", ")}
                    </p>
                  ))}
                </div>
              ) : null}
              {business.openingHours ? <CalendarClock className="mt-4 size-4 text-[#829087]" aria-hidden="true" /> : null}
            </div>
          </section>
        </div>
      </aside>
    </div>
  );
}
