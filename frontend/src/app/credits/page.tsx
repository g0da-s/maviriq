"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { createCheckout } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

const PACKS = [
  { credits: 5, price: "$5", pricePerCredit: "$1.00", label: "Starter" },
  { credits: 20, price: "$15", pricePerCredit: "$0.75", label: "Popular", highlight: true },
  { credits: 50, price: "$30", pricePerCredit: "$0.60", label: "Pro" },
];

export default function CreditsPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-foreground border-t-transparent" />
      </div>
    }>
      <CreditsContent />
    </Suspense>
  );
}

function CreditsContent() {
  const { user, token, loading: authLoading, refreshUser } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [purchasing, setPurchasing] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  // Handle return from Stripe
  useEffect(() => {
    if (searchParams.get("success") === "true") {
      setSuccess(true);
      refreshUser();
    }
  }, [searchParams, refreshUser]);

  // Redirect if not logged in
  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [authLoading, user, router]);

  async function handleBuy(pack: number) {
    if (!token) return;
    setPurchasing(pack);
    setError("");

    try {
      const res = await createCheckout(pack, token);
      window.location.href = res.checkout_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "checkout failed");
      setPurchasing(null);
    }
  }

  if (authLoading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-foreground border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-6 pt-28 pb-16">
      <div className="text-center">
        <h1 className="font-display text-3xl font-bold">credits</h1>
        <p className="mt-2 text-muted">
          you have{" "}
          <span className="font-display font-bold text-foreground">
            {user.credits}
          </span>{" "}
          credit{user.credits !== 1 ? "s" : ""} remaining
        </p>
      </div>

      {success && (
        <div className="mt-6 rounded-xl border border-build/30 bg-build/5 px-4 py-3 text-center text-sm text-build">
          credits added successfully!
        </div>
      )}

      {searchParams.get("canceled") === "true" && (
        <div className="mt-6 rounded-xl border border-maybe/30 bg-maybe/5 px-4 py-3 text-center text-sm text-maybe">
          checkout was canceled
        </div>
      )}

      {error && (
        <div className="mt-6 rounded-xl border border-skip/30 bg-skip/5 px-4 py-3 text-center text-sm text-skip">
          {error}
        </div>
      )}

      {/* Pricing Cards */}
      <div className="mt-10 grid gap-4 sm:grid-cols-3">
        {PACKS.map((pack) => (
          <div
            key={pack.credits}
            className={`relative rounded-2xl border p-6 text-center transition-colors ${
              pack.highlight
                ? "border-build/40 bg-build/5"
                : "border-card-border bg-card"
            }`}
          >
            {pack.highlight && (
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-build px-3 py-0.5 text-xs font-medium text-background">
                best value
              </span>
            )}
            <p className="text-xs uppercase tracking-wider text-muted/60">
              {pack.label}
            </p>
            <p className="mt-3 font-display text-4xl font-bold">
              {pack.credits}
            </p>
            <p className="text-sm text-muted">credits</p>
            <p className="mt-4 font-display text-2xl font-bold">{pack.price}</p>
            <p className="text-xs text-muted/50">
              {pack.pricePerCredit} per validation
            </p>
            <button
              onClick={() => handleBuy(pack.credits)}
              disabled={purchasing !== null}
              className={`mt-6 w-full rounded-full px-4 py-2.5 text-sm font-medium transition-all disabled:cursor-not-allowed disabled:opacity-40 ${
                pack.highlight
                  ? "bg-build text-background hover:bg-build/80"
                  : "border border-card-border hover:bg-white/5"
              }`}
            >
              {purchasing === pack.credits ? (
                <span className="inline-flex items-center gap-2">
                  <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
                  redirecting...
                </span>
              ) : (
                `buy ${pack.credits} credits`
              )}
            </button>
          </div>
        ))}
      </div>

      <div className="mt-8 text-center">
        <Link
          href="/"
          className="text-sm text-muted hover:text-foreground transition-colors"
        >
          &larr; back to validation
        </Link>
      </div>
    </div>
  );
}
