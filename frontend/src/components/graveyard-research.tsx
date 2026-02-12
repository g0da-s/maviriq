import type { GraveyardResearchOutput } from "@/lib/types";

const severityColor = {
  high: "text-skip",
  medium: "text-maybe",
  low: "text-muted",
};

const directionIcon = {
  positive: "+",
  negative: "-",
  neutral: "~",
};

const directionColor = {
  positive: "text-build",
  negative: "text-skip",
  neutral: "text-maybe",
};

export function GraveyardResearch({ data }: { data: GraveyardResearchOutput }) {
  return (
    <div className="space-y-5">
      {/* previous attempts */}
      {data.previous_attempts.length > 0 && (
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted/60 mb-3">
            previous attempts
          </p>
          <div className="space-y-2">
            {data.previous_attempts.map((attempt, i) => (
              <div key={i} className="rounded-lg border border-card-border bg-white/[0.02] p-3">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium">{attempt.name}</p>
                  {attempt.year && (
                    <span className="text-xs text-muted/40">{attempt.year}</span>
                  )}
                </div>
                <p className="mt-1 text-xs text-muted/60">{attempt.what_they_did}</p>
                <p className="mt-1 text-xs text-skip/80">
                  Shut down: {attempt.shutdown_reason}
                </p>
                <p className="mt-0.5 text-xs text-muted/40">{attempt.source}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* failure reasons */}
      {data.failure_reasons.length > 0 && (
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted/60 mb-3">
            common failure reasons
          </p>
          <div className="flex flex-wrap gap-2">
            {data.failure_reasons.map((reason, i) => (
              <span key={i} className="rounded-full border border-skip/20 bg-skip/5 px-3 py-1 text-xs text-skip/80">
                {reason}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* lessons learned */}
      {data.lessons_learned && (
        <div className="rounded-xl border border-card-border bg-white/[0.02] p-4">
          <p className="text-xs text-muted/60 mb-1">lessons learned</p>
          <p className="text-sm text-muted leading-relaxed">{data.lessons_learned}</p>
        </div>
      )}

      {/* churn signals */}
      {data.churn_signals.length > 0 && (
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted/60 mb-3">
            churn signals
          </p>
          <div className="space-y-2">
            {data.churn_signals.map((sig, i) => (
              <div key={i} className="flex items-start gap-3 rounded-lg border border-card-border bg-white/[0.02] p-3">
                <span className={`font-mono text-xs font-bold ${severityColor[sig.severity]}`}>
                  {sig.severity === "high" ? "!!!" : sig.severity === "medium" ? "!!" : "!"}
                </span>
                <div className="flex-1">
                  <p className="text-sm">{sig.signal}</p>
                  <p className="mt-0.5 text-xs text-muted/50">{sig.source}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* competitor health signals */}
      {data.competitor_health_signals.length > 0 && (
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted/60 mb-3">
            competitor health
          </p>
          <div className="space-y-2">
            {data.competitor_health_signals.map((sig, i) => (
              <div key={i} className="flex items-start gap-3 rounded-lg border border-card-border bg-white/[0.02] p-3">
                <span className={`font-mono text-sm font-bold ${directionColor[sig.direction]}`}>
                  {directionIcon[sig.direction]}
                </span>
                <div className="flex-1">
                  <p className="text-sm"><span className="font-medium">{sig.company}:</span> {sig.signal}</p>
                  <p className="mt-0.5 text-xs text-muted/50">{sig.source}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
