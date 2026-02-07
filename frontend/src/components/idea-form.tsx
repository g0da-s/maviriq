"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createValidation } from "@/lib/api";

export function IdeaForm() {
  const [idea, setIdea] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (idea.trim().length < 3) {
      setError("idea must be at least 3 characters");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const res = await createValidation(idea.trim());
      router.push(`/validations/${res.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "something went wrong");
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl">
      <div className="relative">
        <textarea
          value={idea}
          onChange={(e) => {
            setIdea(e.target.value);
            setError("");
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

      {error && <p className="mt-3 text-sm text-skip">{error}</p>}

      <button
        type="submit"
        disabled={loading || idea.trim().length < 3}
        className="mt-4 w-full rounded-full border border-foreground bg-foreground px-8 py-3 text-base font-medium text-background transition-all hover:bg-transparent hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40"
      >
        {loading ? (
          <span className="inline-flex items-center gap-2">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-background border-t-transparent" />
            validating...
          </span>
        ) : (
          "validate"
        )}
      </button>
    </form>
  );
}
