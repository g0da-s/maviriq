import type { GraveyardResearchOutput } from "@/lib/types";

const severityColor = {
  high: "text-skip",
  medium: "text-maybe",
  low: "text-muted",
};

const severityLabel = {
  high: "High risk",
  medium: "Medium risk",
  low: "Low risk",
};

export function GraveyardResearch({ data }: { data: GraveyardResearchOutput }) {
  return (
    <div className="space-y-6">
      {/* previous attempts — timeline style */}
      {data.previous_attempts.length > 0 && (
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted/60 mb-3">
            Companies that tried this
          </p>
          <div className="rounded-xl border border-card-border bg-card divide-y divide-card-border">
            {data.previous_attempts.map((attempt, i) => (
              <div key={i} className="px-5 py-4">
                <div className="flex items-baseline gap-2 mb-1.5">
                  <p className="text-sm font-semibold text-foreground/90">{attempt.name}</p>
                  {attempt.year && (
                    <span className="text-xs text-muted/50">{attempt.year}</span>
                  )}
                </div>
                <p className="text-sm text-foreground/70 mb-2">{attempt.what_they_did}</p>
                <p className="text-sm text-skip/90">
                  <span className="text-xs font-medium text-skip/60 uppercase">Why they failed:</span>{" "}
                  {attempt.shutdown_reason}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* failure reasons — numbered list, not red pill badges */}
      {data.failure_reasons.length > 0 && (
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted/60 mb-3">
            Common reasons for failure
          </p>
          <div className="rounded-xl border border-card-border bg-card px-5 py-4">
            <ol className="space-y-2">
              {data.failure_reasons.map((reason, i) => (
                <li key={i} className="flex items-start gap-3 text-sm text-foreground/80">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-skip/10 text-xs font-medium text-skip/70">
                    {i + 1}
                  </span>
                  {reason}
                </li>
              ))}
            </ol>
          </div>
        </div>
      )}

      {/* churn signals — clean table */}
      {data.churn_signals.length > 0 && (
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted/60 mb-3">
            Warning signs to watch for
          </p>
          <div className="rounded-xl border border-card-border bg-card divide-y divide-card-border">
            {data.churn_signals.map((sig, i) => (
              <div key={i} className="flex items-center justify-between px-5 py-3.5">
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-foreground/80">{sig.signal}</p>
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
