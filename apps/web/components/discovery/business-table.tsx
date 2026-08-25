import {
  Check,
  ChevronRight,
  ExternalLink,
  LoaderCircle,
  MapPin,
  RefreshCw,
  SearchX,
  Sparkles,
} from "lucide-react";

import { businessLocation, displayWebsite, safeWebsiteUrl } from "@/lib/format";
import type { Business, EnrichedField } from "@/types/business";

interface BusinessTableProps {
  businesses: Business[];
  enrichingSourceIds: ReadonlySet<string>;
  enrichmentErrors: Record<string, string>;
  onSelect: (business: Business) => void;
  onEnrich: (business: Business) => void;
}

function WebsiteCell({ business }: { business: Business }) {
  const href = safeWebsiteUrl(business.website);
  const verification = business.enrichment?.websiteStatus;
  const label =
    verification === "verified"
      ? "Verified"
      : verification === "unreachable"
        ? "Unreachable"
        : business.website
          ? "Listed"
          : "Not listed";
  const badgeClass =
    verification === "verified"
      ? "bg-[#e7f8ef] text-[#126b47]"
      : verification === "unreachable"
        ? "bg-[#fff1ed] text-[#9a493c]"
        : business.website
          ? "bg-[#edf6f1] text-[#326a53]"
          : "bg-[#f2f4f3] text-[#6f7b75]";

  return (
    <div className="space-y-1">
      <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${badgeClass}`}>
        {label}
      </span>
      {business.website && href ? (
        <a
          href={href}
          target="_blank"
          rel="noreferrer noopener"
          onClick={(event) => event.stopPropagation()}
          className="flex max-w-40 items-center gap-1 truncate text-xs font-medium text-[#52635b] hover:text-[#177454] hover:underline"
          title={business.website}
        >
          <span className="truncate">{displayWebsite(business.website)}</span>
          <ExternalLink aria-label="Open website in a new tab" className="size-3 shrink-0" />
        </a>
      ) : null}
    </div>
  );
}

function ContactCell({ kind, value }: { kind: "phone" | "email"; value: string | null }) {
  if (!value) {
    return <span className="text-xs text-[#7c8881]">Not listed</span>;
  }
  return (
    <a
      href={`${kind === "phone" ? "tel" : "mailto"}:${value}`}
      onClick={(event) => event.stopPropagation()}
      className="block max-w-44 truncate text-xs font-medium text-[#3f5f50] hover:text-[#177454] hover:underline"
      title={value}
    >
      {value}
    </a>
  );
}

function hasOfficialWebsiteSource(field: EnrichedField | undefined): boolean {
  return Boolean(
    field?.primary?.source === "official_website" ||
      field?.alternatives.some((item) => item.source === "official_website"),
  );
}

function sourceLabel(business: Business): string {
  const fields = business.enrichment?.fields;
  return fields &&
    [fields.phone, fields.email, fields.website].some(hasOfficialWebsiteSource)
    ? "OSM + Website"
    : "OpenStreetMap";
}

function EnrichAction({
  business,
  enriching,
  error,
  onEnrich,
}: {
  business: Business;
  enriching: boolean;
  error?: string;
  onEnrich: (business: Business) => void;
}) {
  const status = business.enrichment?.status;
  const completed = status === "completed";
  const settled = completed || status === "partial" || status === "no_data";
  let label = "Enrich";
  let Icon = Sparkles;
  if (enriching) {
    label = "Enriching…";
    Icon = LoaderCircle;
  } else if (completed) {
    label = "Enriched";
    Icon = Check;
  } else if (status === "partial") {
    label = "Partial";
    Icon = Check;
  } else if (status === "no_data") {
    label = "No data";
    Icon = SearchX;
  } else if (status === "failed" || error) {
    label = "Retry";
    Icon = RefreshCw;
  }
  const buttonClass =
    status === "failed" || error
      ? "border-[#ead3cf] bg-[#fff8f6] text-[#98483c] hover:border-[#d9aaa2] hover:bg-[#fff2ef]"
      : status === "no_data"
        ? "border-[#dfe5e2] bg-[#f7f9f8] text-[#66736c]"
        : "border-[#cfe1d8] bg-white text-[#176846] hover:border-[#9fc9b5] hover:bg-[#f1faf6]";

  return (
    <div className="min-w-28">
      <button
        type="button"
        disabled={enriching || settled}
        onClick={(event) => {
          event.stopPropagation();
          onEnrich(business);
        }}
        className={`inline-flex min-h-9 items-center justify-center gap-1.5 rounded-lg border px-3 text-xs font-semibold transition disabled:cursor-default disabled:opacity-80 ${buttonClass}`}
        title={
          error ??
          business.enrichment?.message ??
          "Find additional public contact details"
        }
      >
        <Icon className={`size-3.5 ${enriching ? "animate-spin" : ""}`} />
        {label}
      </button>
      {error ? <p className="mt-1 max-w-36 text-[10px] leading-4 text-[#a44d40]">{error}</p> : null}
    </div>
  );
}

export function BusinessTable({
  businesses,
  enrichingSourceIds,
  enrichmentErrors,
  onSelect,
  onEnrich,
}: BusinessTableProps) {
  return (
    <section
      aria-label="Discovered businesses"
      className="overflow-hidden rounded-2xl border border-[#dfe7e3] bg-white shadow-[0_8px_28px_rgba(30,57,45,0.045)]"
    >
      <div className="border-b border-[#e4ebe7] px-5 py-4 sm:px-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h3 className="font-semibold text-[#1b2721]">Lead candidates</h3>
            <p className="mt-0.5 text-xs text-[#758179]">Open a row for details or use Enrich to find additional public contact details.</p>
          </div>
          <span className="rounded-lg border border-[#dfe7e3] bg-[#f8faf9] px-2.5 py-1.5 text-xs font-semibold text-[#5e6c65]">
            {businesses.length} records
          </span>
        </div>
      </div>

      <div className="divide-y divide-[#e8edea] md:hidden">
        {businesses.map((business) => (
          <article key={business.sourceId} className="p-4">
            <button
              type="button"
              onClick={() => onSelect(business)}
              className="flex w-full items-start gap-3 text-left focus:outline-none"
            >
              <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-[#edf7f2] text-sm font-bold text-[#177454]">
                {business.name.slice(0, 1).toUpperCase()}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-semibold text-[#1e2a24]">{business.name}</span>
                <span className="mt-1 flex items-center gap-1 truncate text-xs text-[#6c7972]">
                  <MapPin className="size-3 shrink-0" />
                  {businessLocation(business)}
                </span>
              </span>
              <ChevronRight aria-hidden="true" className="mt-2 size-4 shrink-0 text-[#9ba69f]" />
            </button>
            <div className="mt-3 grid grid-cols-2 gap-3 rounded-xl bg-[#f7faf8] p-3">
              <div><p className="mb-1 text-[10px] font-bold tracking-wide text-[#839087] uppercase">Phone</p><ContactCell kind="phone" value={business.phone} /></div>
              <div><p className="mb-1 text-[10px] font-bold tracking-wide text-[#839087] uppercase">Email</p><ContactCell kind="email" value={business.email} /></div>
              <div><p className="mb-1 text-[10px] font-bold tracking-wide text-[#839087] uppercase">Website</p><WebsiteCell business={business} /></div>
              <div className="flex items-end justify-end">
                <EnrichAction
                  business={business}
                  enriching={enrichingSourceIds.has(business.sourceId)}
                  error={enrichmentErrors[business.sourceId]}
                  onEnrich={onEnrich}
                />
              </div>
            </div>
          </article>
        ))}
      </div>

      <div className="hidden overflow-x-auto md:block">
        <table className="w-full min-w-[1180px] border-collapse text-left">
          <thead>
            <tr className="bg-[#f8faf9] text-[11px] font-bold tracking-[0.055em] text-[#68756e] uppercase">
              <th className="px-6 py-3.5">Business</th>
              <th className="px-4 py-3.5">Category</th>
              <th className="px-4 py-3.5">Location</th>
              <th className="px-4 py-3.5">Phone</th>
              <th className="px-4 py-3.5">Email</th>
              <th className="px-4 py-3.5">Website</th>
              <th className="px-4 py-3.5">Source</th>
              <th className="px-4 py-3.5">Action</th>
              <th className="w-10 px-3 py-3.5"><span className="sr-only">Open details</span></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#e8edea]">
            {businesses.map((business) => (
              <tr
                key={business.sourceId}
                onClick={() => onSelect(business)}
                className="group cursor-pointer text-sm transition hover:bg-[#f8fbf9]"
              >
                <td className="px-6 py-4">
                  <button
                    type="button"
                    onClick={() => onSelect(business)}
                    className="flex max-w-60 items-center gap-3 text-left focus:outline-none"
                  >
                    <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-[#edf7f2] text-xs font-bold text-[#177454]">
                      {business.name.slice(0, 1).toUpperCase()}
                    </span>
                    <span className="min-w-0">
                      <span className="block truncate font-semibold text-[#1e2a24] group-hover:text-[#126848]">{business.name}</span>
                      <span className="mt-0.5 block truncate text-xs text-[#849087]">{business.sourceId}</span>
                    </span>
                  </button>
                </td>
                <td className="px-4 py-4 text-[#55635c]">{business.category ?? "—"}</td>
                <td className="max-w-55 px-4 py-4"><span className="line-clamp-2 text-xs leading-5 text-[#55635c]" title={businessLocation(business)}>{businessLocation(business)}</span></td>
                <td className="px-4 py-4"><ContactCell kind="phone" value={business.phone} /></td>
                <td className="px-4 py-4"><ContactCell kind="email" value={business.email} /></td>
                <td className="px-4 py-4"><WebsiteCell business={business} /></td>
                <td className="px-4 py-4">
                  <span className="inline-flex items-center gap-1.5 text-xs font-semibold whitespace-nowrap text-[#4e5e56]">
                    <span className="size-1.5 rounded-full bg-[#33a678]" />
                    {sourceLabel(business)}
                  </span>
                </td>
                <td className="px-4 py-4">
                  <EnrichAction
                    business={business}
                    enriching={enrichingSourceIds.has(business.sourceId)}
                    error={enrichmentErrors[business.sourceId]}
                    onEnrich={onEnrich}
                  />
                </td>
                <td className="px-3 py-4"><ChevronRight aria-hidden="true" className="size-4 text-[#a1aba5] transition group-hover:translate-x-0.5 group-hover:text-[#177454]" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
