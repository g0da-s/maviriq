"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { getStreamUrl, getValidation } from "@/lib/api";
import { mapBackendError } from "@/lib/supabase-error";
import { useAuth } from "@/lib/auth-context";
import type { ValidationRun } from "@/lib/types";

// Agents 1-4 run in parallel after agent 0 completes
const PARALLEL_AGENTS = new Set([1, 2, 3, 4]);

type Status = "waiting" | "running" | "done";

interface Props {
  runId: string;
  onComplete: (run: ValidationRun) => void;
  onError: (error: string) => void;
  onProgress?: (completed: number, total: number) => void;
}

export function PipelineProgress({ runId, onComplete, onError, onProgress }: Props) {
  const [completedAgents, setCompletedAgents] = useState<Set<number>>(new Set());
  const [pipelineStarted, setPipelineStarted] = useState(false);
  const [failed, setFailed] = useState(false);
  const [reconnecting, setReconnecting] = useState(false);
  const esRef = useRef<EventSource | null>(null);
  const retriesRef = useRef(0);
  const doneRef = useRef(false);
  const lastEventTimeRef = useRef(Date.now());
  const { session } = useAuth();
  const t = useTranslations("pipeline");

  const contextAgent = { num: 0, name: t("agent0Name"), desc: t("agent0Desc") };
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

    // Connection generation counter — prevents stale async connect() from proceeding
    let currentGeneration = 0;
    let connectInFlight = false;
    let abortController = new AbortController();

    function startNewGeneration() {
      currentGeneration += 1;
      abortController.abort();
      abortController = new AbortController();
      esRef.current?.close();
      return currentGeneration;
    }

    /** Build a set of completed agent numbers from a validation record. */
    function completedFromRecord(run: ValidationRun): Set<number> {
      const s = new Set<number>();
      if (run.context_research) s.add(0);
      if (run.pain_discovery) s.add(1);
      if (run.competitor_research) s.add(2);
      if (run.market_intelligence) s.add(3);
      if (run.graveyard_research) s.add(4);
      if (run.synthesis) s.add(5);
      return s;
    }

    async function connect() {
      if (doneRef.current) return;
      if (connectInFlight) return; // Prevent duplicate parallel connects

      const gen = startNewGeneration();
      connectInFlight = true;

      try {
        // Check if pipeline already finished (handles refresh / stale reconnect)
        try {
          const current = await getValidation(runId);
          if (gen !== currentGeneration) return; // Stale — bail out
          if (current.status === "completed") {
            doneRef.current = true;
            setCompletedAgents(new Set([0, 1, 2, 3, 4, 5]));
            setPipelineStarted(true);
            onComplete(current);
            return;
          }
          if (current.status === "failed") {
            doneRef.current = true;
            setFailed(true);
            onError(current.error || t("somethingWentWrong"));
            return;
          }

          // Pipeline still running — pre-populate from DB state
          const preCompleted = completedFromRecord(current);
          setCompletedAgents(preCompleted);
          setPipelineStarted(true);
        } catch {
          if (gen !== currentGeneration) return;
          // If status check fails, proceed with SSE anyway
          setPipelineStarted(true);
        }

        let url: string;
        try {
          url = await getStreamUrl(runId, abortController.signal);
        } catch {
          // Aborted or failed — bail out
          if (gen !== currentGeneration) return;
          throw new Error("Failed to get stream URL");
        }
        if (gen !== currentGeneration) return; // Stale — bail out

        const es = new EventSource(url);
        esRef.current = es;

        es.addEventListener("keepalive", () => {
          lastEventTimeRef.current = Date.now();
        });

        es.addEventListener("agent_completed", (e) => {
          retriesRef.current = 0;
          lastEventTimeRef.current = Date.now();
          setReconnecting(false);
          let data: Record<string, unknown>;
          try { data = JSON.parse(e.data); } catch { return; }
          const agentNum = data.agent as number;

          setCompletedAgents((prev) => new Set([...prev, agentNum]));
        });

        es.addEventListener("pipeline_completed", async (e) => {
          lastEventTimeRef.current = Date.now();
          doneRef.current = true;
          try { JSON.parse(e.data); } catch {
            es.close();
            onError(t("somethingWentWrong"));
            return;
          }
          setCompletedAgents(new Set([0, 1, 2, 3, 4, 5]));
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
          const key = mapBackendError(data.error as string, "somethingWentWrong");
          onError(t(key));
          es.close();
        });

        es.addEventListener("error", () => {
          if (doneRef.current) return;
          es.close();

          if (retriesRef.current < MAX_RETRIES) {
            setReconnecting(true);
            const delay = Math.min(1000 * 2 ** retriesRef.current, 10_000);
            retriesRef.current += 1;
            connectInFlight = false; // Allow retry to proceed
            setTimeout(connect, delay);
          } else {
            setReconnecting(false);
            setFailed(true);
            onError(t("connectionLost"));
          }
        });
      } finally {
        connectInFlight = false;
      }
    }

    connect();

    // Watchdog: force reconnect if no event (including keepalive) in 30s
    const watchdog = setInterval(() => {
      if (doneRef.current) return;
      const staleSec = (Date.now() - lastEventTimeRef.current) / 1000;
      if (staleSec > 30) {
        retriesRef.current = 0;
        setReconnecting(true);
        connectInFlight = false; // Allow reconnect
        connect();
      }
    }, 20_000);

    function handleVisibilityChange() {
      if (document.visibilityState !== "visible") return;
      if (doneRef.current) return;
      const staleSec = (Date.now() - lastEventTimeRef.current) / 1000;
      if (staleSec > 20) {
        retriesRef.current = 0;
        setReconnecting(true);
        connectInFlight = false; // Allow reconnect
        connect();
      }
    }

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      doneRef.current = true;
      startNewGeneration(); // Aborts in-flight fetch + closes EventSource
      clearInterval(watchdog);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [runId, session, onComplete, onError, t]);

  useEffect(() => {
    onProgress?.(completedAgents.size, 6);
  }, [completedAgents, onProgress]);

  // Derive running status from completedAgents — no separate state to keep in sync
  function getStatus(agentNum: number): Status {
    if (completedAgents.has(agentNum)) return "done";
    if (failed || !pipelineStarted) return "waiting";

    // Agent 0 runs first — it's running if nothing has completed yet
    if (agentNum === 0) {
      return completedAgents.size === 0 ? "running" : "waiting";
    }

    // Agents 1-4 run in parallel after agent 0 completes
    if (PARALLEL_AGENTS.has(agentNum)) {
      return completedAgents.has(0) ? "running" : "waiting";
    }

    // Agent 5 runs after all parallel agents complete
    if (agentNum === 5) {
      const allParallelDone = [...PARALLEL_AGENTS].every((a) => completedAgents.has(a));
      return allParallelDone && completedAgents.has(0) ? "running" : "waiting";
    }

    return "waiting";
  }

  const contextStatus = getStatus(contextAgent.num);
  const parallelAgents = agents.filter((a) => PARALLEL_AGENTS.has(a.num));
  const synthesisAgent = agents.find((a) => a.num === 5)!;
  const synthesisStatus = getStatus(synthesisAgent.num);
  const allParallelDone = parallelAgents.every((a) => getStatus(a.num) === "done");
  const contextDone = contextStatus === "done";

  // Shared renderer for standalone agent rows (agent 0 and agent 5)
  function renderStandaloneAgent(agent: { num: number; name: string; desc: string }, status: Status) {
    return (
      <div
        className={`flex flex-col items-center text-center rounded-xl px-3 py-2.5 sm:rounded-none sm:px-0 sm:py-0 sm:bg-transparent transition-all duration-300 ${
          status === "running" ? "bg-build/5 shimmer-bg" : ""
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
            <span className="check-pop">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </span>
          ) : status === "running" ? (
            <div className="h-4 w-4 rounded-full border-2 border-build border-t-transparent spin-slow" />
          ) : (
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          )}
        </div>
        <div className="min-w-0 mt-2">
          <p
            className={`font-display text-sm font-semibold transition-colors duration-300 ${
              status === "done" || status === "running"
                ? "text-foreground"
                : "text-muted/40"
            }`}
          >
            {agent.name}
          </p>
          <p
            className={`mt-0.5 sm:mt-1 text-xs transition-colors duration-300 ${
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
  }

  return (
    <div className="w-full max-w-2xl mx-auto">
      {/* Agent 0: context research */}
      {renderStandaloneAgent(contextAgent, contextStatus)}

      {/* connector: agent 0 → parallel agents */}
      <div className="flex justify-center py-2 sm:py-3">
        <div
          className={`w-0.5 h-6 sm:h-8 transition-colors duration-500 ${
            contextDone ? "bg-build/40 connector-fill" : "bg-card-border"
          }`}
        />
      </div>

      {/* parallel agents — 2-col grid on mobile, 4-col grid on desktop */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 sm:gap-3">
        {parallelAgents.map((agent, index) => {
          const status = getStatus(agent.num);
          return (
            <div
              key={agent.num}
              className={`flex flex-col items-center text-center rounded-xl px-2 py-2.5 sm:rounded-none sm:px-0 sm:py-0 sm:bg-transparent transition-all duration-500 ${
                status === "running" ? "bg-build/5 shimmer-bg" : ""
              }`}
              style={{
                transitionDelay: status === "running" ? `${index * 100}ms` : "0ms",
                opacity: status === "waiting" ? 0.4 : 1,
              }}
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
                  <span className="check-pop">
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </span>
                ) : status === "running" ? (
                  <div className="h-4 w-4 rounded-full border-2 border-build border-t-transparent spin-slow" />
                ) : (
                  agent.num
                )}
              </div>
              <div className="min-w-0 mt-2">
                <p
                  className={`font-display text-xs sm:text-sm font-semibold leading-tight transition-colors duration-300 ${
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

      {/* connector: parallel agents → synthesis */}
      <div className="flex justify-center py-2 sm:py-3">
        <div
          className={`w-0.5 h-6 sm:h-8 transition-colors duration-500 ${
            allParallelDone ? "bg-build/40 connector-fill" : "bg-card-border"
          }`}
        />
      </div>

      {/* Agent 5: synthesis */}
      {renderStandaloneAgent(synthesisAgent, synthesisStatus)}

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
