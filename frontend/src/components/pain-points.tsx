import type { PainDiscoveryOutput } from "@/lib/types";

export function PainPoints({ data }: { data: PainDiscoveryOutput }) {
  return (
    <div className="space-y-5">
      {/* summary */}
      <p className="text-sm text-muted leading-relaxed">{data.pain_summary}</p>

      {/* target user */}
      <div className="rounded-xl border border-card-border bg-white/[0.02] p-4">
        <p className="text-xs font-medium uppercase tracking-wider text-muted/60 mb-2">
          primary target user
        </p>
        <p className="font-display font-semibold">{data.primary_target_user.label}</p>
        <p className="mt-1 text-sm text-muted">{data.primary_target_user.description}</p>
        <div className="mt-2 flex flex-wrap gap-2">
          <span className="rounded-full bg-white/5 px-3 py-0.5 text-xs text-muted">
            willingness to pay: {data.primary_target_user.willingness_to_pay}
          </span>
          <span className="rounded-full bg-white/5 px-3 py-0.5 text-xs text-muted">
            frequency: {data.primary_target_user.frequency}
          </span>
        </div>
      </div>

      {/* pain points */}
      <div>
        <p className="text-xs font-medium uppercase tracking-wider text-muted/60 mb-3">
          pain points ({data.pain_points.length})
        </p>
        <div className="space-y-3">
          {data.pain_points.slice(0, 5).map((pp, i) => (
            <div key={i} className="rounded-xl border border-card-border bg-white/[0.02] p-4">
              <div className="flex items-start justify-between gap-4">
                <p className="text-sm text-foreground/90 italic">&ldquo;{pp.quote}&rdquo;</p>
                <div className="flex shrink-0 items-center gap-1">
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
              <div className="mt-2 flex items-center gap-2 text-xs text-muted/60">
                {pp.source_url ? (
                  <a href={pp.source_url} target="_blank" rel="noopener noreferrer" className="hover:underline">
                    {pp.source} <span className="text-muted/30">↗</span>
                  </a>
                ) : (
                  <span>{pp.source}</span>
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

      {/* user segments */}
      {data.user_segments.length > 1 && (
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted/60 mb-3">
            user segments ({data.user_segments.length})
          </p>
          <div className="grid gap-2 sm:grid-cols-2">
            {data.user_segments.map((seg, i) => (
              <div key={i} className="rounded-lg border border-card-border bg-white/[0.02] p-3">
                <p className="text-sm font-medium">{seg.label}</p>
                <p className="mt-1 text-xs text-muted/60">wtp: {seg.willingness_to_pay}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
