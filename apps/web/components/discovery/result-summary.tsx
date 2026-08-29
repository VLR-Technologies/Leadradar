import { Building2, Globe2, GlobeLock, Mail, Phone, TrendingUp } from "lucide-react";

import type { DiscoveryQuery, SearchSummary } from "@/types/business";

interface ResultSummaryProps {
  summary: SearchSummary;
  query: DiscoveryQuery;
}

export function ResultSummary({ summary, query }: ResultSummaryProps) {
  const metrics = [
    {
      label: "Total businesses",
      value: summary.total,
      icon: Building2,
      iconClass: "bg-[#eaf4ff] text-[#2563a6]",
    },
    {
      label: "Official website",
      value: summary.withOfficialWebsite,
      icon: Globe2,
      iconClass: "bg-[#eaf8f1] text-[#177454]",
    },
    {
      label: "No official website",
      value: summary.withoutOfficialWebsite,
      icon: GlobeLock,
      iconClass: "bg-[#fff5e7] text-[#ae681b]",
    },
    {
      label: "Phone available",
      value: summary.withPhone,
      icon: Phone,
      iconClass: "bg-[#f0edff] text-[#694eb7]",
    },
    {
      label: "Email available",
      value: summary.withEmail,
      icon: Mail,
      iconClass: "bg-[#edf7ff] text-[#316f9f]",
    },
    {
      label: "High opportunity",
      value: summary.highOpportunity,
      icon: TrendingUp,
      iconClass: "bg-[#fff0e8] text-[#a64d20]",
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
            {summary.total.toLocaleString()} businesses in this view
          </h2>
        </div>
        <p className="text-xs text-[#738078]">Opportunity is an internal sales heuristic, not a business-quality rating.</p>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-6">
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
