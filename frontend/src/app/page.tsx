"use client";

import { useEffect, useState } from "react";
import { IdeaForm } from "@/components/idea-form";
import { getStats } from "@/lib/api";

export default function Home() {
  const [count, setCount] = useState<number | null>(null);

  useEffect(() => {
    getStats().then((s) => setCount(s.ideas_analyzed)).catch(() => {});
  }, []);

  return (
    <div className="flex min-h-screen flex-col items-center px-6 pt-24">
      {/* ═══ HERO — vertically centered in viewport ═══ */}
      <div className="flex flex-1 flex-col items-center justify-center w-full max-w-3xl text-center">
        {/* live counter */}
        {count !== null && count > 0 && (
          <p className="mb-6 text-sm text-muted">
            <span className="font-semibold text-foreground">{count.toLocaleString()}</span> ideas analyzed
          </p>
        )}

        <h1 className="font-display text-5xl font-bold tracking-tight sm:text-7xl">
          validate your{" "}
          <span className="inline-flex flex-col">
            <span>idea</span>
            <span className="cursor-blink h-1.5 sm:h-2 w-full rounded-full bg-build -mt-1"></span>
          </span>
        </h1>
        <p className="mt-6 text-lg text-muted">
          stop guessing. know if your idea is worth building
          before you waste your time on it.
        </p>

        <div className="mt-12 w-full">
          <IdeaForm />
        </div>
      </div>

      {/* ═══ BELOW THE FOLD ═══ */}
      <div className="w-full max-w-3xl pb-16">
        {/* HOW IT WORKS */}
        <div className="pt-20 pb-16">
          <h2 className="font-display text-center text-2xl font-bold tracking-tight mb-12">
            how it works
          </h2>
          <div className="grid gap-8 sm:grid-cols-3">
            <div className="text-center">
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-white/20 text-lg font-bold font-display text-foreground">
                1
              </div>
              <p className="text-sm font-semibold text-foreground mb-1">describe your idea</p>
              <p className="text-sm text-muted">type what you want to build in plain english</p>
            </div>
            <div className="text-center">
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-white/20 text-lg font-bold font-display text-foreground">
                2
              </div>
              <p className="text-sm font-semibold text-foreground mb-1">5 AI agents research it</p>
              <p className="text-sm text-muted">pain discovery, competition, market size, failed startups, and viability</p>
            </div>
            <div className="text-center">
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-white/20 text-lg font-bold font-display text-foreground">
                3
              </div>
              <p className="text-sm font-semibold text-foreground mb-1">get your verdict</p>
              <p className="text-sm text-muted">a build, skip, or maybe verdict with full research breakdown</p>
            </div>
          </div>
        </div>

        {/* EXAMPLE OUTPUT */}
        <div className="pt-16 pb-16">
          <h2 className="font-display text-center text-2xl font-bold tracking-tight mb-4">
            what you get
          </h2>
          <p className="text-center text-sm text-muted mb-10">
            real research, not a chatbot opinion
          </p>

          {/* mockup results card */}
          <div className="rounded-2xl border border-card-border bg-card p-6 sm:p-8 select-none">
            <p className="text-xs text-muted/50 mb-3">example output</p>
            <h3 className="font-display text-xl font-bold uppercase mb-4">
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

            {/* mini metrics */}
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

            {/* strengths / risks */}
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

            <div className="mt-6 text-center">
              <p className="text-xs text-muted/40">
                + competitor analysis, market data, failed startups, action plan...
              </p>
            </div>
          </div>
        </div>

        {/* FOOTER */}
        <div className="pt-8 pb-4 text-center">
          <p className="text-xs text-muted/40">powered by anthropic</p>
        </div>
      </div>
    </div>
  );
}
