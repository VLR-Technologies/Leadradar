import { Building2, Globe2, GlobeLock, Phone } from "lucide-react";

import type { Business, DiscoveryQuery } from "@/types/business";

interface ResultSummaryProps {
  businesses: Business[];
  query: DiscoveryQuery;
}

export function ResultSummary({ businesses, query }: ResultSummaryProps) {
  const websiteListed = businesses.filter((business) => business.website).length;
  const phoneAvailable = businesses.filter((business) => business.phone).length;
  const metrics = [
    {
      label: "Total businesses",
      value: businesses.length,
      icon: Building2,
      iconClass: "bg-[#eaf4ff] text-[#2563a6]",
    },
    {
      label: "Website listed",
      value: websiteListed,
      icon: Globe2,
      iconClass: "bg-[#eaf8f1] text-[#177454]",
    },
    {
      label: "Website not listed",
      value: businesses.length - websiteListed,
      icon: GlobeLock,
      iconClass: "bg-[#fff5e7] text-[#ae681b]",
    },
    {
      label: "Phone available",
      value: phoneAvailable,
      icon: Phone,
      iconClass: "bg-[#f0edff] text-[#694eb7]",
    },
  ] as const;
  const locationLabel = [query.city, query.region, query.country].filter(Boolean).join(", ");

  return (
    <section aria-labelledby="result-heading">
      <div className="mb-4 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-[#177454]">
            {locationLabel} · {query.category}
          </p>
          <h2 id="result-heading" className="mt-1 text-xl font-semibold tracking-[-0.025em] text-[#17211d]">
            {businesses.length.toLocaleString()} businesses discovered
          </h2>
        </div>
        <p className="text-xs text-[#738078]">Website status reflects the current source record.</p>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <article
              key={metric.label}
              className="rounded-2xl border border-[#dfe7e3] bg-white p-4 shadow-[0_5px_20px_rgba(30,57,45,0.035)] sm:p-5"
            >
              <div className={`mb-4 flex size-9 items-center justify-center rounded-xl ${metric.iconClass}`}>
                <Icon aria-hidden="true" className="size-[18px]" />
              </div>
              <p className="text-2xl font-semibold tracking-[-0.03em] text-[#17211d] sm:text-[28px]">
                {metric.value.toLocaleString()}
              </p>
              <p className="mt-1 text-xs font-medium text-[#6c7872] sm:text-sm">{metric.label}</p>
            </article>
          );
        })}
      </div>
    </section>
  );
}
