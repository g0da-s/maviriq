import type { MarketIntelligenceOutput } from "@/lib/types";

const growthColor = {
  growing: "text-build",
  stable: "text-maybe",
  shrinking: "text-skip",
  unknown: "text-muted",
};

const growthLabel = {
  growing: "market is growing",
  stable: "market is stable",
  shrinking: "market is shrinking",
  unknown: "growth unknown",
};

const effortLabel = {
  low: "easy to reach",
  medium: "moderate effort",
  high: "hard to reach",
};

const effortColor = {
  low: "text-build",
  medium: "text-maybe",
  high: "text-skip",
};

export function MarketIntelligence({ data }: { data: MarketIntelligenceOutput }) {
  return (
    <div className="space-y-6">
      {/* headline stats */}
      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-xl border border-card-border bg-card p-5">
          <p className="text-sm font-semibold text-foreground mb-2">how big is this market?</p>
          <p className="font-display text-lg font-bold">{data.market_size_estimate}</p>
        </div>
        <div className="rounded-xl border border-card-border bg-card p-5">
          <p className="text-sm font-semibold text-foreground mb-2">is it growing?</p>
          <p className={`font-display text-lg font-bold ${growthColor[data.growth_direction]}`}>
            {growthLabel[data.growth_direction]}
          </p>
        </div>
      </div>

      {/* TAM reasoning */}
      <div className="rounded-xl border border-card-border bg-card p-5">
        <p className="text-sm font-semibold text-foreground mb-3">
          why this size?
        </p>
        <p className="text-sm text-muted leading-relaxed">{data.tam_reasoning}</p>
      </div>

      {/* distribution channels */}
      {data.distribution_channels.length > 0 && (
        <div>
          <p className="text-sm font-semibold text-foreground mb-3">
            how to reach customers
          </p>
          <div className="rounded-xl border border-card-border bg-card divide-y divide-card-border">
            {data.distribution_channels.map((ch, i) => (
              <div key={i} className="flex items-center justify-between px-5 py-3.5">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground/90">{ch.channel}</p>
                  <p className="text-xs text-muted/50 mt-0.5">{ch.reach_estimate}</p>
                </div>
                <span className={`text-xs font-medium ${effortColor[ch.effort]}`}>
                  {effortLabel[ch.effort]}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* funding signals */}
      {data.funding_signals.length > 0 && (
        <div>
          <p className="text-sm font-semibold text-foreground mb-3">
            investor activity in this space
          </p>
          <div className="rounded-xl border border-card-border bg-card divide-y divide-card-border">
            {data.funding_signals.map((sig, i) => (
              <div key={i} className="px-5 py-3.5">
                <p className="text-sm text-muted">{sig}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
