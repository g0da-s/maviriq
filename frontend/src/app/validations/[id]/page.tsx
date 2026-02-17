"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { getValidation } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { ValidationRun } from "@/lib/types";
import { PipelineProgress } from "@/components/pipeline-progress";
import { VerdictBadge } from "@/components/verdict-badge";
import { PainPoints } from "@/components/pain-points";
import { Competitors } from "@/components/competitors";
import { MarketIntelligence } from "@/components/market-intelligence";
import { GraveyardResearch } from "@/components/graveyard-research";
import { Viability } from "@/components/viability";

export default function ValidationPage() {
  const { id } = useParams<{ id: string }>();
  const [run, setRun] = useState<ValidationRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const { user, session, loading: authLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
      return;
    }
    if (!session) return;

    let cancelled = false;

    async function load() {
      const MAX_RETRIES = 3;
      const RETRY_DELAY = 1500;

      for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
        if (cancelled) return;
        try {
          const data = await getValidation(id);
          if (cancelled) return;
          setRun(data);
          if (data.status === "running" || data.status === "pending") {
            setIsStreaming(true);
          }
          setLoading(false);
          return;
        } catch (err) {
          const is404 = err instanceof Error && err.message.includes("404");
          if (is404 && attempt < MAX_RETRIES) {
            await new Promise((r) => setTimeout(r, RETRY_DELAY));
            continue;
          }
          if (cancelled) return;
          if (is404) {
            setError("validation not found");
          } else {
            setError(err instanceof Error ? err.message : "failed to load validation");
          }
          setLoading(false);
          return;
        }
      }
    }
    load();
    return () => { cancelled = true; };
  }, [id, session, authLoading, user, router]);

  const handleComplete = useCallback((completedRun: ValidationRun) => {
    setRun(completedRun);
    setIsStreaming(false);
  }, []);

  const handleError = useCallback((errMsg: string) => {
    setError(errMsg);
    setIsStreaming(false);
  }, []);

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl px-6 pt-28 pb-16">
        <div className="h-4 w-28 animate-pulse rounded bg-white/5" />
        <div className="mt-6 space-y-2">
          <div className="h-8 w-2/3 animate-pulse rounded bg-white/5" />
          <div className="mt-5 flex items-start gap-5 rounded-2xl border border-card-border bg-card px-6 py-5">
            <div className="flex flex-col items-center shrink-0 gap-3">
              <div className="h-12 w-16 animate-pulse rounded bg-white/5" />
              <div className="h-6 w-20 animate-pulse rounded-full bg-white/5" />
            </div>
            <div className="flex-1 space-y-2 pt-1">
              <div className="h-4 w-full animate-pulse rounded bg-white/5" />
              <div className="h-4 w-4/5 animate-pulse rounded bg-white/5" />
            </div>
          </div>
        </div>
        <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-card-border bg-card p-4 text-center space-y-2">
              <div className="mx-auto h-3 w-16 animate-pulse rounded bg-white/5" />
              <div className="mx-auto h-7 w-12 animate-pulse rounded bg-white/5" />
            </div>
          ))}
        </div>
        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className="rounded-2xl border border-card-border bg-card p-5 space-y-3">
              <div className="h-3 w-20 animate-pulse rounded bg-white/5" />
              <div className="h-4 w-full animate-pulse rounded bg-white/5" />
              <div className="h-4 w-5/6 animate-pulse rounded bg-white/5" />
              <div className="h-4 w-3/4 animate-pulse rounded bg-white/5" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error && !isStreaming) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 pt-20">
        <p role="alert" className="text-skip">{error}</p>
        <button
          onClick={() => {
            setError("");
            setLoading(true);
            router.refresh();
          }}
          className="rounded-lg border border-card-border px-4 py-2 text-sm text-muted transition-colors hover:bg-white/5"
        >
          retry
        </button>
        <Link href="/" className="text-sm text-muted/50 hover:text-foreground transition-colors">
          go home
        </Link>
      </div>
    );
  }

  if (isStreaming) {
    return (
      <div className="mx-auto max-w-2xl px-6 pt-28 pb-16">
        <div className="mb-8 text-center">
          <h1 className="font-display text-3xl font-bold">
            {run?.idea || "validating..."}
          </h1>
          <p className="mt-2 text-sm text-muted">researching your idea across the internet</p>
        </div>
        <PipelineProgress
          runId={id}
          onComplete={handleComplete}
          onError={handleError}
        />
      </div>
    );
  }

  if (!run) return null;

  const s = run.synthesis;
  const pain = run.pain_discovery;
  const comp = run.competitor_research;
  const mktIntel = run.market_intelligence;
  const graveyard = run.graveyard_research;
  const via = run.viability;

  const avgSeverity = pain && pain.pain_points.length > 0
    ? (pain.pain_points.reduce((sum, p) => sum + p.pain_severity, 0) / pain.pain_points.length)
    : 0;

  return (
    <div className="mx-auto max-w-4xl px-6 pt-28 pb-16">
      {/* back link + date */}
      <div className="flex items-center justify-between">
        <Link href="/validations" className="text-sm text-muted hover:text-foreground transition-colors">
          &larr; back to history
        </Link>
        {run.completed_at && (
          <span className="text-xs text-muted/40">
            {new Date(run.completed_at).toLocaleDateString()}
          </span>
        )}
      </div>

      {/* ═══ 1. VERDICT HERO ═══ */}
      <div className="mt-6">
        <h1 className="font-display text-3xl font-bold leading-tight">{run.idea}</h1>

        {s && (
          <div className="mt-5 rounded-2xl border border-card-border bg-card px-6 py-6">
            <div className="flex items-center gap-6">
              <div className="flex flex-col items-start shrink-0">
                <span className={`font-display text-6xl font-bold leading-none ${
                  Math.round(s.confidence * 100) >= 70 ? "text-build" :
                  Math.round(s.confidence * 100) >= 40 ? "text-maybe" : "text-skip"
                }`}>
                  {Math.round(s.confidence * 100)}<span className="text-3xl">%</span>
                </span>
                <div className="mt-2">
                  <VerdictBadge verdict={s.verdict} size="md" />
                </div>
              </div>
              <p className="text-sm text-muted leading-relaxed lowercase">
                {s.one_line_summary}
              </p>
            </div>
          </div>
        )}

        {run.status === "failed" && !s && (
          <div className="mt-5 flex items-center gap-3 rounded-2xl border border-skip/30 bg-skip/5 px-6 py-5">
            <span className="rounded-full border border-skip px-3 py-0.5 text-xs text-skip font-display font-bold">
              failed
            </span>
            {run.error && <p className="text-sm text-muted">{run.error}</p>}
          </div>
        )}
      </div>

      {/* ═══ 2. KEY METRICS ═══ */}
      <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {pain && (
          <div className="rounded-xl border border-card-border bg-card p-4 text-center">
            <p className="text-xs font-medium text-foreground/80">pain severity</p>
            {pain.pain_points.length > 0 ? (
              <p className="mt-1 font-display text-2xl font-bold">
                {avgSeverity.toFixed(1)}<span className="text-sm text-muted/40">/5</span>
              </p>
            ) : (
              <p className="mt-1 font-display text-lg font-bold text-muted/40">N/A</p>
            )}
          </div>
        )}
        {comp && (
          <div className="rounded-xl border border-card-border bg-card p-4 text-center">
            <p className="text-xs font-medium text-foreground/80">competition</p>
            <p className={`mt-1 font-display text-2xl font-bold ${
              comp.market_saturation === "high" ? "text-skip" :
              comp.market_saturation === "medium" ? "text-maybe" : "text-build"
            }`}>
              {comp.market_saturation}
            </p>
          </div>
        )}
        {(s || via) && (
          <div className="rounded-xl border border-card-border bg-card p-4 text-center">
            <p className="text-xs font-medium text-foreground/80">will pay?</p>
            <p className={`mt-1 font-display text-2xl font-bold ${(s?.people_pay ?? via?.people_pay) ? "text-build" : "text-skip"}`}>
              {(s?.people_pay ?? via?.people_pay) ? "yes" : "no"}
            </p>
          </div>
        )}
        {(s || via) && (
          <div className="rounded-xl border border-card-border bg-card p-4 text-center">
            <p className="text-xs font-medium text-foreground/80">market gap</p>
            {(() => {
              const gapSize = s?.gap_size ?? via?.gap_size;
              return (
                <p className={`mt-1 font-display text-2xl font-bold ${
                  gapSize === "large" ? "text-build" :
                  gapSize === "medium" ? "text-maybe" :
                  gapSize === "small" ? "text-muted" : "text-skip"
                }`}>
                  {gapSize}
                </p>
              );
            })()}
          </div>
        )}
        {mktIntel && (
          <div className="rounded-xl border border-card-border bg-card p-4 text-center">
            <p className="text-xs font-medium text-foreground/80">growth</p>
            <p className={`mt-1 font-display text-2xl font-bold ${
              mktIntel.growth_direction === "growing" ? "text-build" :
              mktIntel.growth_direction === "stable" ? "text-maybe" :
              mktIntel.growth_direction === "shrinking" ? "text-skip" : "text-muted"
            }`}>
              {mktIntel.growth_direction}
            </p>
          </div>
        )}
        {graveyard && (
          <div className="rounded-xl border border-card-border bg-card p-4 text-center">
            <p className="text-xs font-medium text-foreground/80">dead startups</p>
            <p className={`mt-1 font-display text-2xl font-bold ${
              graveyard.previous_attempts.length > 0 ? "text-skip" : "text-muted"
            }`}>
              {graveyard.previous_attempts.length}
            </p>
          </div>
        )}
      </div>

      {/* ═══ 3. STRENGTHS vs RISKS ═══ */}
      {s && (s.key_strengths.length > 0 || s.key_risks.length > 0) && (
        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          {s.key_strengths.length > 0 && (
            <div className="rounded-2xl border border-card-border bg-card p-5 border-l-2 border-l-build">
              <p className="text-sm font-semibold text-foreground mb-3">why this could work</p>
              <ul className="space-y-2">
                {s.key_strengths.map((str, i) => (
                  <li key={i} className="text-sm text-muted leading-relaxed">
                    {str}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {s.key_risks.length > 0 && (
            <div className="rounded-2xl border border-card-border bg-card p-5 border-l-2 border-l-skip">
              <p className="text-sm font-semibold text-foreground mb-3">what could kill it</p>
              <ul className="space-y-2">
                {s.key_risks.map((risk, i) => (
                  <li key={i} className="text-sm text-muted leading-relaxed">
                    {risk}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* ═══ 4. ACTION PLAN — moved up, before research ═══ */}
      {s && (
        <div className="mt-10">
          <h2 className="text-lg font-semibold text-foreground mb-5">
            What to Do Next
          </h2>

          <div className="grid gap-3 sm:grid-cols-2 mb-4">
            <div className="rounded-xl border border-card-border bg-card p-4">
              <p className="text-sm font-semibold text-foreground mb-1">target user</p>
              <p className="text-sm text-muted">{s.target_user_summary}</p>
            </div>
            <div className="rounded-xl border border-card-border bg-card p-4">
              <p className="text-sm font-semibold text-foreground mb-1">market size</p>
              <p className="text-sm text-muted">{s.estimated_market_size}</p>
            </div>
          </div>

          {s.recommended_mvp && (
            <div className="mb-4 rounded-2xl border border-card-border bg-card p-6">
              <p className="text-sm font-semibold text-foreground mb-2">
                what to build first
              </p>
              <p className="text-sm text-muted leading-relaxed">{s.recommended_mvp}</p>
            </div>
          )}

          {s.differentiation_strategy && (
            <div className="mb-4 rounded-2xl border border-card-border bg-card p-6">
              <p className="text-sm font-semibold text-foreground mb-2">
                differentiation strategy
              </p>
              <p className="text-sm text-muted leading-relaxed">{s.differentiation_strategy}</p>
            </div>
          )}

          {s.lessons_from_failures && (
            <div className="mb-4 rounded-2xl border border-card-border bg-card p-6">
              <p className="text-sm font-semibold text-foreground mb-2">
                lessons from past failures
              </p>
              <p className="text-sm text-muted leading-relaxed">{s.lessons_from_failures}</p>
              {s.previous_attempts_summary && (
                <div className="mt-3 pt-3 border-t border-card-border">
                  <p className="text-sm font-semibold text-foreground mb-1">previous attempts</p>
                  <p className="text-sm text-muted leading-relaxed">{s.previous_attempts_summary}</p>
                </div>
              )}
            </div>
          )}

          {s.next_steps.length > 0 && (
            <div className="rounded-2xl border border-card-border bg-card p-6">
              <p className="text-sm font-semibold text-foreground mb-3">
                next steps
              </p>
              <ol className="space-y-2.5">
                {s.next_steps.map((step, i) => (
                  <li key={i} className="flex items-start gap-3 text-sm text-muted">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white/10 text-xs font-medium text-muted">
                      {i + 1}
                    </span>
                    {step}
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}

      {/* ═══ 5. THE RESEARCH — single source of truth, no duplicate section ═══ */}
      <div className="mt-14">
        <h2 className="text-lg font-semibold text-foreground mb-8">
          The Research
        </h2>

        {/* — The Pain — */}
        {pain && (
          <section className="mb-12">
            <h3 className="text-base font-semibold text-foreground mb-2">
              The Pain
            </h3>
            <p className="text-muted leading-relaxed mb-5">{pain.pain_summary}</p>
            <PainPoints data={pain} />
          </section>
        )}

        {/* — The Competition — */}
        {comp && (
          <section className="mb-12">
            <h3 className="text-base font-semibold text-foreground mb-2">
              The Competition
            </h3>
            <Competitors data={comp} />
          </section>
        )}

        {/* — The Market — */}
        {mktIntel && (
          <section className="mb-12">
            <h3 className="text-base font-semibold text-foreground mb-2">
              The Market
            </h3>
            <MarketIntelligence data={mktIntel} />
          </section>
        )}

        {/* — The Graveyard — */}
        {graveyard && (graveyard.previous_attempts.length > 0 || graveyard.lessons_learned) && (
          <section className="mb-12">
            <h3 className="text-base font-semibold text-foreground mb-2">
              Why Others Failed
            </h3>
            {graveyard.lessons_learned && (
              <p className="text-muted leading-relaxed mb-5">{graveyard.lessons_learned}</p>
            )}
            <GraveyardResearch data={graveyard} />
          </section>
        )}

        {/* legacy viability for old runs */}
        {!mktIntel && via && (
          <section className="mb-12">
            <h3 className="text-base font-semibold text-foreground mb-4">
              Viability Analysis
            </h3>
            <Viability data={via} />
          </section>
        )}

        {/* — Full Reasoning (collapsed) — */}
        {s && (
          <details className="mb-8 rounded-2xl border border-card-border bg-card group">
            <summary className="flex cursor-pointer items-center justify-between p-5 text-base font-semibold text-foreground hover:bg-white/[0.02] transition-colors select-none">
              full AI reasoning
              <svg
                className="h-4 w-4 text-muted/40 transition-transform group-open:rotate-180"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </summary>
            <div className="border-t border-card-border p-5">
              <p className="text-sm text-muted leading-relaxed whitespace-pre-line">{s.reasoning}</p>
              {s.recommended_positioning && (
                <div className="mt-4 pt-4 border-t border-card-border">
                  <p className="text-sm font-semibold text-foreground mb-1">recommended positioning</p>
                  <p className="text-sm text-muted leading-relaxed">{s.recommended_positioning}</p>
                </div>
              )}
            </div>
          </details>
        )}
      </div>
    </div>
  );
}
