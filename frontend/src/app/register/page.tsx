"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [emailSent, setEmailSent] = useState(false);
  const { signUp } = useAuth();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password !== confirm) {
      setError("passwords don't match");
      return;
    }
    if (password.length < 8) {
      setError("password must be at least 8 characters");
      return;
    }

    setLoading(true);
    setError("");

    const { error: signUpError, needsVerification } = await signUp(email, password);
    if (signUpError) {
      setError(signUpError);
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
          <h1 className="font-display text-3xl font-bold">check your email</h1>
          <p className="mt-4 text-sm text-muted">
            we sent a verification link to{" "}
            <strong className="text-foreground">{email}</strong>. click it to
            activate your account and get your free credit.
          </p>
          <Link
            href="/login"
            className="mt-8 inline-block text-sm text-foreground hover:underline"
          >
            go to login
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <h1 className="font-display text-3xl font-bold text-center">sign up</h1>
        <p className="mt-2 text-center text-sm text-muted">
          get 1 free validation after verifying your email
        </p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="email"
            required
            className="w-full rounded-xl border border-card-border bg-white/[0.03] px-4 py-3 text-sm text-foreground placeholder:text-muted/50 focus:border-white/20 focus:outline-none transition-colors"
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="password"
            required
            minLength={8}
            className="w-full rounded-xl border border-card-border bg-white/[0.03] px-4 py-3 text-sm text-foreground placeholder:text-muted/50 focus:border-white/20 focus:outline-none transition-colors"
          />
          <input
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            placeholder="confirm password"
            required
            className="w-full rounded-xl border border-card-border bg-white/[0.03] px-4 py-3 text-sm text-foreground placeholder:text-muted/50 focus:border-white/20 focus:outline-none transition-colors"
          />

          {error && <p className="text-sm text-skip">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-full border border-foreground bg-foreground px-6 py-3 text-sm font-medium text-background transition-all hover:bg-transparent hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40"
          >
            {loading ? "creating account..." : "create account"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-muted">
          already have an account?{" "}
          <Link href="/login" className="text-foreground hover:underline">
            log in
          </Link>
        </p>
      </div>
    </div>
  );
}
