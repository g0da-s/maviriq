"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getValidation } from "@/lib/api";
import type { ValidationRun } from "@/lib/types";
import { PipelineProgress } from "@/components/pipeline-progress";
import { PainPoints } from "@/components/pain-points";
import { Competitors } from "@/components/competitors";
import { Viability } from "@/components/viability";
import { Synthesis } from "@/components/synthesis";
import { VerdictBadge } from "@/components/verdict-badge";

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
        // If still running, show the pipeline progress with SSE
        if (data.status === "running" || data.status === "pending") {
          setIsStreaming(true);
        }
      } catch (err) {
        if (err instanceof Error && err.message.includes("404")) {
          // Not found yet — might be still initializing, show streaming
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

  // Still running — show pipeline progress
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

  // Completed — show full results
  if (!run) return null;

  return (
    <div className="mx-auto max-w-3xl px-6 pt-28 pb-16">
      {/* header */}
      <div className="mb-10">
        <Link href="/validations" className="text-sm text-muted hover:text-foreground transition-colors">
          &larr; back to history
        </Link>
        <h1 className="mt-4 font-display text-3xl font-bold">{run.idea}</h1>
        <div className="mt-3 flex items-center gap-4">
          {run.synthesis && (
            <>
              <VerdictBadge verdict={run.synthesis.verdict} />
              <span className="text-sm text-muted">
                {Math.round(run.synthesis.confidence * 100)}% confidence
              </span>
            </>
          )}
          {run.status === "failed" && (
            <span className="rounded-full border border-skip px-3 py-0.5 text-xs text-skip">
              failed
            </span>
          )}
          {run.completed_at && (
            <span className="text-xs text-muted/40">
              {new Date(run.completed_at).toLocaleDateString()}
            </span>
          )}
        </div>
        {run.synthesis?.one_line_summary && (
          <p className="mt-4 text-muted leading-relaxed">{run.synthesis.one_line_summary}</p>
        )}
      </div>

      {/* agent results */}
      <div className="space-y-6">
        {run.synthesis && <Synthesis data={run.synthesis} />}
        {run.pain_discovery && <PainPoints data={run.pain_discovery} />}
        {run.competitor_research && <Competitors data={run.competitor_research} />}
        {run.viability && <Viability data={run.viability} />}
      </div>
    </div>
  );
}
