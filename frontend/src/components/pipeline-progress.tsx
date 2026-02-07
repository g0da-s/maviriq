"use client";

import { useEffect, useRef, useState } from "react";
import { getStreamUrl, getValidation } from "@/lib/api";
import type { ValidationRun, Verdict } from "@/lib/types";

const AGENTS = [
  { num: 1, name: "pain & user discovery", desc: "searching reddit, hn, forums for real pain points" },
  { num: 2, name: "competitor research", desc: "mapping competitors, pricing, reviews on g2 & capterra" },
  { num: 3, name: "viability analysis", desc: "analyzing willingness to pay, reachability, market gaps" },
  { num: 4, name: "synthesis & verdict", desc: "combining all research into a final build/skip verdict" },
];

type Status = "waiting" | "running" | "done";

interface Props {
  runId: string;
  onComplete: (run: ValidationRun) => void;
  onError: (error: string) => void;
}

export function PipelineProgress({ runId, onComplete, onError }: Props) {
  const [currentAgent, setCurrentAgent] = useState(0);
  const [completedAgents, setCompletedAgents] = useState<Set<number>>(new Set());
  const [verdict, setVerdict] = useState<{ verdict: Verdict; confidence: number } | null>(null);
  const [failed, setFailed] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    // Start at agent 1 immediately
    setCurrentAgent(1);

    const es = new EventSource(getStreamUrl(runId));
    esRef.current = es;

    es.addEventListener("agent_completed", (e) => {
      const data = JSON.parse(e.data);
      const agentNum = data.agent as number;
      setCompletedAgents((prev) => new Set([...prev, agentNum]));
      // Advance to next agent
      if (agentNum < 4) {
        setCurrentAgent(agentNum + 1);
      }
    });

    es.addEventListener("pipeline_completed", async (e) => {
      const data = JSON.parse(e.data);
      setVerdict({ verdict: data.verdict, confidence: data.confidence });
      setCompletedAgents(new Set([1, 2, 3, 4]));
      es.close();

      // Fetch full results
      try {
        const run = await getValidation(runId);
        onComplete(run);
      } catch {
        onError("failed to fetch results");
      }
    });

    es.addEventListener("pipeline_error", (e) => {
      const data = JSON.parse(e.data);
      setFailed(true);
      onError(data.error);
      es.close();
    });

    es.addEventListener("error", () => {
      // EventSource auto-reconnects; only handle if closed
      if (es.readyState === EventSource.CLOSED) {
        setFailed(true);
        onError("connection lost");
      }
    });

    return () => {
      es.close();
    };
  }, [runId, onComplete, onError]);

  function getStatus(agentNum: number): Status {
    if (completedAgents.has(agentNum)) return "done";
    if (agentNum === currentAgent && !failed) return "running";
    return "waiting";
  }

  return (
    <div className="w-full max-w-lg mx-auto">
      {verdict && (
        <div className="mb-8 text-center">
          <p className="text-sm text-muted mb-2">verdict</p>
          <p
            className={`font-display text-4xl font-bold ${
              verdict.verdict === "BUILD"
                ? "text-build"
                : verdict.verdict === "SKIP"
                  ? "text-skip"
                  : "text-conditional"
            }`}
          >
            {verdict.verdict.toLowerCase()}
          </p>
          <p className="mt-1 text-muted">
            {Math.round(verdict.confidence * 100)}% confidence
          </p>
        </div>
      )}

      <div className="space-y-0">
        {AGENTS.map((agent, i) => {
          const status = getStatus(agent.num);
          return (
            <div key={agent.num} className="flex gap-4">
              {/* timeline */}
              <div className="flex flex-col items-center">
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-full border-2 text-xs font-bold transition-all duration-500 ${
                    status === "done"
                      ? "border-build bg-build/20 text-build"
                      : status === "running"
                        ? "border-build text-build pulse-glow"
                        : "border-card-border text-muted/40"
                  }`}
                >
                  {status === "done" ? (
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    agent.num
                  )}
                </div>
                {i < AGENTS.length - 1 && (
                  <div
                    className={`w-0.5 flex-1 min-h-[2rem] transition-colors duration-500 ${
                      status === "done" ? "bg-build/40" : "bg-card-border"
                    }`}
                  />
                )}
              </div>

              {/* content */}
              <div className="pb-8">
                <p
                  className={`font-display font-semibold transition-colors duration-300 ${
                    status === "done"
                      ? "text-foreground"
                      : status === "running"
                        ? "text-foreground"
                        : "text-muted/40"
                  }`}
                >
                  {agent.name}
                </p>
                <p
                  className={`mt-0.5 text-sm transition-colors duration-300 ${
                    status === "running" ? "text-muted" : "text-muted/30"
                  }`}
                >
                  {status === "running" ? (
                    <span className="inline-flex items-center gap-2">
                      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-build" />
                      {agent.desc}
                    </span>
                  ) : status === "done" ? (
                    "complete"
                  ) : (
                    "waiting"
                  )}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {failed && (
        <div className="mt-4 rounded-xl border border-skip/30 bg-skip/5 p-4 text-center text-sm text-skip">
          pipeline failed — check server logs
        </div>
      )}
    </div>
  );
}
