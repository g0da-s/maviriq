import type { GraveyardResearchOutput } from "@/lib/types";

export function GraveyardResearch({ data }: { data: GraveyardResearchOutput }) {
  return (
    <div className="space-y-6">
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
    </div>
  );
}
