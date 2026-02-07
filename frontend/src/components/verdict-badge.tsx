import type { Verdict } from "@/lib/types";

const styles: Record<Verdict, string> = {
  BUILD: "border-build text-build",
  SKIP: "border-skip text-skip",
  CONDITIONAL: "border-conditional text-conditional",
};

export function VerdictBadge({
  verdict,
  size = "md",
}: {
  verdict: Verdict;
  size?: "sm" | "md" | "lg";
}) {
  const sizeClass =
    size === "lg"
      ? "px-6 py-2 text-2xl"
      : size === "sm"
        ? "px-3 py-0.5 text-xs"
        : "px-4 py-1 text-sm";

  return (
    <span
      className={`inline-block rounded-full border font-display font-bold lowercase ${styles[verdict]} ${sizeClass}`}
    >
      {verdict.toLowerCase()}
    </span>
  );
}
