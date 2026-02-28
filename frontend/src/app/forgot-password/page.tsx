"use client";

import { useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { supabase } from "@/lib/supabase";
import { mapSupabaseError } from "@/lib/supabase-error";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);
  const t = useTranslations('forgotPassword');
  const tc = useTranslations('common');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    const { error: resetError } = await supabase.auth.resetPasswordForEmail(
      email,
      { redirectTo: `${window.location.origin}/reset-password` }
    );

    if (resetError) {
      const key = mapSupabaseError(resetError.message, {}, "authError");
      setError(t(key));
      setLoading(false);
      return;
    }

    setSent(true);
    setLoading(false);
  }

  if (sent) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center px-6">
        <div className="w-full max-w-sm text-center">
          <h1 className="font-display text-3xl font-bold">{t('checkYourEmail')}</h1>
          <p className="mt-4 text-sm text-muted">
            {t('resetLinkSent', { email })}
          </p>
          <Link
            href="/login"
            className="mt-8 inline-block text-sm text-muted hover:text-foreground transition-colors"
          >
            {t('backToLogin')}
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <h1 className="font-display text-3xl font-bold text-center">
          {t('title')}
        </h1>
        <p className="mt-2 text-center text-sm text-muted">
          {t('subtitle')}
        </p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          <div>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder={t('email')}
              required
              className="w-full rounded-xl border border-card-border bg-white/[0.03] px-4 py-3 text-sm text-foreground placeholder:text-muted/50 focus:border-white/20 focus:outline-none transition-colors"
            />
          </div>

          {error && <p role="alert" className="text-sm text-skip">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-full border border-foreground bg-foreground px-6 py-3 text-sm font-medium text-background transition-all hover:bg-transparent hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40"
          >
            {loading ? t('sending') : t('sendResetLink')}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-muted">
          {t('rememberPassword')}{" "}
          <Link href="/login" className="text-foreground hover:underline">
            {tc('logIn')}
          </Link>
        </p>
      </div>
    </div>
  );
}
