"use client";

import { useTranslations } from "next-intl";
import type { GraveyardResearchOutput } from "@/lib/types";

export function GraveyardResearch({ data }: { data: GraveyardResearchOutput }) {
  const t = useTranslations("graveyard");

  return (
    <div className="space-y-6">
      {data.previous_attempts.length > 0 && (
        <div className="rounded-xl border border-card-border bg-card divide-y divide-card-border">
          {data.previous_attempts.map((attempt, i) => (
            <div key={i} className="px-5 py-4">
              <div className="flex items-center gap-2.5 mb-1.5">
                <p className="text-sm font-semibold text-foreground">{attempt.name}</p>
                {attempt.year && (
                  <span className="text-[10px] uppercase tracking-wider text-muted/40">{attempt.year}</span>
                )}
              </div>
              <p className="text-sm text-muted mb-3">{attempt.what_they_did}</p>
              <div>
                <p className="text-[10px] font-medium uppercase tracking-wider text-muted/50 mb-1.5">{t("whyTheyFailed")}</p>
                <p className="text-xs text-foreground/60">{attempt.shutdown_reason}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
