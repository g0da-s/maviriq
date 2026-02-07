import type { CompetitorResearchOutput } from "@/lib/types";

const sentimentColor = {
  positive: "text-build",
  mixed: "text-conditional",
  negative: "text-skip",
};

export function Competitors({ data }: { data: CompetitorResearchOutput }) {
  return (
    <div className="rounded-2xl border border-card-border bg-card p-6">
      <div className="mb-4 flex items-center gap-3">
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-build/10 text-xs font-bold text-build">
          2
        </span>
        <h3 className="font-display text-lg font-semibold">competitor research</h3>
      </div>

      {/* overview stats */}
      <div className="mb-6 grid grid-cols-3 gap-3">
        <div className="rounded-xl border border-card-border bg-white/[0.02] p-3 text-center">
          <p className="text-xs text-muted/60">saturation</p>
          <p className={`mt-1 font-display font-bold ${
            data.market_saturation === "high" ? "text-skip" :
            data.market_saturation === "medium" ? "text-conditional" : "text-build"
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
      <p className="text-xs font-medium uppercase tracking-wider text-muted/60 mb-3">
        competitors
      </p>
      <div className="space-y-3">
        {data.competitors.map((comp, i) => (
          <div
            key={i}
            className="rounded-xl border border-card-border bg-white/[0.02] p-4"
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="font-medium">{comp.name}</p>
                <p className="mt-0.5 text-xs text-muted/60">{comp.one_liner}</p>
              </div>
              <span className={`text-xs font-medium ${sentimentColor[comp.review_sentiment]}`}>
                {comp.review_sentiment}
                {comp.review_count > 0 && ` (${comp.review_count})`}
              </span>
            </div>

            {/* pricing */}
            {comp.pricing.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {comp.pricing.map((p, j) => (
                  <span key={j} className="rounded-full bg-white/5 px-3 py-0.5 text-xs text-muted">
                    {p.plan_name}: {p.price}
                  </span>
                ))}
              </div>
            )}

            {/* strengths & weaknesses */}
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

      {/* underserved needs */}
      {data.underserved_needs.length > 0 && (
        <>
          <p className="mt-6 text-xs font-medium uppercase tracking-wider text-muted/60 mb-3">
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
        </>
      )}

      {/* common complaints */}
      {data.common_complaints.length > 0 && (
        <>
          <p className="mt-6 text-xs font-medium uppercase tracking-wider text-muted/60 mb-3">
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
        </>
      )}
    </div>
  );
}
