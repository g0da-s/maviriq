"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { getValidation } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { ValidationRun } from "@/lib/types";
import { PipelineProgress } from "@/components/pipeline-progress";
import { VerdictBadge } from "@/components/verdict-badge";
import { DetailSection } from "@/components/detail-section";
import { PainPoints } from "@/components/pain-points";
import { Competitors } from "@/components/competitors";
import { MarketIntelligence } from "@/components/market-intelligence";
import { GraveyardResearch } from "@/components/graveyard-research";
import { Viability } from "@/components/viability";

function isSafeUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

const sourceLabels: Record<string, { label: string; color: string }> = {
  reddit: { label: "Reddit", color: "border-orange-500/30 text-orange-400" },
  hackernews: { label: "Hacker News", color: "border-amber-500/30 text-amber-400" },
  twitter: { label: "X / Twitter", color: "border-sky-500/30 text-sky-400" },
  youtube: { label: "YouTube", color: "border-red-500/30 text-red-400" },
  google_news: { label: "News", color: "border-blue-500/30 text-blue-400" },
  producthunt: { label: "Product Hunt", color: "border-orange-400/30 text-orange-300" },
  google: { label: "Google", color: "border-blue-500/30 text-blue-400" },
  g2: { label: "G2", color: "border-orange-500/30 text-orange-400" },
  capterra: { label: "Capterra", color: "border-teal-500/30 text-teal-400" },
  crunchbase: { label: "Crunchbase", color: "border-indigo-500/30 text-indigo-400" },
};

function SourceBadge({ source }: { source: string }) {
  const key = source.toLowerCase().replace(/\s+/g, "");
  const info = sourceLabels[key];
  return (
    <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${info?.color ?? "border-white/10 text-muted/60"}`}>
      {info?.label ?? source}
    </span>
  );
}

const effortColor = { low: "text-build", medium: "text-maybe", high: "text-skip" };

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
          <div className="mt-5 flex items-start gap-5 rounded-2xl border border-card-border bg-card px-6 py-5">
            <div className="flex flex-col items-center shrink-0">
              <span className={`font-display text-5xl font-bold ${
                Math.round(s.confidence * 100) >= 70 ? "text-build" :
                Math.round(s.confidence * 100) >= 40 ? "text-maybe" : "text-skip"
              }`}>
                {Math.round(s.confidence * 100)}<span className="text-2xl">%</span>
              </span>
              <div className="mt-3">
                <VerdictBadge verdict={s.verdict} size="md" />
              </div>
            </div>
            <p className="mt-1 text-sm text-muted leading-relaxed">
              {s.one_line_summary}
            </p>
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
            <p className="text-xs text-muted/60">pain severity</p>
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
            <p className="text-xs text-muted/60">competition</p>
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
            <p className="text-xs text-muted/60">will pay?</p>
            <p className={`mt-1 font-display text-2xl font-bold ${(s?.people_pay ?? via?.people_pay) ? "text-build" : "text-skip"}`}>
              {(s?.people_pay ?? via?.people_pay) ? "yes" : "no"}
            </p>
          </div>
        )}
        {(s || via) && (
          <div className="rounded-xl border border-card-border bg-card p-4 text-center">
            <p className="text-xs text-muted/60">market gap</p>
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
            <p className="text-xs text-muted/60">growth</p>
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
            <p className="text-xs text-muted/60">dead startups</p>
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
            <div className="rounded-2xl border border-build/20 bg-build/5 p-5">
              <p className="text-xs font-medium uppercase tracking-wider text-build/70 mb-3">
                strengths
              </p>
              <ul className="space-y-2">
                {s.key_strengths.map((str, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-foreground/80">
                    <span className="mt-0.5 text-build font-bold">+</span>
                    {str}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {s.key_risks.length > 0 && (
            <div className="rounded-2xl border border-skip/20 bg-skip/5 p-5">
              <p className="text-xs font-medium uppercase tracking-wider text-skip/70 mb-3">
                risks
              </p>
              <ul className="space-y-2">
                {s.key_risks.map((risk, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-foreground/80">
                    <span className="mt-0.5 text-skip font-bold">-</span>
                    {risk}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* ═══ 4. THE RESEARCH — curated highlights ═══ */}
      <div className="mt-14">
        <p className="text-xs font-medium uppercase tracking-wider text-muted/40 mb-6">
          the research
        </p>

        {/* — The Pain — */}
        {pain && (
          <div className="mb-10">
            <h2 className="text-sm font-medium uppercase tracking-wider text-muted/60 mb-3">
              the pain
            </h2>
            <p className="text-sm text-muted leading-relaxed mb-4">{pain.pain_summary}</p>
            {pain.pain_points.length > 0 && (
              <div className="space-y-2">
                {pain.pain_points.slice(0, 3).map((pp, i) => (
                  <div key={i} className="flex items-start gap-3 rounded-lg border border-card-border bg-white/[0.02] p-3">
                    <div className="flex shrink-0 items-center gap-0.5 mt-0.5">
                      {Array.from({ length: 5 }).map((_, j) => (
                        <div
                          key={j}
                          className={`h-1.5 w-1.5 rounded-full ${
                            j < pp.pain_severity ? "bg-skip" : "bg-white/10"
                          }`}
                        />
                      ))}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-foreground/90 italic">&ldquo;{pp.quote}&rdquo;</p>
                      <div className="mt-1 flex items-center gap-2 text-xs text-muted/50">
                        {pp.source_url && isSafeUrl(pp.source_url) ? (
                          <a href={pp.source_url} target="_blank" rel="noopener noreferrer" className="hover:opacity-80">
                            <SourceBadge source={pp.source} />
                          </a>
                        ) : (
                          <SourceBadge source={pp.source} />
                        )}
                        {pp.author_context && <span>{pp.author_context}</span>}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* — The Competition — */}
        {comp && (
          <div className="mb-10">
            <h2 className="text-sm font-medium uppercase tracking-wider text-muted/60 mb-3">
              the competition
            </h2>
            {/* stat bar */}
            <div className="grid grid-cols-3 gap-3 mb-4">
              <div className="rounded-xl border border-card-border bg-white/[0.02] p-3 text-center">
                <p className="text-xs text-muted/60">saturation</p>
                <p className={`mt-1 font-display font-bold ${
                  comp.market_saturation === "high" ? "text-skip" :
                  comp.market_saturation === "medium" ? "text-maybe" : "text-build"
                }`}>
                  {comp.market_saturation}
                </p>
              </div>
              <div className="rounded-xl border border-card-border bg-white/[0.02] p-3 text-center">
                <p className="text-xs text-muted/60">avg price</p>
                <p className="mt-1 font-display font-bold">{comp.avg_price_point}</p>
              </div>
              <div className="rounded-xl border border-card-border bg-white/[0.02] p-3 text-center">
                <p className="text-xs text-muted/60">competitors</p>
                <p className="mt-1 font-display font-bold">{comp.competitors.length}</p>
              </div>
            </div>
            {/* compact competitor list */}
            {comp.competitors.length > 0 && (
              <div className="space-y-2 mb-4">
                {comp.competitors.map((c, i) => (
                  <div key={i} className="flex items-center gap-3 rounded-lg border border-card-border bg-white/[0.02] p-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        {c.url && isSafeUrl(c.url) ? (
                          <a href={c.url} target="_blank" rel="noopener noreferrer" className="text-sm font-medium hover:underline truncate">
                            {c.name}<span className="ml-1 text-muted/40 text-xs">↗</span>
                          </a>
                        ) : (
                          <p className="text-sm font-medium truncate">{c.name}</p>
                        )}
                        <span className="text-xs text-muted/40 truncate hidden sm:inline">{c.one_liner}</span>
                      </div>
                    </div>
                    {c.pricing.length > 0 && (
                      <span className="shrink-0 text-xs text-muted/60">{c.pricing[0].price}</span>
                    )}
                  </div>
                ))}
              </div>
            )}
            {/* underserved needs */}
            {comp.underserved_needs.length > 0 && (
              <div className="flex flex-wrap gap-2">
                <span className="text-xs text-muted/40 self-center mr-1">gaps:</span>
                {comp.underserved_needs.map((need, i) => (
                  <span key={i} className="rounded-full border border-build/20 bg-build/5 px-3 py-1 text-xs text-build">
                    {need}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* — The Market — */}
        {mktIntel && (
          <div className="mb-10">
            <h2 className="text-sm font-medium uppercase tracking-wider text-muted/60 mb-3">
              the market
            </h2>
            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="rounded-xl border border-card-border bg-white/[0.02] p-3">
                <p className="text-xs text-muted/60 mb-1">market size</p>
                <p className="font-display font-bold text-sm">{mktIntel.market_size_estimate}</p>
              </div>
              <div className="rounded-xl border border-card-border bg-white/[0.02] p-3">
                <p className="text-xs text-muted/60 mb-1">growth</p>
                <p className={`font-display font-bold ${
                  mktIntel.growth_direction === "growing" ? "text-build" :
                  mktIntel.growth_direction === "stable" ? "text-maybe" :
                  mktIntel.growth_direction === "shrinking" ? "text-skip" : "text-muted"
                }`}>
                  {mktIntel.growth_direction}
                </p>
              </div>
            </div>
            {mktIntel.distribution_channels.length > 0 && (
              <div className="space-y-2">
                {mktIntel.distribution_channels.map((ch, i) => (
                  <div key={i} className="flex items-center justify-between rounded-lg border border-card-border bg-white/[0.02] p-3">
                    <div>
                      <p className="text-sm font-medium">{ch.channel}</p>
                      <p className="text-xs text-muted/50">{ch.reach_estimate}</p>
                    </div>
                    <span className={`text-xs ${effortColor[ch.effort]}`}>
                      {ch.effort} effort
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* — The Graveyard — */}
        {graveyard && graveyard.previous_attempts.length > 0 && (
          <div className="mb-10">
            <h2 className="text-sm font-medium uppercase tracking-wider text-muted/60 mb-3">
              the graveyard
            </h2>
            <div className="space-y-2 mb-4">
              {graveyard.previous_attempts.map((attempt, i) => (
                <div key={i} className="rounded-lg border border-card-border bg-white/[0.02] p-3">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium">{attempt.name}</p>
                    {attempt.year && (
                      <span className="text-xs text-muted/40">{attempt.year}</span>
                    )}
                  </div>
                  <p className="mt-1 text-xs text-muted/60">{attempt.what_they_did}</p>
                  <p className="mt-1 text-xs text-skip/80">Shut down: {attempt.shutdown_reason}</p>
                </div>
              ))}
            </div>
            {graveyard.failure_reasons.length > 0 && (
              <div className="flex flex-wrap gap-2">
                <span className="text-xs text-muted/40 self-center mr-1">why they failed:</span>
                {graveyard.failure_reasons.map((reason, i) => (
                  <span key={i} className="rounded-full border border-skip/20 bg-skip/5 px-3 py-1 text-xs text-skip/80">
                    {reason}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* legacy viability for old runs */}
        {!mktIntel && via && (
          <div className="mb-10">
            <h2 className="text-sm font-medium uppercase tracking-wider text-muted/60 mb-3">
              viability analysis
            </h2>
            <Viability data={via} />
          </div>
        )}
      </div>

      {/* ═══ 5. ACTION PLAN ═══ */}
      {s && (
        <div className="mt-4">
          <p className="text-xs font-medium uppercase tracking-wider text-muted/40 mb-6">
            action plan
          </p>

          <div className="grid gap-3 sm:grid-cols-2 mb-4">
            <div className="rounded-xl border border-card-border bg-card p-4">
              <p className="text-xs text-muted/60 mb-1">target user</p>
              <p className="text-sm text-foreground/80">{s.target_user_summary}</p>
            </div>
            <div className="rounded-xl border border-card-border bg-card p-4">
              <p className="text-xs text-muted/60 mb-1">market size</p>
              <p className="text-sm text-foreground/80">{s.estimated_market_size}</p>
            </div>
          </div>

          {s.recommended_mvp && (
            <div className="mb-4 rounded-2xl border border-card-border bg-card p-6">
              <p className="text-xs font-medium uppercase tracking-wider text-build/70 mb-2">
                what to build first
              </p>
              <p className="text-sm text-foreground/90 leading-relaxed">{s.recommended_mvp}</p>
            </div>
          )}

          {s.differentiation_strategy && (
            <div className="mb-4 rounded-2xl border border-build/20 bg-build/5 p-6">
              <p className="text-xs font-medium uppercase tracking-wider text-build/70 mb-2">
                differentiation strategy
              </p>
              <p className="text-sm text-foreground/90 leading-relaxed">{s.differentiation_strategy}</p>
            </div>
          )}

          {s.lessons_from_failures && (
            <div className="mb-4 rounded-2xl border border-skip/20 bg-skip/5 p-6">
              <p className="text-xs font-medium uppercase tracking-wider text-skip/70 mb-2">
                lessons from past failures
              </p>
              <p className="text-sm text-foreground/90 leading-relaxed">{s.lessons_from_failures}</p>
              {s.previous_attempts_summary && (
                <div className="mt-3 pt-3 border-t border-skip/10">
                  <p className="text-xs text-muted/60 mb-1">previous attempts</p>
                  <p className="text-sm text-muted leading-relaxed">{s.previous_attempts_summary}</p>
                </div>
              )}
            </div>
          )}

          {s.next_steps.length > 0 && (
            <div className="rounded-2xl border border-card-border bg-card p-6">
              <p className="text-xs font-medium uppercase tracking-wider text-muted/60 mb-3">
                next steps
              </p>
              <ol className="space-y-2.5">
                {s.next_steps.map((step, i) => (
                  <li key={i} className="flex items-start gap-3 text-sm text-foreground/80">
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

      {/* ═══ 6. DETAILED RESEARCH — full data for power users ═══ */}
      <div className="mt-14">
        <p className="text-xs font-medium uppercase tracking-wider text-muted/40 mb-4">
          detailed research
        </p>
        <div className="space-y-3">
          {s && (
            <DetailSection title="full reasoning">
              <p className="text-sm text-muted leading-relaxed whitespace-pre-line">{s.reasoning}</p>
              {s.recommended_positioning && (
                <div className="mt-4 pt-4 border-t border-card-border">
                  <p className="text-xs text-muted/60 mb-1">recommended positioning</p>
                  <p className="text-sm text-muted leading-relaxed">{s.recommended_positioning}</p>
                </div>
              )}
            </DetailSection>
          )}
          {pain && (
            <DetailSection title="pain & user discovery">
              <PainPoints data={pain} />
            </DetailSection>
          )}
          {comp && (
            <DetailSection title="competitor research">
              <Competitors data={comp} />
            </DetailSection>
          )}
          {mktIntel && (
            <DetailSection title="market intelligence">
              <MarketIntelligence data={mktIntel} />
            </DetailSection>
          )}
          {graveyard && (
            <DetailSection title="graveyard research">
              <GraveyardResearch data={graveyard} />
            </DetailSection>
          )}
        </div>
      </div>
    </div>
  );
}
