"use client";

import { useLocale } from "next-intl";
import type { Verdict } from "@/lib/types";

const styles: Record<Verdict, string> = {
  BUILD: "border-build text-build",
  SKIP: "border-skip text-skip",
  MAYBE: "border-maybe text-maybe",
};

const labels: Record<string, Record<Verdict, string>> = {
  en: { BUILD: "build", SKIP: "skip", MAYBE: "maybe" },
  lt: { BUILD: "verta", SKIP: "neverta", MAYBE: "galbūt" },
};

export function VerdictBadge({
  verdict,
  size = "md",
}: {
  verdict: Verdict;
  size?: "sm" | "md" | "lg";
}) {
  const locale = useLocale();
  const sizeClass =
    size === "lg"
      ? "px-6 py-2 text-2xl"
      : size === "sm"
        ? "px-3 py-0.5 text-xs"
        : "px-4 py-1 text-sm";

  return (
    <span
      className={`inline-block rounded-full border font-display font-bold ${styles[verdict]} ${sizeClass}`}
    >
      {(labels[locale] ?? labels.en)[verdict]}
    </span>
  );
}
