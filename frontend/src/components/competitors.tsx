import type { CompetitorResearchOutput } from "@/lib/types";

function isSafeUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

const sentimentColor = {
  positive: "text-build",
  mixed: "text-maybe",
  negative: "text-skip",
};

const sentimentLabel = {
  positive: "Liked",
  mixed: "Mixed reviews",
  negative: "Disliked",
};

export function Competitors({ data }: { data: CompetitorResearchOutput }) {
  return (
    <div className="space-y-6">
      {/* overview stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-xl border border-card-border bg-card p-4 text-center">
          <p className="text-xs text-muted/60 mb-1">Market crowded?</p>
          <p className={`mt-1 font-display text-lg font-bold ${
            data.market_saturation === "high" ? "text-skip" :
            data.market_saturation === "medium" ? "text-maybe" : "text-build"
          }`}>
            {data.market_saturation === "high" ? "Very crowded" :
             data.market_saturation === "medium" ? "Somewhat" : "Not crowded"}
          </p>
        </div>
        <div className="rounded-xl border border-card-border bg-card p-4 text-center">
          <p className="text-xs text-muted/60 mb-1">Typical price</p>
          <p className="mt-1 font-display text-lg font-bold">{data.avg_price_point}</p>
        </div>
        <div className="rounded-xl border border-card-border bg-card p-4 text-center">
          <p className="text-xs text-muted/60 mb-1">Competitors found</p>
          <p className="mt-1 font-display text-lg font-bold">{data.competitors.length}</p>
        </div>
      </div>

      {/* competitor cards */}
      {data.competitors.length > 0 && (
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted/60 mb-3">
            Who you&apos;re up against
          </p>
          <div className="rounded-xl border border-card-border bg-card divide-y divide-card-border">
            {data.competitors.map((comp, i) => (
              <div key={i} className="px-5 py-4">
                {/* header row */}
                <div className="flex items-start justify-between mb-1.5">
                  <div>
                    {comp.url && isSafeUrl(comp.url) ? (
                      <a href={comp.url} target="_blank" rel="noopener noreferrer" className="text-sm font-semibold text-foreground/90 hover:underline">
                        {comp.name}<span className="ml-1 text-muted/40 text-xs">&#8599;</span>
                      </a>
                    ) : (
                      <p className="text-sm font-semibold text-foreground/90">{comp.name}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className={`text-xs font-medium ${sentimentColor[comp.review_sentiment]}`}>
                      {sentimentLabel[comp.review_sentiment]}
                      {comp.review_count != null && comp.review_count > 0 && ` (${comp.review_count})`}
                    </span>
                  </div>
                </div>

                {/* description */}
                <p className="text-sm text-foreground/60 mb-3">{comp.one_liner}</p>

                {/* pricing */}
                {comp.pricing.length > 0 && (
                  <div className="flex flex-wrap gap-2 mb-3">
                    {comp.pricing.map((p, j) => (
                      <span key={j} className="rounded-full bg-white/5 px-3 py-0.5 text-xs text-muted">
                        {p.plan_name}: {p.price}
                      </span>
                    ))}
                  </div>
                )}

                {/* strengths + weaknesses side by side */}
                {(comp.strengths.length > 0 || comp.weaknesses.length > 0) && (
                  <div className="grid gap-3 sm:grid-cols-2">
                    {comp.strengths.length > 0 && (
                      <div>
                        <p className="text-xs text-build/70 font-medium mb-1.5">What they do well</p>
                        <ul className="space-y-1">
                          {comp.strengths.slice(0, 3).map((s, j) => (
                            <li key={j} className="flex items-start gap-2 text-xs text-foreground/60">
                              <span className="text-build mt-0.5">+</span>
                              {s}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {comp.weaknesses.length > 0 && (
                      <div>
                        <p className="text-xs text-skip/70 font-medium mb-1.5">Where they fall short</p>
                        <ul className="space-y-1">
                          {comp.weaknesses.slice(0, 3).map((w, j) => (
                            <li key={j} className="flex items-start gap-2 text-xs text-foreground/60">
                              <span className="text-skip mt-0.5">-</span>
                              {w}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* underserved needs — your opportunity */}
      {data.underserved_needs.length > 0 && (
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted/60 mb-3">
            Gaps competitors aren&apos;t filling
          </p>
          <div className="rounded-xl border border-build/15 bg-build/5 px-5 py-4">
            <ul className="space-y-2">
              {data.underserved_needs.map((need, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-foreground/80">
                  <span className="text-build mt-0.5 font-bold">+</span>
                  {need}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* common complaints */}
      {data.common_complaints.length > 0 && (
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted/60 mb-3">
            What users complain about
          </p>
          <div className="rounded-xl border border-card-border bg-card px-5 py-4">
            <ul className="space-y-2">
              {data.common_complaints.map((c, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-foreground/70">
                  <span className="text-skip mt-0.5 font-bold">-</span>
                  {c}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
