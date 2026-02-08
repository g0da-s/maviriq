import type { ViabilityOutput } from "@/lib/types";

const directionIcon = {
  positive: "+",
  negative: "-",
  neutral: "~",
};

const directionColor = {
  positive: "text-build",
  negative: "text-skip",
  neutral: "text-conditional",
};

export function Viability({ data }: { data: ViabilityOutput }) {
  const scorePercent = Math.round(data.opportunity_score * 100);

  return (
    <div className="space-y-5">
      {/* opportunity score */}
      <div className="flex items-center gap-4">
        <div className="relative h-20 w-20">
          <svg className="h-20 w-20 -rotate-90" viewBox="0 0 36 36">
            <circle
              cx="18" cy="18" r="15.5"
              fill="none" stroke="currentColor"
              className="text-white/5"
              strokeWidth="3"
            />
            <circle
              cx="18" cy="18" r="15.5"
              fill="none"
              className={scorePercent >= 60 ? "text-build" : scorePercent >= 40 ? "text-conditional" : "text-skip"}
              stroke="currentColor"
              strokeWidth="3"
              strokeDasharray={`${scorePercent} ${100 - scorePercent}`}
              strokeLinecap="round"
            />
          </svg>
          <span className="absolute inset-0 flex items-center justify-center font-display text-lg font-bold">
            {scorePercent}
          </span>
        </div>
        <div>
          <p className="font-display font-semibold">opportunity score</p>
          <p className="text-sm text-muted">
            {scorePercent >= 70 ? "strong opportunity" : scorePercent >= 50 ? "moderate opportunity" : "weak opportunity"}
          </p>
        </div>
      </div>

      {/* key metrics */}
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-xl border border-card-border bg-white/[0.02] p-4">
          <p className="text-xs text-muted/60 mb-1">will people pay?</p>
          <p className={`font-display font-bold ${data.people_pay ? "text-build" : "text-skip"}`}>
            {data.people_pay ? "yes" : "no"}
          </p>
          <p className="mt-1 text-xs text-muted/60 leading-relaxed">{data.people_pay_reasoning}</p>
        </div>
        <div className="rounded-xl border border-card-border bg-white/[0.02] p-4">
          <p className="text-xs text-muted/60 mb-1">reachability</p>
          <p className={`font-display font-bold ${
            data.reachability === "easy" ? "text-build" :
            data.reachability === "moderate" ? "text-conditional" : "text-skip"
          }`}>
            {data.reachability}
          </p>
          <p className="mt-1 text-xs text-muted/60 leading-relaxed">{data.reachability_reasoning}</p>
        </div>
      </div>

      {/* market gap */}
      <div className="rounded-xl border border-card-border bg-white/[0.02] p-4">
        <p className="text-xs text-muted/60 mb-1">
          market gap:{" "}
          <span className={`font-medium ${
            data.gap_size === "large" ? "text-build" :
            data.gap_size === "medium" ? "text-conditional" :
            data.gap_size === "small" ? "text-muted" : "text-skip"
          }`}>
            {data.gap_size}
          </span>
        </p>
        <p className="text-sm text-muted leading-relaxed">{data.market_gap}</p>
      </div>

      {/* signals */}
      {data.signals.length > 0 && (
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted/60 mb-3">
            signals
          </p>
          <div className="space-y-2">
            {data.signals.map((sig, i) => (
              <div key={i} className="flex items-start gap-3 rounded-lg border border-card-border bg-white/[0.02] p-3">
                <span className={`font-mono text-sm font-bold ${directionColor[sig.direction]}`}>
                  {directionIcon[sig.direction]}
                </span>
                <div className="flex-1">
                  <p className="text-sm">{sig.signal}</p>
                  <p className="mt-0.5 text-xs text-muted/50">{sig.source} &middot; {Math.round(sig.confidence * 100)}%</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* risk factors */}
      {data.risk_factors.length > 0 && (
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted/60 mb-3">
            risk factors
          </p>
          <div className="flex flex-wrap gap-2">
            {data.risk_factors.map((risk, i) => (
              <span key={i} className="rounded-full border border-skip/20 bg-skip/5 px-3 py-1 text-xs text-skip/80">
                {risk}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
