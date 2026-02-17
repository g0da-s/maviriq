import type { PainDiscoveryOutput } from "@/lib/types";

function isSafeUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

const sourceLabels: Record<string, { label: string; color: string }> = {
  reddit: { label: "Reddit", color: "border-orange-500/30 text-orange-400" },
  hackernews: { label: "Hacker News", color: "border-amber-500/30 text-amber-400" },
  twitter: { label: "X / Twitter", color: "border-sky-500/30 text-sky-400" },
  youtube: { label: "YouTube", color: "border-red-500/30 text-red-400" },
  google_news: { label: "News", color: "border-blue-500/30 text-blue-400" },
  producthunt: { label: "Product Hunt", color: "border-orange-400/30 text-orange-300" },
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

const wtpLabel = {
  high: "willing to pay a lot",
  medium: "willing to pay some",
  low: "price sensitive",
};

export function PainPoints({ data }: { data: PainDiscoveryOutput }) {
  return (
    <div className="space-y-6">
      {/* target user */}
      <div className="rounded-xl border border-card-border bg-card p-5">
        <p className="text-sm font-semibold text-foreground mb-3">
          who has this pain?
        </p>
        <p className="text-sm font-semibold text-foreground">{data.primary_target_user.label}</p>
        <p className="mt-1.5 text-sm text-muted">{data.primary_target_user.description}</p>
        <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted">
          <span>{wtpLabel[data.primary_target_user.willingness_to_pay]}</span>
          <span className="text-muted/30">|</span>
          <span>frequency: {data.primary_target_user.frequency}x</span>
        </div>
      </div>

      {/* pain points — evidence quotes */}
      {data.pain_points.length > 0 && (
        <div>
          <p className="text-sm font-semibold text-foreground mb-3">
            what people are saying ({data.pain_points.length} quotes found)
          </p>
          <div className="rounded-xl border border-card-border bg-card divide-y divide-card-border">
            {data.pain_points.slice(0, 5).map((pp, i) => (
              <div key={i} className="px-5 py-4">
                <div className="flex items-start justify-between gap-4">
                  <p className="text-sm text-muted italic leading-relaxed">&ldquo;{pp.quote}&rdquo;</p>
                  <div className="flex shrink-0 items-center gap-0.5 mt-1">
                    {Array.from({ length: 5 }).map((_, j) => (
                      <div
                        key={j}
                        className={`h-1.5 w-1.5 rounded-full ${
                          j < pp.pain_severity ? "bg-skip" : "bg-white/10"
                        }`}
                      />
                    ))}
                  </div>
                </div>
                <div className="mt-2 flex items-center gap-2 text-xs text-muted/50">
                  {pp.source_url && isSafeUrl(pp.source_url) ? (
                    <a href={pp.source_url} target="_blank" rel="noopener noreferrer" className="hover:opacity-80">
                      <SourceBadge source={pp.source} />
                    </a>
                  ) : (
                    <SourceBadge source={pp.source} />
                  )}
                  {pp.author_context && (
                    <>
                      <span>&middot;</span>
                      <span>{pp.author_context}</span>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* user segments */}
      {data.user_segments.length > 1 && (
        <div>
          <p className="text-sm font-semibold text-foreground mb-3">
            other user groups affected
          </p>
          <div className="rounded-xl border border-card-border bg-card divide-y divide-card-border">
            {data.user_segments.map((seg, i) => (
              <div key={i} className="flex items-center justify-between px-5 py-3.5">
                <div>
                  <p className="text-sm font-medium text-foreground/90">{seg.label}</p>
                  <p className="text-xs text-muted/50 mt-0.5">{seg.description}</p>
                </div>
                <span className="text-xs text-muted shrink-0 ml-4">
                  {wtpLabel[seg.willingness_to_pay]}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
