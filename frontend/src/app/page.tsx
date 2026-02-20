"use client";

import { useEffect, useState } from "react";
import { IdeaForm } from "@/components/idea-form";
import { getStats } from "@/lib/api";

export default function Home() {
  const [count, setCount] = useState<number | null>(null);

  useEffect(() => {
    getStats()
      .then((s) => setCount(s.ideas_analyzed))
      .catch(() => setCount(0));
  }, []);

  return (
    <>
      {/* ═══ HERO — full viewport, vertically centered ═══ */}
      <div className="flex min-h-screen flex-col items-center justify-center px-6">
        <div className="w-full max-w-2xl text-center">
          {count !== null && count > 0 && (
            <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-card-border bg-card px-4 py-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-build animate-pulse" />
              <span className="text-xs text-muted">
                <span className="font-semibold text-foreground">{count.toLocaleString()}</span> ideas analyzed
              </span>
            </div>
          )}

          <h1 className="font-display text-5xl font-bold tracking-tight sm:text-7xl">
            validate your{" "}
            <span className="inline-flex flex-col">
              <span>idea</span>
              <span className="cursor-blink h-1.5 sm:h-2 w-full rounded-full bg-build -mt-1"></span>
            </span>
          </h1>
          <p className="mt-6 text-lg text-muted max-w-md mx-auto">
            5 AI agents research your startup idea and deliver a build or skip verdict.
          </p>

          <div className="mt-10">
            <IdeaForm />
          </div>
        </div>
      </div>

      {/* ═══ BELOW THE FOLD ═══ */}
      <div className="px-6">
        <div className="mx-auto max-w-2xl">
          {/* HOW IT WORKS */}
          <div className="py-16">
            <div className="grid grid-cols-3 gap-6 text-center">
              <div>
                <p className="text-2xl font-bold font-display text-build">1</p>
                <p className="mt-1 text-sm font-semibold text-foreground">describe</p>
                <p className="mt-0.5 text-xs text-muted">your idea in plain english</p>
              </div>
              <div>
                <p className="text-2xl font-bold font-display text-build">2</p>
                <p className="mt-1 text-sm font-semibold text-foreground">research</p>
                <p className="mt-0.5 text-xs text-muted">5 agents dig into the market</p>
              </div>
              <div>
                <p className="text-2xl font-bold font-display text-build">3</p>
                <p className="mt-1 text-sm font-semibold text-foreground">verdict</p>
                <p className="mt-0.5 text-xs text-muted">build, skip, or maybe — with data</p>
              </div>
            </div>
          </div>

          {/* EXAMPLE OUTPUT */}
          <div className="pb-16">
            <p className="text-center text-xs uppercase tracking-widest text-muted/50 mb-6">
              example output
            </p>

            <div className="rounded-2xl border border-card-border bg-card p-6 sm:p-8 select-none">
              <h3 className="font-display text-lg font-bold uppercase mb-4">
                AI-powered meal planning app for busy parents
              </h3>
              <div className="flex items-center gap-6 mb-6">
                <div className="flex flex-col items-start shrink-0">
                  <span className="font-display text-5xl font-bold text-build leading-none">
                    74<span className="text-2xl">%</span>
                  </span>
                  <span className="mt-1.5 rounded-full bg-build/10 border border-build/30 px-2.5 py-0.5 text-xs font-bold text-build font-display uppercase">
                    build
                  </span>
                </div>
                <p className="text-sm text-muted leading-relaxed">
                  strong pain signal from time-poor parents, but crowded market means you need a sharp wedge — start with dietary restrictions and grocery budget optimization.
                </p>
              </div>

              <div className="grid grid-cols-3 gap-2 sm:grid-cols-6 mb-6">
                {[
                  { label: "pain level", value: "high", color: "text-skip" },
                  { label: "competition", value: "medium", color: "text-maybe" },
                  { label: "will pay?", value: "yes", color: "text-build" },
                  { label: "market gap", value: "medium", color: "text-maybe" },
                  { label: "growth", value: "growing", color: "text-build" },
                  { label: "dead startups", value: "4", color: "text-muted" },
                ].map((m) => (
                  <div key={m.label} className="rounded-lg border border-card-border bg-background/50 p-2.5 text-center">
                    <p className="text-[10px] font-bold text-foreground mb-0.5">{m.label}</p>
                    <p className={`text-xs font-semibold ${m.color}`}>{m.value}</p>
                  </div>
                ))}
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-xl border border-card-border bg-background/50 p-4 border-l-2 border-l-build">
                  <p className="text-xs font-semibold text-foreground mb-2">why this could work</p>
                  <ul className="space-y-1.5">
                    <li className="flex items-baseline gap-2 text-xs text-muted">
                      <span className="text-build shrink-0">&#x2022;</span>
                      Parents will pay for anything that saves time
                    </li>
                    <li className="flex items-baseline gap-2 text-xs text-muted">
                      <span className="text-build shrink-0">&#x2022;</span>
                      Dietary restriction angle is underserved
                    </li>
                    <li className="flex items-baseline gap-2 text-xs text-muted">
                      <span className="text-build shrink-0">&#x2022;</span>
                      Strong retention potential with weekly habit
                    </li>
                  </ul>
                </div>
                <div className="rounded-xl border border-card-border bg-background/50 p-4 border-l-2 border-l-skip">
                  <p className="text-xs font-semibold text-foreground mb-2">what could kill it</p>
                  <ul className="space-y-1.5">
                    <li className="flex items-baseline gap-2 text-xs text-muted">
                      <span className="text-skip shrink-0">&#x2022;</span>
                      Mealime and Eat This Much already dominate
                    </li>
                    <li className="flex items-baseline gap-2 text-xs text-muted">
                      <span className="text-skip shrink-0">&#x2022;</span>
                      Grocery delivery APIs are expensive
                    </li>
                    <li className="flex items-baseline gap-2 text-xs text-muted">
                      <span className="text-skip shrink-0">&#x2022;</span>
                      Recipe content is a commodity
                    </li>
                  </ul>
                </div>
              </div>

              <p className="mt-6 text-center text-xs text-muted/40">
                + competitor deep-dive, market sizing, failed startups, action plan...
              </p>
            </div>
          </div>

          {/* footer */}
          <div className="pb-8 text-center">
            <p className="text-xs text-muted/30">powered by anthropic</p>
          </div>
        </div>
      </div>
    </>
  );
}
