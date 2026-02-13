import type { MarketIntelligenceOutput } from "@/lib/types";

const growthColor = {
  growing: "text-build",
  stable: "text-maybe",
  shrinking: "text-skip",
  unknown: "text-muted",
};

const effortColor = {
  low: "text-build",
  medium: "text-maybe",
  high: "text-skip",
};

export function MarketIntelligence({ data }: { data: MarketIntelligenceOutput }) {
  return (
    <div className="space-y-5">
      {/* market size + growth */}
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-xl border border-card-border bg-white/[0.02] p-4">
          <p className="text-xs text-muted/60 mb-1">market size estimate</p>
          <p className="font-display font-bold text-sm">{data.market_size_estimate}</p>
        </div>
        <div className="rounded-xl border border-card-border bg-white/[0.02] p-4">
          <p className="text-xs text-muted/60 mb-1">growth direction</p>
          <p className={`font-display font-bold ${growthColor[data.growth_direction]}`}>
            {data.growth_direction}
          </p>
        </div>
      </div>

      {/* TAM reasoning */}
      <div className="rounded-xl border border-card-border bg-white/[0.02] p-4">
        <p className="text-xs text-muted/60 mb-1">tam reasoning</p>
        <p className="text-sm text-muted leading-relaxed">{data.tam_reasoning}</p>
      </div>

      {/* distribution channels */}
      {data.distribution_channels.length > 0 && (
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted/60 mb-3">
            distribution channels
          </p>
          <div className="space-y-2">
            {data.distribution_channels.map((ch, i) => (
              <div key={i} className="flex items-start gap-3 rounded-lg border border-card-border bg-white/[0.02] p-3">
                <div className="flex-1">
                  <p className="text-sm font-medium">{ch.channel}</p>
                  <p className="mt-0.5 text-xs text-muted/50">{ch.reach_estimate}</p>
                </div>
                <span className={`rounded-full border px-2 py-0.5 text-xs ${effortColor[ch.effort]} border-current/20`}>
                  {ch.effort} effort
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* funding signals */}
      {data.funding_signals.length > 0 && (
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted/60 mb-3">
            funding signals
          </p>
          <div className="space-y-2">
            {data.funding_signals.map((sig, i) => (
              <div key={i} className="rounded-lg border border-card-border bg-white/[0.02] p-3">
                <p className="text-sm">{sig}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
