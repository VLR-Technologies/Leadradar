"use client";

import {
  Building2,
  CalendarClock,
  Check,
  ExternalLink,
  Globe2,
  Mail,
  MapPin,
  Phone,
  X,
} from "lucide-react";
import { useEffect } from "react";

import { businessLocation, displayWebsite, safeWebsiteUrl } from "@/lib/format";
import type {
  Business,
  EnrichedField,
  EnrichmentStatus,
  ProvenanceSource,
  WebsiteVerificationStatus,
} from "@/types/business";

interface BusinessDetailDrawerProps {
  business: Business | null;
  onClose: () => void;
}

const provenanceLabels: Record<ProvenanceSource, string> = {
  openstreetmap: "OpenStreetMap",
  official_website: "Official website",
  search_provider: "Search provider",
};

const enrichmentStatusLabels: Record<EnrichmentStatus, string> = {
  not_started: "Not enriched",
  in_progress: "Enriching…",
  completed: "Enriched",
  partial: "Partially enriched",
  no_data: "No additional data found",
  failed: "Failed",
};

function enrichmentStatusClass(status: EnrichmentStatus): string {
  if (status === "failed") return "bg-[#fff0ed] text-[#98483c]";
  if (status === "no_data") return "bg-[#f0f3f2] text-[#66736c]";
  return "bg-[#edf7f2] text-[#176846]";
}

function ProvenanceNote({ field, fallbackListed }: { field?: EnrichedField; fallbackListed: boolean }) {
  const primary = field?.primary;
  if (!primary && !fallbackListed) return null;
  return (
    <div className="mt-2 space-y-1">
      <p className="text-[11px] font-medium text-[#78867e]">
        Source: {primary ? provenanceLabels[primary.source] : "OpenStreetMap"}
        {primary ? ` · ${primary.confidence} confidence` : ""}
      </p>
      {field?.alternatives.length ? (
        <p className="text-[11px] leading-4 text-[#89948e]">
          Alternative: {field.alternatives.map((item) => `${item.value} (${provenanceLabels[item.source]})`).join(", ")}
        </p>
      ) : null}
    </div>
  );
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

function websiteStatusLabel(status: WebsiteVerificationStatus | undefined, listed: boolean): string {
  if (status === "verified") return "Verified";
  if (status === "unreachable") return "Unreachable";
  if (status === "mismatch") return "Needs review";
  return listed ? "Listed" : "Not listed";
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
  const enrichmentLabel = enrichment
    ? enrichmentStatusLabels[enrichment.status]
    : null;
  const enrichedSource = enrichment && [
    enrichment.fields.phone,
    enrichment.fields.email,
    enrichment.fields.website,
  ].some((field) =>
    [field.primary, ...field.alternatives].some(
      (item) => item?.source === "official_website",
    ),
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
              {enrichment ? (
                <span className={`mt-2 inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold ${enrichmentStatusClass(enrichment.status)}`}>
                  {enrichmentLabel}
                </span>
              ) : null}
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
                    <p className="mt-1 text-sm font-medium text-[#2a3831]">Not listed</p>
                  )}
                  <ProvenanceNote field={enrichment?.fields.phone} fallbackListed={Boolean(business.phone)} />
                </div>
              </div>

              <div className="flex gap-3 rounded-xl border border-[#e5ebe8] px-4 py-3.5">
                <Mail className="mt-0.5 size-4 shrink-0 text-[#6f7e76]" />
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-[#849087]">Email</p>
                  {business.email ? (
                    <a href={`mailto:${business.email}`} className="mt-1 block break-all text-sm font-semibold text-[#177454] hover:underline">{business.email}</a>
                  ) : (
                    <p className="mt-1 text-sm font-medium text-[#2a3831]">Not listed</p>
                  )}
                  <ProvenanceNote field={enrichment?.fields.email} fallbackListed={Boolean(business.email)} />
                </div>
              </div>

              <div className="flex gap-3 rounded-xl border border-[#e5ebe8] px-4 py-3.5">
                <Globe2 className="mt-0.5 size-4 shrink-0 text-[#6f7e76]" />
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-[#849087]">Website</p>
                  {business.website && websiteHref ? (
                    <a href={websiteHref} target="_blank" rel="noreferrer noopener" className="mt-1 flex items-center gap-1.5 break-all text-sm font-semibold text-[#177454] hover:underline">
                      {displayWebsite(business.website)} <ExternalLink className="size-3.5 shrink-0" />
                    </a>
                  ) : (
                    <p className="mt-1 text-sm font-medium text-[#2a3831]">Not listed in OpenStreetMap</p>
                  )}
                  <ProvenanceNote field={enrichment?.fields.website} fallbackListed={Boolean(business.website)} />
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
                <div><dt className="font-semibold text-[#849087]">City</dt><dd className="mt-1 font-medium text-[#34423b]">{business.address.city ?? "Not listed"}</dd></div>
                <div><dt className="font-semibold text-[#849087]">Region</dt><dd className="mt-1 font-medium text-[#34423b]">{business.address.state ?? "Not listed"}</dd></div>
                <div><dt className="font-semibold text-[#849087]">Country</dt><dd className="mt-1 font-medium text-[#34423b]">{business.address.country ?? "Not listed"}</dd></div>
                <div><dt className="font-semibold text-[#849087]">Coordinates</dt><dd className="mt-1 font-medium text-[#34423b]">{business.latitude?.toFixed(5) ?? "—"}, {business.longitude?.toFixed(5) ?? "—"}</dd></div>
              </dl>
            </div>
          </section>

          {enrichment ? (
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
                    {enrichment.message ?? "No additional explanation was provided."}
                  </dd>
                </div>
              </dl>
            </section>
          ) : null}

          <section className="mt-8" aria-labelledby="presence-heading">
            <h3 id="presence-heading" className="text-sm font-semibold text-[#1e2a24]">Digital presence</h3>
            <p className="mt-1 text-xs leading-5 text-[#748078]">
              Listed means present in source data. Verified is only shown after official website inspection.
            </p>
            <div className="mt-4 divide-y divide-[#e7ece9] rounded-xl border border-[#e1e8e4] px-4">
              <div className="flex items-center justify-between py-3.5 text-sm font-medium text-[#3b4942]"><span>Website</span><span className="rounded-full bg-[#edf6f1] px-2.5 py-1 text-xs font-semibold text-[#326a53]">{websiteStatusLabel(enrichment?.websiteStatus, Boolean(business.website))}</span></div>
              <div className="flex items-center justify-between py-3.5 text-sm font-medium text-[#3b4942]"><span>Email</span><Availability available={Boolean(business.email)} /></div>
              <div className="flex items-center justify-between py-3.5 text-sm font-medium text-[#3b4942]"><span>Phone</span><Availability available={Boolean(business.phone)} /></div>
            </div>
          </section>

          <section className="mt-8" aria-labelledby="source-heading">
            <h3 id="source-heading" className="text-sm font-semibold text-[#1e2a24]">Source information</h3>
            <div className="mt-4 rounded-xl bg-[#f5f8f6] p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-[#2d3b34]"><Building2 className="size-4 text-[#177454]" />{enrichedSource ? "OpenStreetMap + Official Website" : "OpenStreetMap"}</div>
              <dl className="mt-4 grid grid-cols-2 gap-4 text-xs">
                <div><dt className="font-semibold text-[#849087]">Source ID</dt><dd className="mt-1 break-all font-medium text-[#34423b]">{business.sourceId}</dd></div>
                <div><dt className="font-semibold text-[#849087]">Opening hours</dt><dd className="mt-1 font-medium text-[#34423b]">{business.openingHours ?? "Not listed"}</dd></div>
                <div><dt className="font-semibold text-[#849087]">Pages inspected</dt><dd className="mt-1 font-medium text-[#34423b]">{enrichment?.visitedPages.length ?? 0}</dd></div>
                <div><dt className="font-semibold text-[#849087]">Enrichment storage</dt><dd className="mt-1 font-medium text-[#34423b]">Session only</dd></div>
              </dl>
              {business.openingHours ? <CalendarClock className="mt-4 size-4 text-[#829087]" aria-hidden="true" /> : null}
            </div>
          </section>
        </div>
      </aside>
    </div>
  );
}
