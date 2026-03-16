"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import posthog from "posthog-js";
import { useTranslations, useLocale } from "next-intl";
import { createValidation, ApiError } from "@/lib/api";
import { mapBackendError } from "@/lib/supabase-error";
import { useAuth } from "@/lib/auth-context";

// Include Lithuanian consonants (č, š, ž) and vowels (ą, ę, ė, į, ū)
const CONSONANT_MASH = /[^aeiouąęėįū\s\d\W]{5,}/i;
const REPEATED_CHARS = /(.)\1{2,}/;

function validateIdea(text: string): string | null {
  const trimmed = text.trim();
  const words = trimmed.split(/\s+/).filter((w) => w.length > 0);

  if (trimmed.length < 10 || words.length < 3) {
    return "errorMinLength";
  }

  // Gibberish check — flag words with 5+ consecutive consonants or repeated chars
  const substantialWords = words.filter((w) => w.length > 3);
  if (substantialWords.length > 0) {
    const gibberishCount = substantialWords.filter(
      (w) => CONSONANT_MASH.test(w) || REPEATED_CHARS.test(w),
    ).length;
    if (gibberishCount / substantialWords.length > 0.3) {
      return "errorGibberish";
    }
  }

  return null;
}

const TARGET_MARKET_OPTIONS = [
  "Global",
  "Lithuania",
  "Latvia",
  "Estonia",
  "Poland",
  "Germany",
  "United Kingdom",
  "United States",
  "France",
  "Spain",
  "Italy",
  "Netherlands",
  "Sweden",
  "Finland",
  "Norway",
  "Denmark",
  "Ireland",
  "Czech Republic",
  "Austria",
  "Switzerland",
] as const;

// Map Intl timezone region codes to our target market options
const TIMEZONE_TO_COUNTRY: Record<string, string> = {
  LT: "Lithuania",
  LV: "Latvia",
  EE: "Estonia",
  PL: "Poland",
  DE: "Germany",
  GB: "United Kingdom",
  US: "United States",
  FR: "France",
  ES: "Spain",
  IT: "Italy",
  NL: "Netherlands",
  SE: "Sweden",
  FI: "Finland",
  NO: "Norway",
  DK: "Denmark",
  IE: "Ireland",
  CZ: "Czech Republic",
  AT: "Austria",
  CH: "Switzerland",
};

function detectCountryFromTimezone(): string | null {
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    // Extract region from IANA timezone (e.g. "Europe/Vilnius" → look up mapping)
    const tzToRegion: Record<string, string> = {
      "Europe/Vilnius": "LT", "Europe/Riga": "LV", "Europe/Tallinn": "EE",
      "Europe/Warsaw": "PL", "Europe/Berlin": "DE", "Europe/London": "GB",
      "America/New_York": "US", "America/Chicago": "US", "America/Denver": "US",
      "America/Los_Angeles": "US", "America/Anchorage": "US", "Pacific/Honolulu": "US",
      "Europe/Paris": "FR", "Europe/Madrid": "ES", "Europe/Rome": "IT",
      "Europe/Amsterdam": "NL", "Europe/Stockholm": "SE", "Europe/Helsinki": "FI",
      "Europe/Oslo": "NO", "Europe/Copenhagen": "DK", "Europe/Dublin": "IE",
      "Europe/Prague": "CZ", "Europe/Vienna": "AT", "Europe/Zurich": "CH",
    };
    const region = tzToRegion[tz];
    if (region) return TIMEZONE_TO_COUNTRY[region] ?? null;
  } catch {
    // Intl not available
  }
  return null;
}

export function IdeaForm() {
  const t = useTranslations("ideaForm");
  const locale = useLocale();
  const [idea, setIdea] = useState("");
  const [targetMarket, setTargetMarket] = useState(() => {
    // Priority: locale hint → timezone detection → Global
    if (locale === "lt") return "Lithuania";
    return detectCountryFromTimezone() ?? "Global";
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [needsCredits, setNeedsCredits] = useState(false);
  const router = useRouter();
  const { user, session, refreshUser } = useAuth();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    if (!user || !session) {
      router.push("/login");
      return;
    }

    const validationError = validateIdea(idea);
    if (validationError) {
      setError(t(validationError));
      return;
    }

    setLoading(true);
    setError("");
    setNeedsCredits(false);

    try {
      const res = await createValidation(idea.trim(), locale, targetMarket);
      posthog.capture("validation_started", { validation_id: res.id, target_market: targetMarket });
      refreshUser();
      router.push(`/validations/${res.id}`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 402) {
        setNeedsCredits(true);
      } else if (err instanceof ApiError && err.status === 422) {
        const key = mapBackendError(err.message, "ideaRejected");
        setError(t(key));
      } else {
        const key = err instanceof Error ? mapBackendError(err.message, "somethingWentWrong") : "somethingWentWrong";
        setError(t(key));
      }
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-3xl">
      <div className="relative">
        <textarea
          value={idea}
          onChange={(e) => {
            setIdea(e.target.value);
            setError("");
            setNeedsCredits(false);
          }}
          placeholder={t("placeholder")}
          maxLength={500}
          rows={3}
          className="w-full resize-none rounded-2xl border border-card-border bg-white/[0.03] px-6 py-4 pr-14 text-lg text-foreground placeholder:text-muted/50 focus:border-white/20 focus:outline-none focus:ring-0 transition-colors"
        />
        <span className="absolute bottom-3 right-4 text-xs text-muted/40">
          {idea.length}/500
        </span>
      </div>

      <div className="mt-3 flex items-center gap-3">
        <label htmlFor="target-market" className="shrink-0 text-sm text-muted/70">
          {t("targetMarket")}
        </label>
        <select
          id="target-market"
          value={targetMarket}
          onChange={(e) => setTargetMarket(e.target.value)}
          className="w-full rounded-xl border border-card-border bg-white/[0.03] px-4 py-2 text-sm text-foreground transition-colors focus:border-white/20 focus:outline-none focus:ring-0"
        >
          {TARGET_MARKET_OPTIONS.map((country) => (
            <option key={country} value={country}>
              {t(`country${country.replace(/\s/g, "")}` as Parameters<typeof t>[0])}
            </option>
          ))}
        </select>
      </div>

      {error && <p role="alert" className="mt-3 text-sm text-skip">{error}</p>}

      {needsCredits && (
        <div role="alert" className="mt-3 rounded-xl border border-maybe/30 bg-maybe/5 px-4 py-3 text-sm text-maybe">
          {t("outOfCredits")}{" "}
          <Link href="/credits" className="underline hover:text-foreground">
            {t("buyMoreCredits")}
          </Link>{" "}
          {t("toContinue")}
        </div>
      )}

      <button
        type="submit"
        disabled={loading || idea.trim().length < 10}
        className="mt-4 w-full rounded-full border border-foreground bg-foreground px-8 py-3 text-base font-medium text-background transition-all hover:bg-transparent hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40"
      >
        {loading ? (
          <span className="inline-flex items-center gap-2">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-background border-t-transparent" />
            {t("validating")}
          </span>
        ) : !user ? (
          t("signInToValidate")
        ) : (
          t("validate")
        )}
      </button>
    </form>
  );
}
