import type { SynthesisOutput } from "@/lib/types";
import { VerdictBadge } from "./verdict-badge";

export function Synthesis({ data }: { data: SynthesisOutput }) {
  return (
    <div className="rounded-2xl border border-card-border bg-card p-6">
      <div className="mb-4 flex items-center gap-3">
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-build/10 text-xs font-bold text-build">
          4
        </span>
        <h3 className="font-display text-lg font-semibold">synthesis & verdict</h3>
      </div>

      {/* verdict hero */}
      <div className="mb-6 rounded-xl border border-card-border bg-white/[0.02] p-6 text-center">
        <VerdictBadge verdict={data.verdict} size="lg" />
        <p className="mt-3 font-display text-lg font-semibold">
          {Math.round(data.confidence * 100)}% confidence
        </p>
        <p className="mt-2 text-sm text-muted leading-relaxed">{data.one_line_summary}</p>
      </div>

      {/* reasoning */}
      <div className="mb-6">
        <p className="text-xs font-medium uppercase tracking-wider text-muted/60 mb-2">
          reasoning
        </p>
        <p className="text-sm text-muted leading-relaxed">{data.reasoning}</p>
      </div>

      {/* strengths & risks */}
      <div className="mb-6 grid gap-4 sm:grid-cols-2">
        {data.key_strengths.length > 0 && (
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-build/70 mb-2">
              key strengths
            </p>
            <ul className="space-y-1.5">
              {data.key_strengths.map((s, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-muted">
                  <span className="mt-1 text-build">+</span>
                  {s}
                </li>
              ))}
            </ul>
          </div>
        )}
        {data.key_risks.length > 0 && (
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-skip/70 mb-2">
              key risks
            </p>
            <ul className="space-y-1.5">
              {data.key_risks.map((r, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-muted">
                  <span className="mt-1 text-skip">-</span>
                  {r}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* target user & market */}
      <div className="mb-6 grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl border border-card-border bg-white/[0.02] p-4">
          <p className="text-xs text-muted/60 mb-1">target user</p>
          <p className="text-sm">{data.target_user_summary}</p>
        </div>
        <div className="rounded-xl border border-card-border bg-white/[0.02] p-4">
          <p className="text-xs text-muted/60 mb-1">estimated market size</p>
          <p className="text-sm">{data.estimated_market_size}</p>
        </div>
      </div>

      {/* recommended mvp */}
      {data.recommended_mvp && (
        <div className="mb-6 rounded-xl border border-build/20 bg-build/5 p-4">
          <p className="text-xs font-medium uppercase tracking-wider text-build/70 mb-2">
            recommended mvp
          </p>
          <p className="text-sm text-foreground/90 leading-relaxed">{data.recommended_mvp}</p>
        </div>
      )}

      {/* positioning */}
      {data.recommended_positioning && (
        <div className="mb-6 rounded-xl border border-card-border bg-white/[0.02] p-4">
          <p className="text-xs text-muted/60 mb-1">recommended positioning</p>
          <p className="text-sm text-muted leading-relaxed">{data.recommended_positioning}</p>
        </div>
      )}

      {/* next steps */}
      {data.next_steps.length > 0 && (
        <>
          <p className="text-xs font-medium uppercase tracking-wider text-muted/60 mb-3">
            next steps
          </p>
          <ol className="space-y-2">
            {data.next_steps.map((step, i) => (
              <li key={i} className="flex items-start gap-3 text-sm text-muted">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white/5 text-xs font-medium">
                  {i + 1}
                </span>
                {step}
              </li>
            ))}
          </ol>
        </>
      )}
    </div>
  );
}
