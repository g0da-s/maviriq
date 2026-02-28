"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { supabase } from "@/lib/supabase";
import { mapSupabaseError } from "@/lib/supabase-error";

export default function ResetPasswordPage() {
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);
  const [expired, setExpired] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();
  const t = useTranslations('resetPassword');

  // Check for error params from Supabase (e.g. expired link)
  useEffect(() => {
    const errorCode = searchParams.get("error_code");
    if (errorCode === "otp_expired") {
      setExpired(true);
    }
  }, [searchParams]);

  useEffect(() => {
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event) => {
      if (event === "PASSWORD_RECOVERY") {
        setReady(true);
      }
    });

    // The PASSWORD_RECOVERY event may have already fired before this
    // component mounted (caught by auth-context). If there's already
    // a session, show the form immediately.
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        setReady(true);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (password.length < 8) {
      setError(t('passwordMinLength'));
      return;
    }

    if (password !== confirmPassword) {
      setError(t('passwordsDontMatch'));
      return;
    }

    setLoading(true);

    const { error: updateError } = await supabase.auth.updateUser({
      password,
    });

    if (updateError) {
      const key = mapSupabaseError(updateError.message, {}, "authError");
      setError(t(key));
      setLoading(false);
      return;
    }

    router.push("/");
  }

  if (expired) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center px-6">
        <div className="w-full max-w-sm text-center">
          <h1 className="font-display text-3xl font-bold">{t('linkExpired')}</h1>
          <p className="mt-4 text-sm text-muted">
            {t('linkExpiredMessage')}
          </p>
          <Link
            href="/forgot-password"
            className="mt-6 inline-block rounded-full border border-foreground bg-foreground px-6 py-3 text-sm font-medium text-background transition-all hover:bg-transparent hover:text-foreground"
          >
            {t('sendNewResetLink')}
          </Link>
        </div>
      </div>
    );
  }

  if (!ready) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center px-6">
        <div className="w-full max-w-sm text-center">
          <p className="text-sm text-muted">{t('verifyingResetLink')}</p>
          <Link
            href="/forgot-password"
            className="mt-4 inline-block text-sm text-muted hover:text-foreground transition-colors"
          >
            {t('requestNewLink')}
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
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={t('newPassword')}
              required
              className="w-full rounded-xl border border-card-border bg-white/[0.03] px-4 py-3 text-sm text-foreground placeholder:text-muted/50 focus:border-white/20 focus:outline-none transition-colors"
            />
          </div>
          <div>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder={t('confirmNewPassword')}
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
            {loading ? t('updating') : t('updatePassword')}
          </button>
        </form>
      </div>
    </div>
  );
}
