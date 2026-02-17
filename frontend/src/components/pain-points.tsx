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

function SeverityBar({ severity }: { severity: number }) {
  const color = severity >= 4 ? "bg-skip" : severity >= 3 ? "bg-maybe" : "bg-muted/30";
  return (
    <div className="flex items-center gap-2 shrink-0">
      <span className="text-xs text-muted/50">{severity}/5</span>
      <div className="flex gap-0.5">
        {Array.from({ length: 5 }).map((_, j) => (
          <div
            key={j}
            className={`h-1.5 w-1.5 rounded-full ${j < severity ? color : "bg-white/10"}`}
          />
        ))}
      </div>
    </div>
  );
}

export function PainPoints({ data }: { data: PainDiscoveryOutput }) {
  return (
    <div className="space-y-6">
      {/* who has this pain — combined target user + segments */}
      <div className="rounded-xl border border-card-border bg-card">
        <div className="p-5">
          <p className="text-sm font-semibold text-foreground mb-3">
            who has this pain?
          </p>
          <p className="text-base font-bold text-foreground">{data.primary_target_user.label}</p>
          <p className="mt-1.5 text-sm text-muted">{data.primary_target_user.description}</p>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted/50">
            <span className="rounded-full bg-white/5 px-2.5 py-0.5">{wtpLabel[data.primary_target_user.willingness_to_pay]}</span>
            <span className="rounded-full bg-white/5 px-2.5 py-0.5">frequency: {data.primary_target_user.frequency}x</span>
          </div>
        </div>
        {data.user_segments.filter(seg => seg.label !== data.primary_target_user.label).length > 0 && (
          <div className="border-t border-card-border">
            <div className="px-5 pt-4 pb-1">
              <p className="text-xs font-medium text-muted/50 uppercase tracking-wider">also affected</p>
            </div>
            <div className="divide-y divide-card-border">
              {data.user_segments
                .filter(seg => seg.label !== data.primary_target_user.label)
                .map((seg, i) => (
                  <div key={i} className="flex items-center justify-between px-5 py-3">
                    <div>
                      <p className="text-sm text-foreground font-medium">{seg.label}</p>
                      <p className="text-xs text-muted/50 mt-0.5">{seg.description}</p>
                    </div>
                    <span className="text-xs text-muted/50 shrink-0 ml-4">
                      {wtpLabel[seg.willingness_to_pay]}
                    </span>
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>

      {/* pain points — evidence quotes */}
      {data.pain_points.length > 0 && (
        <div className="rounded-xl border border-card-border bg-card">
          <div className="px-5 pt-5 pb-3">
            <p className="text-sm font-semibold text-foreground">
              what people are saying ({data.pain_points.length} quotes found)
            </p>
          </div>
          <div className="divide-y divide-card-border">
            {data.pain_points.slice(0, 5).map((pp, i) => (
              <div key={i} className="px-5 py-4">
                <div className="flex items-start justify-between gap-4">
                  <p className="text-sm text-muted italic leading-relaxed">&ldquo;{pp.quote}&rdquo;</p>
                  <SeverityBar severity={pp.pain_severity} />
                </div>
                <div className="mt-2 flex items-center gap-2 text-xs text-muted/50">
                  {pp.source_url && isSafeUrl(pp.source_url) ? (
                    <a href={pp.source_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 hover:opacity-80">
                      <SourceBadge source={pp.source} />
                      <span className="text-muted/40">&#8599;</span>
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
    </div>
  );
}
