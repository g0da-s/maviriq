import type { GraveyardResearchOutput } from "@/lib/types";

const severityColor = {
  high: "text-skip",
  medium: "text-maybe",
  low: "text-muted",
};

const severityLabel = {
  high: "high risk",
  medium: "medium risk",
  low: "low risk",
};

export function GraveyardResearch({ data }: { data: GraveyardResearchOutput }) {
  return (
    <div className="space-y-6">
      {/* previous attempts */}
      {data.previous_attempts.length > 0 && (
        <div className="rounded-xl border border-card-border bg-card">
          <div className="px-5 py-3 border-b border-card-border">
            <p className="text-xs font-medium uppercase tracking-wider text-muted/50">companies that tried this</p>
          </div>
          <div className="px-5 py-4 space-y-4">
            {data.previous_attempts.map((attempt, i) => (
              <div key={i}>
                <div className="flex items-baseline gap-2 mb-1.5">
                  <p className="text-sm font-semibold text-foreground">{attempt.name}</p>
                  {attempt.year && (
                    <span className="text-xs text-muted/50">{attempt.year}</span>
                  )}
                </div>
                <p className="text-sm text-muted mb-2">{attempt.what_they_did}</p>
                <p className="text-sm text-muted">
                  <span className="text-xs text-muted">why they failed:</span>{" "}
                  {attempt.shutdown_reason}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* failure reasons */}
      {data.failure_reasons.length > 0 && (
        <div className="rounded-xl border border-card-border bg-card">
          <div className="px-5 py-3 border-b border-card-border">
            <p className="text-xs font-medium uppercase tracking-wider text-muted/50">common reasons for failure</p>
          </div>
          <ol className="px-5 py-4 space-y-2">
            {data.failure_reasons.map((reason, i) => (
              <li key={i} className="flex items-start gap-3 text-sm text-muted">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white/10 text-xs font-medium text-muted">
                  {i + 1}
                </span>
                {reason}
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* churn signals */}
      {data.churn_signals.length > 0 && (
        <div className="rounded-xl border border-card-border bg-card">
          <div className="px-5 py-3 border-b border-card-border">
            <p className="text-xs font-medium uppercase tracking-wider text-muted/50">warning signs to watch for</p>
          </div>
          <div className="px-5 py-4 space-y-3">
            {data.churn_signals.map((sig, i) => (
              <div key={i} className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-muted">{sig.signal}</p>
                  <p className="text-xs text-muted/40 mt-0.5">{sig.source}</p>
                </div>
                <span className={`text-xs font-medium shrink-0 ml-4 ${severityColor[sig.severity]}`}>
                  {severityLabel[sig.severity]}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
