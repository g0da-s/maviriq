"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { IdeaForm } from "@/components/idea-form";
import { getStats } from "@/lib/api";

export default function Home() {
  const [count, setCount] = useState<number | null>(null);
  const t = useTranslations('home');

  useEffect(() => {
    getStats()
      .then((s) => setCount(s.ideas_analyzed))
      .catch(() => setCount(0));
  }, []);

  return (
    <>
      {/* ═══ HERO — full viewport, vertically centered ═══ */}
      <div className="flex min-h-screen pt-[12rem] pb-[15vh] flex-col items-center justify-start px-6">
        <div className="w-full max-w-2xl text-center">
          {count !== null && count > 0 && (
            <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-card-border bg-card px-4 py-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-build animate-pulse" />
              <span className="text-xs text-muted">
                <span className="font-semibold text-foreground">{count.toLocaleString()}</span> {t('ideasAnalyzed')}
              </span>
            </div>
          )}

          <h1 className="font-display text-5xl font-bold tracking-tight sm:text-7xl">
            {t('title')}{" "}
            <span className="inline-flex flex-col">
              <span>{t('titleHighlight')}</span>
              <span className="cursor-blink h-1.5 sm:h-2 w-full rounded-full bg-build -mt-1"></span>
            </span>
          </h1>
          <p className="mt-6 text-lg text-muted">
            {t('subtitle')}
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
            <p className="text-center text-xs uppercase tracking-widest text-muted/50 mb-6">
              {t('howItWorks')}
            </p>
            <div className="grid grid-cols-3 gap-3">
              <div className="rounded-xl border border-card-border bg-card p-4 text-center">
                <p className="text-xs font-bold text-build mb-1">01</p>
                <p className="text-sm font-semibold text-foreground">{t('step1Title')}</p>
                <p className="mt-0.5 text-xs text-muted">{t('step1Desc')}</p>
              </div>
              <div className="rounded-xl border border-card-border bg-card p-4 text-center">
                <p className="text-xs font-bold text-build mb-1">02</p>
                <p className="text-sm font-semibold text-foreground">{t('step2Title')}</p>
                <p className="mt-0.5 text-xs text-muted">{t('step2Desc')}</p>
              </div>
              <div className="rounded-xl border border-card-border bg-card p-4 text-center">
                <p className="text-xs font-bold text-build mb-1">03</p>
                <p className="text-sm font-semibold text-foreground">{t('step3Title')}</p>
                <p className="mt-0.5 text-xs text-muted">{t('step3Desc')}</p>
              </div>
            </div>
          </div>

          {/* EXAMPLE OUTPUT */}
          <div className="pb-16">
            <p className="text-center text-xs uppercase tracking-widest text-muted/50 mb-6">
              {t('exampleOutput')}
            </p>

            <div className="rounded-2xl border border-card-border bg-card p-6 sm:p-8 select-none">
              <h3 className="font-display text-lg font-bold uppercase mb-4">
                {t('exampleTitle')}
              </h3>
              <div className="flex items-center gap-6 mb-6">
                <div className="flex flex-col items-start shrink-0">
                  <span className="font-display text-5xl font-bold text-build leading-none">
                    74<span className="text-2xl">%</span>
                  </span>
                  <span className="mt-1.5 rounded-full bg-build/10 border border-build/30 px-2.5 py-0.5 text-xs font-bold text-build font-display uppercase">
                    {t('exampleBuild')}
                  </span>
                </div>
                <p className="text-sm text-muted leading-relaxed">
                  {t('exampleSummary')}
                </p>
              </div>

              <div className="grid grid-cols-3 gap-2 sm:grid-cols-6 mb-6">
                {[
                  { label: t('painLevel'), value: t('high'), color: "text-skip" },
                  { label: t('competition'), value: t('medium'), color: "text-maybe" },
                  { label: t('willPay'), value: t('yes'), color: "text-build" },
                  { label: t('marketGap'), value: t('medium'), color: "text-maybe" },
                  { label: t('growth'), value: t('growing'), color: "text-build" },
                  { label: t('deadStartups'), value: "4", color: "text-muted" },
                ].map((m) => (
                  <div key={m.label} className="rounded-lg border border-card-border bg-background/50 p-2.5 text-center">
                    <p className="text-[10px] font-bold text-foreground mb-0.5">{m.label}</p>
                    <p className={`text-xs font-semibold ${m.color}`}>{m.value}</p>
                  </div>
                ))}
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-xl border border-card-border bg-background/50 p-4 border-l-2 border-l-build">
                  <p className="text-xs font-semibold text-foreground mb-2">{t('whyThisCouldWork')}</p>
                  <ul className="space-y-1.5">
                    <li className="flex items-baseline gap-2 text-xs text-muted">
                      <span className="text-build shrink-0">&#x2022;</span>
                      {t('exampleStrength1')}
                    </li>
                    <li className="flex items-baseline gap-2 text-xs text-muted">
                      <span className="text-build shrink-0">&#x2022;</span>
                      {t('exampleStrength2')}
                    </li>
                    <li className="flex items-baseline gap-2 text-xs text-muted">
                      <span className="text-build shrink-0">&#x2022;</span>
                      {t('exampleStrength3')}
                    </li>
                  </ul>
                </div>
                <div className="rounded-xl border border-card-border bg-background/50 p-4 border-l-2 border-l-skip">
                  <p className="text-xs font-semibold text-foreground mb-2">{t('whatCouldKillIt')}</p>
                  <ul className="space-y-1.5">
                    <li className="flex items-baseline gap-2 text-xs text-muted">
                      <span className="text-skip shrink-0">&#x2022;</span>
                      {t('exampleRisk1')}
                    </li>
                    <li className="flex items-baseline gap-2 text-xs text-muted">
                      <span className="text-skip shrink-0">&#x2022;</span>
                      {t('exampleRisk2')}
                    </li>
                    <li className="flex items-baseline gap-2 text-xs text-muted">
                      <span className="text-skip shrink-0">&#x2022;</span>
                      {t('exampleRisk3')}
                    </li>
                  </ul>
                </div>
              </div>

              <p className="mt-6 text-center text-xs text-muted/40">
                {t('exampleMore')}
              </p>
            </div>
          </div>

          {/* footer */}
          <div className="pb-8 text-center">
            <p className="text-xs text-muted/30">{t('poweredBy')}</p>
          </div>
        </div>
      </div>
    </>
  );
}
