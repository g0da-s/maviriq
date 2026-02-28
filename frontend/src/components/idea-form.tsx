"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import posthog from "posthog-js";
import { useTranslations, useLocale } from "next-intl";
import { createValidation, transcribeAudio, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

const BLOCKED_WORDS = new Set([
  "fuck", "shit", "ass", "bitch", "damn", "cunt", "dick", "cock",
  "pussy", "whore", "slut", "bastard", "nigger", "nigga", "faggot",
  "retard", "retarded",
]);

// Include Lithuanian consonants (č, š, ž) and vowels (ą, ę, ė, į, ū)
const CONSONANT_MASH = /[^aeiouąęėįū\s\d\W]{5,}/i;
const REPEATED_CHARS = /(.)\1{2,}/;

function validateIdea(text: string): string | null {
  const trimmed = text.trim();
  const words = trimmed.split(/\s+/).filter((w) => w.length > 0);

  if (trimmed.length < 10 || words.length < 3) {
    return "errorMinLength";
  }

  // Profanity check
  const inputWords = new Set(trimmed.toLowerCase().match(/[a-z]+/g) ?? []);
  for (const bad of BLOCKED_WORDS) {
    if (inputWords.has(bad)) return "errorProfanity";
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

function getSupportedMimeType(): string {
  if (typeof MediaRecorder !== "undefined") {
    if (MediaRecorder.isTypeSupported("audio/webm")) return "audio/webm";
    if (MediaRecorder.isTypeSupported("audio/mp4")) return "audio/mp4";
  }
  return "audio/webm";
}

export function IdeaForm() {
  const t = useTranslations("ideaForm");
  const locale = useLocale();
  const [idea, setIdea] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [needsCredits, setNeedsCredits] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const router = useRouter();
  const { user, session } = useAuth();

  async function toggleRecording() {
    if (isRecording) {
      mediaRecorderRef.current?.stop();
      setIsRecording(false);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = getSupportedMimeType();
      const recorder = new MediaRecorder(stream, { mimeType });
      chunksRef.current = [];

      recorder.ondataavailable = (e) => chunksRef.current.push(e.data);
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: mimeType });
        setIsTranscribing(true);
        try {
          const text = await transcribeAudio(blob);
          setIdea((prev) => (prev + " " + text).trim().slice(0, 500));
        } catch {
          setError(t("transcriptionFailed"));
        } finally {
          setIsTranscribing(false);
        }
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
    } catch {
      setError(t("micDenied"));
    }
  }

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
      const res = await createValidation(idea.trim(), locale);
      posthog.capture("validation_started", { validation_id: res.id });
      router.push(`/validations/${res.id}`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 402) {
        setNeedsCredits(true);
      } else {
        setError(err instanceof Error ? err.message : t("transcriptionFailed"));
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
        {/* Mic button */}
        <button
          type="button"
          onClick={toggleRecording}
          disabled={isTranscribing || loading}
          className="absolute bottom-3 left-4 rounded-lg p-1.5 text-muted/50 transition-colors hover:text-foreground disabled:opacity-40"
          aria-label={isRecording ? t("stopRecording") : t("startRecording")}
        >
          {isTranscribing ? (
            <span className="block h-5 w-5 animate-spin rounded-full border-2 border-muted border-t-transparent" />
          ) : isRecording ? (
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5 text-skip animate-pulse">
              <path d="M12 2a3 3 0 0 0-3 3v6a3 3 0 1 0 6 0V5a3 3 0 0 0-3-3Z" />
              <path d="M19 10a1 1 0 0 0-2 0 5 5 0 0 1-10 0 1 1 0 1 0-2 0 7 7 0 0 0 6 6.93V20H8a1 1 0 1 0 0 2h8a1 1 0 1 0 0-2h-3v-3.07A7 7 0 0 0 19 10Z" />
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5">
              <path d="M12 2a3 3 0 0 0-3 3v6a3 3 0 1 0 6 0V5a3 3 0 0 0-3-3Z" />
              <path d="M19 10a1 1 0 0 0-2 0 5 5 0 0 1-10 0 1 1 0 1 0-2 0 7 7 0 0 0 6 6.93V20H8a1 1 0 1 0 0 2h8a1 1 0 1 0 0-2h-3v-3.07A7 7 0 0 0 19 10Z" />
            </svg>
          )}
        </button>
        <span className="absolute bottom-3 right-4 text-xs text-muted/40">
          {idea.length}/500
        </span>
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
