import type { MarketIntelligenceOutput } from "@/lib/types";

function isSafeUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

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
          <p className="text-sm text-muted">{data.market_size_estimate}</p>
        </div>
        <div className="rounded-xl border border-card-border bg-card p-5">
          <p className="text-sm font-semibold text-foreground mb-2">is it growing?</p>
          <p className={`text-sm ${growthColor[data.growth_direction]}`}>
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
        <div className="rounded-xl border border-card-border bg-card">
          <div className="px-5 pt-5 pb-3">
            <p className="text-sm font-semibold text-foreground">
              how to reach customers
            </p>
          </div>
          <div className="divide-y divide-card-border">
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
        <div className="rounded-xl border border-card-border bg-card">
          <div className="px-5 pt-5 pb-3">
            <p className="text-sm font-semibold text-foreground">
              investor activity in this space
            </p>
          </div>
          <div className="divide-y divide-card-border">
            {data.funding_signals.map((sig, i) => (
              <div key={i} className="px-5 py-3.5">
                <p className="text-sm text-muted">{typeof sig === "string" ? sig : sig.description}</p>
                {typeof sig === "object" && sig.source_url && isSafeUrl(sig.source_url) && (
                  <a href={sig.source_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 mt-1 text-xs text-muted/40 hover:text-muted/60">
                    source <span>&#8599;</span>
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
