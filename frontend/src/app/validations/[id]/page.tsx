"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getValidation } from "@/lib/api";
import type { ValidationRun } from "@/lib/types";
import { PipelineProgress } from "@/components/pipeline-progress";
import { VerdictBadge } from "@/components/verdict-badge";
import { DetailSection } from "@/components/detail-section";
import { PainPoints } from "@/components/pain-points";
import { Competitors } from "@/components/competitors";
import { Viability } from "@/components/viability";

export default function ValidationPage() {
  const { id } = useParams<{ id: string }>();
  const [run, setRun] = useState<ValidationRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const data = await getValidation(id);
        setRun(data);
        if (data.status === "running" || data.status === "pending") {
          setIsStreaming(true);
        }
      } catch (err) {
        if (err instanceof Error && err.message.includes("404")) {
          setIsStreaming(true);
        } else {
          setError(err instanceof Error ? err.message : "failed to load validation");
        }
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

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
      <div className="flex min-h-screen items-center justify-center pt-20">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-foreground border-t-transparent" />
      </div>
    );
  }

  if (error && !isStreaming) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 pt-20">
        <p className="text-skip">{error}</p>
        <Link href="/" className="text-sm text-muted hover:text-foreground transition-colors">
          try again
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
  const via = run.viability;

  const avgSeverity = pain && pain.pain_points.length > 0
    ? (pain.pain_points.reduce((sum, p) => sum + p.pain_severity, 0) / pain.pain_points.length)
    : 0;

  return (
    <div className="mx-auto max-w-3xl px-6 pt-28 pb-16">
      {/* back link */}
      <Link href="/validations" className="text-sm text-muted hover:text-foreground transition-colors">
        &larr; back to history
      </Link>

      {/* ═══ HERO: IDEA + VERDICT ═══ */}
      <div className="mt-6">
        <h1 className="font-display text-3xl font-bold leading-tight">{run.idea}</h1>
        {run.completed_at && (
          <p className="mt-1 text-xs text-muted/40">
            {new Date(run.completed_at).toLocaleDateString()}
          </p>
        )}

        {/* verdict card */}
        {s && (
          <div className="mt-5 flex items-center gap-5 rounded-2xl border border-card-border bg-card px-6 py-5">
            <span className={`font-display text-5xl font-bold ${
              Math.round(s.confidence * 100) >= 70 ? "text-build" :
              Math.round(s.confidence * 100) >= 40 ? "text-conditional" : "text-skip"
            }`}>
              {Math.round(s.confidence * 100)}<span className="text-2xl">%</span>
            </span>
            <div className="min-w-0 flex-1">
              <VerdictBadge verdict={s.verdict} size="sm" />
              <p className="mt-1.5 text-sm text-muted leading-relaxed">
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

      {/* ═══ KEY METRICS ═══ */}
      <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {pain && (
          <div className="rounded-xl border border-card-border bg-card p-4 text-center">
            <p className="text-xs text-muted/60">pain severity</p>
            <p className="mt-1 font-display text-2xl font-bold">
              {avgSeverity.toFixed(1)}<span className="text-sm text-muted/40">/5</span>
            </p>
          </div>
        )}
        {comp && (
          <div className="rounded-xl border border-card-border bg-card p-4 text-center">
            <p className="text-xs text-muted/60">competition</p>
            <p className={`mt-1 font-display text-2xl font-bold ${
              comp.market_saturation === "high" ? "text-skip" :
              comp.market_saturation === "medium" ? "text-conditional" : "text-build"
            }`}>
              {comp.market_saturation}
            </p>
          </div>
        )}
        {via && (
          <div className="rounded-xl border border-card-border bg-card p-4 text-center">
            <p className="text-xs text-muted/60">will pay?</p>
            <p className={`mt-1 font-display text-2xl font-bold ${via.people_pay ? "text-build" : "text-skip"}`}>
              {via.people_pay ? "yes" : "no"}
            </p>
          </div>
        )}
        {via && (
          <div className="rounded-xl border border-card-border bg-card p-4 text-center">
            <p className="text-xs text-muted/60">market gap</p>
            <p className={`mt-1 font-display text-2xl font-bold ${
              via.gap_size === "large" ? "text-build" :
              via.gap_size === "medium" ? "text-conditional" :
              via.gap_size === "small" ? "text-muted" : "text-skip"
            }`}>
              {via.gap_size}
            </p>
          </div>
        )}
      </div>

      {/* ═══ STRENGTHS vs RISKS ═══ */}
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

      {/* ═══ TARGET USER + MARKET SIZE ═══ */}
      {s && (
        <div className="mt-8 grid gap-3 sm:grid-cols-2">
          <div className="rounded-xl border border-card-border bg-card p-4">
            <p className="text-xs text-muted/60 mb-1">target user</p>
            <p className="text-sm text-foreground/80">{s.target_user_summary}</p>
          </div>
          <div className="rounded-xl border border-card-border bg-card p-4">
            <p className="text-xs text-muted/60 mb-1">market size</p>
            <p className="text-sm text-foreground/80">{s.estimated_market_size}</p>
          </div>
        </div>
      )}

      {/* ═══ WHAT TO BUILD FIRST ═══ */}
      {s?.recommended_mvp && (
        <div className="mt-6 rounded-2xl border border-card-border bg-card p-6">
          <p className="text-xs font-medium uppercase tracking-wider text-build/70 mb-2">
            what to build first
          </p>
          <p className="text-sm text-foreground/90 leading-relaxed">{s.recommended_mvp}</p>
        </div>
      )}

      {/* ═══ NEXT STEPS ═══ */}
      {s && s.next_steps.length > 0 && (
        <div className="mt-6 rounded-2xl border border-card-border bg-card p-6">
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

      {/* ═══ DETAILED RESEARCH (collapsible) ═══ */}
      <div className="mt-12">
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
          {via && (
            <DetailSection title="viability analysis">
              <Viability data={via} />
            </DetailSection>
          )}
        </div>
      </div>
    </div>
  );
}
