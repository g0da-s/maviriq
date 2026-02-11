"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [waitingForAuth, setWaitingForAuth] = useState(false);
  const router = useRouter();
  const { signIn, user } = useAuth();

  // Redirect when user is set after successful login
  useEffect(() => {
    if (waitingForAuth && user) {
      router.push("/");
    }
  }, [waitingForAuth, user, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    const { error: signInError } = await signIn(email, password);
    if (signInError) {
      setError(signInError);
      setLoading(false);
      return;
    }

    // Set flag to wait for user to be populated by auth state change
    setWaitingForAuth(true);
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <h1 className="font-display text-3xl font-bold text-center">log in</h1>
        <p className="mt-2 text-center text-sm text-muted">
          welcome back to maverick
        </p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          <div>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="email"
              required
              className="w-full rounded-xl border border-card-border bg-white/[0.03] px-4 py-3 text-sm text-foreground placeholder:text-muted/50 focus:border-white/20 focus:outline-none transition-colors"
            />
          </div>
          <div>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="password"
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
            {loading ? "logging in..." : "log in"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-muted">
          don&apos;t have an account?{" "}
          <Link href="/register" className="text-foreground hover:underline">
            sign up
          </Link>
        </p>
      </div>
    </div>
  );
}
