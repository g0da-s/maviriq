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
  growing: "growing",
  stable: "stable",
  shrinking: "shrinking",
  unknown: "unknown",
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
        <div className="rounded-xl border border-card-border bg-card">
          <div className="px-5 py-3 border-b border-card-border">
            <p className="text-xs font-medium uppercase tracking-wider text-muted/50">market size (TAM)</p>
          </div>
          <div className="px-5 py-4">
            <p className="text-sm text-muted">{data.market_size_estimate}</p>
          </div>
        </div>
        <div className="rounded-xl border border-card-border bg-card">
          <div className="px-5 py-3 border-b border-card-border">
            <p className="text-xs font-medium uppercase tracking-wider text-muted/50">market growth</p>
          </div>
          <div className="px-5 py-4">
            <p className={`text-sm ${growthColor[data.growth_direction]}`}>
              {growthLabel[data.growth_direction]}
            </p>
          </div>
        </div>
      </div>

      {/* TAM reasoning */}
      <div className="rounded-xl border border-card-border bg-card">
        <div className="px-5 py-3 border-b border-card-border">
          <p className="text-xs font-medium uppercase tracking-wider text-muted/50">why this size?</p>
        </div>
        <div className="px-5 py-4">
          <p className="text-sm text-muted leading-relaxed">{data.tam_reasoning}</p>
        </div>
      </div>

      {/* distribution channels */}
      {data.distribution_channels.length > 0 && (
        <div className="rounded-xl border border-card-border bg-card">
          <div className="px-5 py-3 border-b border-card-border">
            <p className="text-xs font-medium uppercase tracking-wider text-muted/50">how to reach customers</p>
          </div>
          <div className="px-5 py-4 space-y-3">
            {data.distribution_channels.map((ch, i) => (
              <div key={i} className="flex items-center justify-between">
                <p className="text-sm font-medium text-foreground/90">{ch.channel}</p>
                <span className={`text-xs font-medium shrink-0 ml-4 ${effortColor[ch.effort]}`}>
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
          <div className="px-5 py-3 border-b border-card-border">
            <p className="text-xs font-medium uppercase tracking-wider text-muted/50">investor activity in this space</p>
          </div>
          <div className="px-5 py-4 space-y-3">
            {data.funding_signals.map((sig, i) => (
              <div key={i}>
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
