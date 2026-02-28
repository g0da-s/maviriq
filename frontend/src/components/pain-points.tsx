"use client";

import { useTranslations } from "next-intl";
import type { PainDiscoveryOutput } from "@/lib/types";

function isSafeUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

const wtpRank = { high: 3, medium: 2, low: 1 } as const;

const severityRank = { high: 3, moderate: 2, mild: 1 } as const;


export function PainPoints({ data }: { data: PainDiscoveryOutput }) {
  const t = useTranslations("painPoints");

  const wtpLabel = {
    high: t("willingToPayALot"),
    medium: t("willingToPaySome"),
    low: t("priceSensitive"),
  };

  const allSegments = [data.primary_target_user, ...data.user_segments.filter(seg => seg.label !== data.primary_target_user.label)]
    .sort((a, b) => wtpRank[b.willingness_to_pay] - wtpRank[a.willingness_to_pay]);

  const sortedQuotes = [...data.pain_points]
    .sort((a, b) => severityRank[b.pain_severity] - severityRank[a.pain_severity]);

  return (
    <div className="space-y-6">
      {/* who has this pain — combined target user + segments */}
      <div className="rounded-xl border border-card-border bg-card">
        <div className="px-5 py-3 border-b border-card-border">
          <p className="text-xs font-medium uppercase tracking-wider text-muted/50">
            {t("whoHasThisPain")}
          </p>
        </div>
        <div className="divide-y divide-card-border">
          {allSegments.map((seg, i) => (
            <div key={i} className="flex items-center justify-between px-5 py-3">
              <div>
                <p className="text-sm text-foreground font-medium">{seg.label}</p>
                <p className="text-xs text-muted/50 mt-0.5">{seg.description}</p>
              </div>
              <span className="text-xs text-muted/50 shrink-0 ml-4">
                {wtpLabel[seg.willingness_to_pay]}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* pain points — evidence quotes */}
      {sortedQuotes.length > 0 && (
        <div className="rounded-xl border border-card-border bg-card">
          <div className="px-5 py-3 border-b border-card-border">
            <p className="text-xs font-medium uppercase tracking-wider text-muted/50">
              {t("whatPeopleAreSaying")}
              <span className="ml-1.5 text-muted/30">{t("found", { count: data.pain_points.length })}</span>
            </p>
          </div>
          <div className="divide-y divide-card-border">
            {sortedQuotes.slice(0, 3).map((pp, i) => (
              <div key={i} className="px-5 py-4">
                {pp.source_url && isSafeUrl(pp.source_url) ? (
                  <a href={pp.source_url} target="_blank" rel="noopener noreferrer" className="block group">
                    <p className="text-sm text-muted italic leading-relaxed group-hover:text-foreground/70 transition-colors">
                      &ldquo;{pp.quote}&rdquo;
                    </p>
                    <p className="mt-1.5 text-xs text-muted/40">{pp.source} &#8599;</p>
                  </a>
                ) : (
                  <>
                    <p className="text-sm text-muted italic leading-relaxed">
                      &ldquo;{pp.quote}&rdquo;
                    </p>
                    <p className="mt-1.5 text-xs text-muted/40">{pp.source}</p>
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
