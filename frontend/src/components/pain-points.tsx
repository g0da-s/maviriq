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

const wtpRank = { high: 3, medium: 2, low: 1 } as const;

const severityRank = { critical: 4, major: 3, moderate: 2, minor: 1 } as const;

export function PainPoints({ data }: { data: PainDiscoveryOutput }) {
  const allSegments = [data.primary_target_user, ...data.user_segments.filter(seg => seg.label !== data.primary_target_user.label)]
    .sort((a, b) => wtpRank[b.willingness_to_pay] - wtpRank[a.willingness_to_pay]);

  const sortedQuotes = [...data.pain_points]
    .sort((a, b) => severityRank[b.pain_severity] - severityRank[a.pain_severity]);

  return (
    <div className="space-y-6">
      {/* who has this pain — combined target user + segments */}
      <div className="rounded-xl border border-card-border bg-card">
        <div className="px-5 pt-5 pb-3">
          <p className="text-sm font-semibold text-foreground">
            who has this pain?
          </p>
        </div>
        <div className="divide-y divide-card-border">
          {allSegments.map((seg, i) => (
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

      {/* pain points — evidence quotes */}
      {sortedQuotes.length > 0 && (
        <div className="rounded-xl border border-card-border bg-card">
          <div className="px-5 pt-5 pb-3">
            <p className="text-sm font-semibold text-foreground">
              what people are saying ({data.pain_points.length} quotes found)
            </p>
          </div>
          <div className="divide-y divide-card-border">
            {sortedQuotes.slice(0, 5).map((pp, i) => (
              <div key={i} className="px-5 py-4">
                <div>
                  <p className="text-sm text-muted italic leading-relaxed">&ldquo;{pp.quote}&rdquo;</p>
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
