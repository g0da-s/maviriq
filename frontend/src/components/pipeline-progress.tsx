"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { getStreamUrl, getValidation } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { ValidationRun } from "@/lib/types";

// Agents 1-4 run in parallel, then agent 5 runs after all complete
const PARALLEL_AGENTS = new Set([1, 2, 3, 4]);

type Status = "waiting" | "running" | "done";

interface Props {
  runId: string;
  onComplete: (run: ValidationRun) => void;
  onError: (error: string) => void;
}

export function PipelineProgress({ runId, onComplete, onError }: Props) {
  const [runningAgents, setRunningAgents] = useState<Set<number>>(new Set());
  const [completedAgents, setCompletedAgents] = useState<Set<number>>(new Set());
  const [failed, setFailed] = useState(false);
  const [reconnecting, setReconnecting] = useState(false);
  const esRef = useRef<EventSource | null>(null);
  const retriesRef = useRef(0);
  const doneRef = useRef(false);
  const { session } = useAuth();
  const t = useTranslations("pipeline");

  const agents = [
    { num: 1, name: t("agent1Name"), desc: t("agent1Desc") },
    { num: 2, name: t("agent2Name"), desc: t("agent2Desc") },
    { num: 3, name: t("agent3Name"), desc: t("agent3Desc") },
    { num: 4, name: t("agent4Name"), desc: t("agent4Desc") },
    { num: 5, name: t("agent5Name"), desc: t("agent5Desc") },
  ];

  useEffect(() => {
    if (!session) return;

    const MAX_RETRIES = 5;
    doneRef.current = false;
    retriesRef.current = 0;

    async function connect() {
      if (doneRef.current) return;

      // Agents 1-4 start in parallel immediately
      setRunningAgents(new Set([1, 2, 3, 4]));

      const url = await getStreamUrl(runId);
      const es = new EventSource(url);
      esRef.current = es;

      es.addEventListener("agent_completed", (e) => {
        retriesRef.current = 0;
        setReconnecting(false);
        let data: Record<string, unknown>;
        try { data = JSON.parse(e.data); } catch { return; }
        const agentNum = data.agent as number;

        setCompletedAgents((prev) => {
          const next = new Set([...prev, agentNum]);

          // When all 4 parallel agents are done, start agent 5
          if (PARALLEL_AGENTS.has(agentNum)) {
            const allDone = [...PARALLEL_AGENTS].every((a) => next.has(a));
            if (allDone) {
              setRunningAgents(new Set([5]));
            }
          }

          return next;
        });
      });

      es.addEventListener("pipeline_completed", async (e) => {
        doneRef.current = true;
        let data: Record<string, unknown>;
        try { data = JSON.parse(e.data); } catch {
          es.close();
          onError(t("somethingWentWrong"));
          return;
        }
        setCompletedAgents(new Set([1, 2, 3, 4, 5]));
        setRunningAgents(new Set());
        es.close();

        try {
          const run = await getValidation(runId);
          onComplete(run);
        } catch {
          onError(t("failedToFetchResults"));
        }
      });

      es.addEventListener("pipeline_error", (e) => {
        doneRef.current = true;
        let data: Record<string, unknown>;
        try { data = JSON.parse(e.data); } catch {
          setFailed(true);
          onError(t("somethingWentWrong"));
          es.close();
          return;
        }
        setFailed(true);
        onError(data.error as string);
        es.close();
      });

      es.addEventListener("error", () => {
        if (doneRef.current) return;
        es.close();

        if (retriesRef.current < MAX_RETRIES) {
          setReconnecting(true);
          const delay = Math.min(1000 * 2 ** retriesRef.current, 10_000);
          retriesRef.current += 1;
          setTimeout(connect, delay);
        } else {
          setReconnecting(false);
          setFailed(true);
          onError(t("connectionLost"));
        }
      });
    }

    connect();

    return () => {
      doneRef.current = true;
      esRef.current?.close();
    };
  }, [runId, session, onComplete, onError, t]);

  function getStatus(agentNum: number): Status {
    if (completedAgents.has(agentNum)) return "done";
    if (runningAgents.has(agentNum) && !failed) return "running";
    return "waiting";
  }

  const parallelAgents = agents.filter((a) => PARALLEL_AGENTS.has(a.num));
  const synthesisAgent = agents.find((a) => a.num === 5)!;
  const synthesisStatus = getStatus(synthesisAgent.num);
  const allParallelDone = parallelAgents.every((a) => getStatus(a.num) === "done");

  return (
    <div className="w-full max-w-2xl mx-auto">
      {/* parallel agents — vertical list on mobile, 4-col grid on desktop */}
      <div className="flex flex-col gap-3 sm:grid sm:grid-cols-4 sm:gap-3">
        {parallelAgents.map((agent) => {
          const status = getStatus(agent.num);
          return (
            <div
              key={agent.num}
              className={`flex items-center gap-3 rounded-xl px-3 py-2.5 sm:flex-col sm:items-center sm:text-center sm:rounded-none sm:px-0 sm:py-0 sm:bg-transparent transition-colors duration-300 ${
                status === "running" ? "bg-build/5" : ""
              }`}
            >
              <div
                className={`flex h-9 w-9 sm:h-10 sm:w-10 shrink-0 items-center justify-center rounded-full border-2 text-sm font-bold transition-all duration-500 ${
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
              <div className="min-w-0 sm:mt-2">
                <p
                  className={`font-display text-sm font-semibold leading-tight transition-colors duration-300 ${
                    status === "done" || status === "running"
                      ? "text-foreground"
                      : "text-muted/40"
                  }`}
                >
                  {agent.name}
                </p>
                <p
                  className={`mt-0.5 sm:mt-1 text-xs leading-snug transition-colors duration-300 ${
                    status === "running" ? "text-muted" : "text-muted/30"
                  }`}
                >
                  {status === "running" ? (
                    <span>{agent.desc}</span>
                  ) : status === "done" ? (
                    t("complete")
                  ) : (
                    t("waiting")
                  )}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* connector line — hidden on mobile (vertical list), visible on desktop (grid) */}
      <div className="hidden sm:flex justify-center py-3">
        <div
          className={`w-0.5 h-8 transition-colors duration-500 ${
            allParallelDone ? "bg-build/40" : "bg-card-border"
          }`}
        />
      </div>
      {/* mobile separator */}
      <div className="sm:hidden flex justify-center py-1">
        <div className={`w-8 h-0.5 rounded transition-colors duration-500 ${allParallelDone ? "bg-build/40" : "bg-card-border"}`} />
      </div>

      {/* synthesis agent */}
      <div
        className={`flex items-center gap-3 rounded-xl px-3 py-2.5 sm:flex-col sm:items-center sm:text-center sm:rounded-none sm:px-0 sm:py-0 sm:bg-transparent transition-colors duration-300 ${
          synthesisStatus === "running" ? "bg-build/5" : ""
        }`}
      >
        <div
          className={`flex h-9 w-9 sm:h-10 sm:w-10 shrink-0 items-center justify-center rounded-full border-2 text-sm font-bold transition-all duration-500 ${
            synthesisStatus === "done"
              ? "border-build bg-build/20 text-build"
              : synthesisStatus === "running"
                ? "border-build text-build pulse-glow"
                : "border-card-border text-muted/40"
          }`}
        >
          {synthesisStatus === "done" ? (
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          ) : (
            synthesisAgent.num
          )}
        </div>
        <div className="min-w-0 sm:mt-2">
          <p
            className={`font-display text-sm font-semibold transition-colors duration-300 ${
              synthesisStatus === "done" || synthesisStatus === "running"
                ? "text-foreground"
                : "text-muted/40"
            }`}
          >
            {synthesisAgent.name}
          </p>
          <p
            className={`mt-0.5 sm:mt-1 text-xs transition-colors duration-300 ${
              synthesisStatus === "running" ? "text-muted" : "text-muted/30"
            }`}
          >
            {synthesisStatus === "running" ? (
              <span>{synthesisAgent.desc}</span>
            ) : synthesisStatus === "done" ? (
              t("complete")
            ) : (
              t("waiting")
            )}
          </p>
        </div>
      </div>

      {reconnecting && (
        <div role="alert" className="mt-6 rounded-xl border border-maybe/30 bg-maybe/5 p-4 text-center text-sm text-maybe">
          <span className="inline-flex items-center gap-2">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-maybe" />
            {t("reconnecting")}
          </span>
        </div>
      )}

      {failed && (
        <div role="alert" className="mt-6 rounded-xl border border-skip/30 bg-skip/5 p-4 text-center text-sm text-skip">
          {t("somethingWentWrong")}
        </div>
      )}
    </div>
  );
}
