"use client";

import { useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useAuth } from "@/lib/auth-context";
import { mapSupabaseError } from "@/lib/supabase-error";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [emailSent, setEmailSent] = useState(false);
  const { signUp, signInWithGoogle } = useAuth();
  const t = useTranslations('register');
  const tc = useTranslations('common');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password !== confirm) {
      setError(t('passwordsDontMatch'));
      return;
    }
    if (password.length < 8) {
      setError(t('passwordMinLength'));
      return;
    }

    setLoading(true);
    setError("");

    const { error: signUpError, needsVerification } = await signUp(email, password);
    if (signUpError) {
      const key = mapSupabaseError(signUpError, {
        "already registered": "emailAlreadyRegistered",
        "already been registered": "emailAlreadyRegistered",
        "user already registered": "emailAlreadyRegistered",
      }, "authError");
      setError(t(key));
      setLoading(false);
      return;
    }
    if (needsVerification) {
      setEmailSent(true);
    }
    setLoading(false);
  }

  if (emailSent) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center px-6">
        <div className="w-full max-w-sm text-center">
          <h1 className="font-display text-3xl font-bold">{t('checkYourEmail')}</h1>
          <p className="mt-4 text-sm text-muted">
            {t('verificationSent', { email })}
          </p>
          <Link
            href="/login"
            className="mt-8 inline-block text-sm text-foreground hover:underline"
          >
            {t('goToLogin')}
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <h1 className="font-display text-3xl font-bold text-center">{t('title')}</h1>
        <p className="mt-2 text-center text-sm text-muted">
          {t('subtitle')}
        </p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder={t('email')}
            required
            className="w-full rounded-xl border border-card-border bg-white/[0.03] px-4 py-3 text-sm text-foreground placeholder:text-muted/50 focus:border-white/20 focus:outline-none transition-colors"
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={t('password')}
            required
            minLength={8}
            className="w-full rounded-xl border border-card-border bg-white/[0.03] px-4 py-3 text-sm text-foreground placeholder:text-muted/50 focus:border-white/20 focus:outline-none transition-colors"
          />
          <input
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            placeholder={t('confirmPassword')}
            required
            className="w-full rounded-xl border border-card-border bg-white/[0.03] px-4 py-3 text-sm text-foreground placeholder:text-muted/50 focus:border-white/20 focus:outline-none transition-colors"
          />

          {error && <p role="alert" className="text-sm text-skip">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-full border border-foreground bg-foreground px-6 py-3 text-sm font-medium text-background transition-all hover:bg-transparent hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40"
          >
            {loading ? t('creatingAccount') : t('createAccount')}
          </button>
        </form>

        <div className="mt-4 flex items-center gap-3">
          <div className="h-px flex-1 bg-card-border" />
          <span className="text-xs text-muted/50">{tc('or')}</span>
          <div className="h-px flex-1 bg-card-border" />
        </div>

        <button
          type="button"
          onClick={() => signInWithGoogle()}
          className="mt-4 flex w-full items-center justify-center gap-3 rounded-full border border-card-border px-6 py-3 text-sm font-medium text-foreground transition-colors hover:bg-white/5"
        >
          <svg className="h-4 w-4" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
          </svg>
          {t('continueWithGoogle')}
        </button>

        <p className="mt-6 text-center text-sm text-muted">
          {t('alreadyHaveAccount')}{" "}
          <Link href="/login" className="text-foreground hover:underline">
            {tc('logIn')}
          </Link>
        </p>
      </div>
    </div>
  );
}
