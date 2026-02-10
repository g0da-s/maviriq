"use client";

import { useEffect, useRef, useState } from "react";
import { getStreamUrl, getValidation } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { ValidationRun, Verdict } from "@/lib/types";

const AGENTS = [
  { num: 1, name: "pain & user discovery", desc: "searching reddit, hn, forums for real pain points" },
  { num: 2, name: "competitor research", desc: "mapping competitors, pricing, reviews on g2 & capterra" },
  { num: 3, name: "viability analysis", desc: "analyzing willingness to pay, reachability, market gaps" },
  { num: 4, name: "synthesis & verdict", desc: "combining all research into a final build/skip verdict" },
];

// Agents 1 & 2 run in parallel, then 3 & 4 run sequentially
const PARALLEL_AGENTS = new Set([1, 2]);

type Status = "waiting" | "running" | "done";

interface Props {
  runId: string;
  onComplete: (run: ValidationRun) => void;
  onError: (error: string) => void;
}

export function PipelineProgress({ runId, onComplete, onError }: Props) {
  const [runningAgents, setRunningAgents] = useState<Set<number>>(new Set());
  const [completedAgents, setCompletedAgents] = useState<Set<number>>(new Set());
  const [verdict, setVerdict] = useState<{ verdict: Verdict; confidence: number } | null>(null);
  const [failed, setFailed] = useState(false);
  const esRef = useRef<EventSource | null>(null);
  const retriesRef = useRef(0);
  const doneRef = useRef(false);
  const { session } = useAuth();

  useEffect(() => {
    if (!session) return;

    const MAX_RETRIES = 5;
    doneRef.current = false;
    retriesRef.current = 0;

    async function connect() {
      if (doneRef.current) return;

      // Agents 1 & 2 start in parallel immediately
      setRunningAgents(new Set([1, 2]));

      const url = await getStreamUrl(runId);
      const es = new EventSource(url);
      esRef.current = es;

      es.addEventListener("agent_completed", (e) => {
        retriesRef.current = 0; // reset on success
        const data = JSON.parse(e.data);
        const agentNum = data.agent as number;

        setCompletedAgents((prev) => {
          const next = new Set([...prev, agentNum]);

          // When both parallel agents (1 & 2) are done, start agent 3
          if (PARALLEL_AGENTS.has(agentNum)) {
            const bothDone = [...PARALLEL_AGENTS].every((a) => next.has(a));
            if (bothDone) {
              setRunningAgents(new Set([3]));
            }
          } else if (agentNum < 4) {
            // Sequential agents (3 → 4)
            setRunningAgents(new Set([agentNum + 1]));
          }

          return next;
        });
      });

      es.addEventListener("pipeline_completed", async (e) => {
        doneRef.current = true;
        const data = JSON.parse(e.data);
        setVerdict({ verdict: data.verdict, confidence: data.confidence });
        setCompletedAgents(new Set([1, 2, 3, 4]));
        setRunningAgents(new Set());
        es.close();

        try {
          const run = await getValidation(runId);
          onComplete(run);
        } catch {
          onError("failed to fetch results");
        }
      });

      es.addEventListener("pipeline_error", (e) => {
        doneRef.current = true;
        const data = JSON.parse(e.data);
        setFailed(true);
        onError(data.error);
        es.close();
      });

      es.addEventListener("error", () => {
        if (doneRef.current) return;
        es.close();

        if (retriesRef.current < MAX_RETRIES) {
          const delay = Math.min(1000 * 2 ** retriesRef.current, 10_000);
          retriesRef.current += 1;
          setTimeout(connect, delay);
        } else {
          setFailed(true);
          onError("connection lost after multiple retries");
        }
      });
    }

    connect();

    return () => {
      doneRef.current = true;
      esRef.current?.close();
    };
  }, [runId, session, onComplete, onError]);

  function getStatus(agentNum: number): Status {
    if (completedAgents.has(agentNum)) return "done";
    if (runningAgents.has(agentNum) && !failed) return "running";
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
                  : "text-maybe"
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
