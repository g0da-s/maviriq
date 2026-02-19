"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import posthog from "posthog-js";
import { createValidation, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

const BLOCKED_WORDS = new Set([
  "fuck", "shit", "ass", "bitch", "damn", "cunt", "dick", "cock",
  "pussy", "whore", "slut", "bastard", "nigger", "nigga", "faggot",
  "retard", "retarded",
]);

const CONSONANT_MASH = /[^aeiou\s\d\W]{5,}/i;
const REPEATED_CHARS = /(.)\1{2,}/;

function validateIdea(text: string): string | null {
  const trimmed = text.trim();
  const words = trimmed.split(/\s+/).filter((w) => w.length > 0);

  if (trimmed.length < 10 || words.length < 3) {
    return "please describe your idea in at least a few words";
  }

  // Profanity check
  const inputWords = new Set(trimmed.toLowerCase().match(/[a-z]+/g) ?? []);
  for (const bad of BLOCKED_WORDS) {
    if (inputWords.has(bad)) return "please keep your input appropriate";
  }

  // Gibberish check — flag words with 5+ consecutive consonants or repeated chars
  const substantialWords = words.filter((w) => w.length > 3);
  if (substantialWords.length > 0) {
    const gibberishCount = substantialWords.filter(
      (w) => CONSONANT_MASH.test(w) || REPEATED_CHARS.test(w),
    ).length;
    if (gibberishCount / substantialWords.length > 0.3) {
      return "your input doesn't look like a real idea — please try again";
    }
  }

  return null;
}

export function IdeaForm() {
  const [idea, setIdea] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [needsCredits, setNeedsCredits] = useState(false);
  const router = useRouter();
  const { user, session } = useAuth();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    if (!user || !session) {
      router.push("/login");
      return;
    }

    const validationError = validateIdea(idea);
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);
    setError("");
    setNeedsCredits(false);

    try {
      const res = await createValidation(idea.trim());
      posthog.capture("validation_started", { validation_id: res.id });
      router.push(`/validations/${res.id}`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 402) {
        setNeedsCredits(true);
      } else {
        setError(err instanceof Error ? err.message : "something went wrong");
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
          placeholder="describe your startup idea..."
          maxLength={500}
          rows={3}
          className="w-full resize-none rounded-2xl border border-card-border bg-white/[0.03] px-6 py-4 text-lg text-foreground placeholder:text-muted/50 focus:border-white/20 focus:outline-none focus:ring-0 transition-colors"
        />
        <span className="absolute bottom-3 right-4 text-xs text-muted/40">
          {idea.length}/500
        </span>
      </div>

      {error && <p role="alert" className="mt-3 text-sm text-skip">{error}</p>}

      {needsCredits && (
        <div role="alert" className="mt-3 rounded-xl border border-maybe/30 bg-maybe/5 px-4 py-3 text-sm text-maybe">
          you&apos;re out of credits.{" "}
          <Link href="/credits" className="underline hover:text-foreground">
            buy more credits
          </Link>{" "}
          to continue validating ideas.
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
            validating...
          </span>
        ) : !user ? (
          "sign in to validate"
        ) : (
          "validate"
        )}
      </button>
    </form>
  );
}
