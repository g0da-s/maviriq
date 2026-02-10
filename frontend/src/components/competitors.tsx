import type { CompetitorResearchOutput } from "@/lib/types";

const sentimentColor = {
  positive: "text-build",
  mixed: "text-maybe",
  negative: "text-skip",
};

const sourceLabels: Record<string, { label: string; color: string }> = {
  google: { label: "Google", color: "border-blue-500/30 text-blue-400" },
  g2: { label: "G2", color: "border-orange-500/30 text-orange-400" },
  capterra: { label: "Capterra", color: "border-teal-500/30 text-teal-400" },
  producthunt: { label: "Product Hunt", color: "border-orange-400/30 text-orange-300" },
  crunchbase: { label: "Crunchbase", color: "border-indigo-500/30 text-indigo-400" },
  linkedin_jobs: { label: "LinkedIn", color: "border-sky-600/30 text-sky-400" },
  google_news: { label: "News", color: "border-blue-500/30 text-blue-400" },
  youtube: { label: "YouTube", color: "border-red-500/30 text-red-400" },
};

function SourceBadge({ source }: { source: string }) {
  const key = source.toLowerCase().replace(/\s+/g, "");
  const info = sourceLabels[key];
  return (
    <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${info?.color ?? "border-white/10 text-muted/60"}`}>
      {info?.label ?? source}
    </span>
  );
}

export function Competitors({ data }: { data: CompetitorResearchOutput }) {
  return (
    <div className="space-y-5">
      {/* overview stats */}
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-xl border border-card-border bg-white/[0.02] p-3 text-center">
          <p className="text-xs text-muted/60">saturation</p>
          <p className={`mt-1 font-display font-bold ${
            data.market_saturation === "high" ? "text-skip" :
            data.market_saturation === "medium" ? "text-maybe" : "text-build"
          }`}>
            {data.market_saturation}
          </p>
        </div>
        <div className="rounded-xl border border-card-border bg-white/[0.02] p-3 text-center">
          <p className="text-xs text-muted/60">avg price</p>
          <p className="mt-1 font-display font-bold">{data.avg_price_point}</p>
        </div>
        <div className="rounded-xl border border-card-border bg-white/[0.02] p-3 text-center">
          <p className="text-xs text-muted/60">competitors</p>
          <p className="mt-1 font-display font-bold">{data.competitors.length}</p>
        </div>
      </div>

      {/* competitor cards */}
      <div>
        <p className="text-xs font-medium uppercase tracking-wider text-muted/60 mb-3">
          competitors
        </p>
        <div className="space-y-3">
          {data.competitors.map((comp, i) => (
            <div key={i} className="rounded-xl border border-card-border bg-white/[0.02] p-4">
              <div className="flex items-start justify-between">
                <div>
                  {comp.url ? (
                    <a href={comp.url} target="_blank" rel="noopener noreferrer" className="font-medium hover:underline">
                      {comp.name}
                      <span className="ml-1 text-muted/40 text-xs">↗</span>
                    </a>
                  ) : (
                    <p className="font-medium">{comp.name}</p>
                  )}
                  <p className="mt-0.5 text-xs text-muted/60">{comp.one_liner}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <SourceBadge source={comp.source} />
                  <span className={`text-xs font-medium ${sentimentColor[comp.review_sentiment]}`}>
                    {comp.review_sentiment}
                    {comp.review_count != null && comp.review_count > 0 && ` (${comp.review_count})`}
                  </span>
                </div>
              </div>
              {comp.pricing.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {comp.pricing.map((p, j) => (
                    <span key={j} className="rounded-full bg-white/5 px-3 py-0.5 text-xs text-muted">
                      {p.plan_name}: {p.price}
                    </span>
                  ))}
                </div>
              )}
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                {comp.strengths.length > 0 && (
                  <div>
                    <p className="text-xs text-build/70 mb-1">strengths</p>
                    <ul className="space-y-0.5">
                      {comp.strengths.slice(0, 3).map((s, j) => (
                        <li key={j} className="text-xs text-muted/70">+ {s}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {comp.weaknesses.length > 0 && (
                  <div>
                    <p className="text-xs text-skip/70 mb-1">weaknesses</p>
                    <ul className="space-y-0.5">
                      {comp.weaknesses.slice(0, 3).map((w, j) => (
                        <li key={j} className="text-xs text-muted/70">- {w}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* underserved needs */}
      {data.underserved_needs.length > 0 && (
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted/60 mb-3">
            underserved needs
          </p>
          <div className="flex flex-wrap gap-2">
            {data.underserved_needs.map((need, i) => (
              <span
                key={i}
                className="rounded-full border border-build/20 bg-build/5 px-3 py-1 text-xs text-build"
              >
                {need}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* sources searched */}
      {data.competitors.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[10px] uppercase tracking-wider text-muted/40 mr-1">sources:</span>
          {[...new Set(data.competitors.map((c) => c.source))].map((src) => (
            <SourceBadge key={src} source={src} />
          ))}
        </div>
      )}

      {/* common complaints */}
      {data.common_complaints.length > 0 && (
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted/60 mb-3">
            common complaints
          </p>
          <div className="flex flex-wrap gap-2">
            {data.common_complaints.map((c, i) => (
              <span
                key={i}
                className="rounded-full border border-skip/20 bg-skip/5 px-3 py-1 text-xs text-skip/80"
              >
                {c}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
