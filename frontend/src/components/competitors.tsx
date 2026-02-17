import type { CompetitorResearchOutput } from "@/lib/types";

function isSafeUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

export function Competitors({ data }: { data: CompetitorResearchOutput }) {
  return (
    <div className="space-y-6">
      {/* competitor cards */}
      {data.competitors.length > 0 && (
        <div>
          <div className="rounded-xl border border-card-border bg-card divide-y divide-card-border">
            {data.competitors.map((comp, i) => (
              <div key={i} className="px-5 py-4">
                {/* header row */}
                <div className="flex items-start justify-between mb-1.5">
                  <div>
                    {comp.url && isSafeUrl(comp.url) ? (
                      <a href={comp.url} target="_blank" rel="noopener noreferrer" className="text-sm font-semibold text-foreground hover:underline">
                        {comp.name}<span className="ml-1 text-muted/40 text-xs">&#8599;</span>
                      </a>
                    ) : (
                      <p className="text-sm font-semibold text-foreground">{comp.name}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="rounded-full border border-white/10 px-2.5 py-0.5 text-[10px] font-medium text-muted/60">
                      {comp.competitor_type}
                    </span>
                  </div>
                </div>

                {/* description */}
                <p className="text-sm text-muted mb-3">{comp.one_liner}</p>

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
                        <p className="text-sm font-semibold text-foreground mb-1.5">what they do well</p>
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
                        <p className="text-sm font-semibold text-foreground mb-1.5">where they fall short</p>
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

      {/* underserved needs */}
      {data.underserved_needs.length > 0 && (
        <div className="rounded-xl border border-card-border bg-card">
          <div className="px-5 pt-5 pb-3">
            <p className="text-sm font-semibold text-foreground">
              gaps competitors aren&apos;t filling
            </p>
          </div>
          <div className="px-5 pb-4">
            <ul className="space-y-2">
              {data.underserved_needs.map((need, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-muted">
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
        <div className="rounded-xl border border-card-border bg-card">
          <div className="px-5 pt-5 pb-3">
            <p className="text-sm font-semibold text-foreground">
              what users complain about
            </p>
          </div>
          <div className="px-5 pb-4">
            <ul className="space-y-2">
              {data.common_complaints.map((c, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-muted">
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
