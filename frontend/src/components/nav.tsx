"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations, useLocale } from "next-intl";
import { useAuth } from "@/lib/auth-context";
import { ltPlural } from "@/lib/plural";

function switchLocale(newLocale: string) {
  document.cookie = `locale=${newLocale};path=/;max-age=31536000`;
  window.location.reload();
}

function LanguageToggle() {
  const locale = useLocale();
  return (
    <div className="flex items-center gap-0.5 rounded-lg border border-card-border text-xs">
      <button
        onClick={() => switchLocale("lt")}
        className={`rounded-l-md px-2 py-1 transition-colors ${
          locale === "lt"
            ? "bg-white/10 text-foreground font-semibold"
            : "text-muted hover:text-foreground"
        }`}
      >
        LT
      </button>
      <button
        onClick={() => switchLocale("en")}
        className={`rounded-r-md px-2 py-1 transition-colors ${
          locale === "en"
            ? "bg-white/10 text-foreground font-semibold"
            : "text-muted hover:text-foreground"
        }`}
      >
        EN
      </button>
    </div>
  );
}

export function Nav() {
  const pathname = usePathname();
  const isHome = pathname === "/";
  const isHistory = pathname.startsWith("/validations");
  const { user, loading, signOut } = useAuth();
  const [open, setOpen] = useState(false);
  const t = useTranslations("nav");
  const tc = useTranslations("common");
  const locale = useLocale();

  const creditsText = user
    ? t(`credits${locale === "lt" ? ({ one: "One", few: "Few", other: "Other" } as const)[ltPlural(user.credits)] : user.credits === 1 ? "One" : "Other"}`, { count: user.credits })
    : "";

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-card-border bg-background/80 backdrop-blur-md">
      <div className="flex items-center justify-between px-8 py-4">
        <Link href="/" className="font-display text-2xl font-bold tracking-tight">
          maviriq
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-1">
          {loading ? (
            <div className="h-4 w-20 animate-pulse rounded bg-white/5" />
          ) : user ? (
            <>
              <Link
                href="/"
                className={`rounded-lg px-3 py-1.5 text-sm transition-colors ${
                  isHome
                    ? "bg-white/10 text-foreground"
                    : "text-muted hover:bg-white/5 hover:text-foreground"
                }`}
              >
                {t("new")}
              </Link>
              <Link
                href="/validations"
                className={`rounded-lg px-3 py-1.5 text-sm transition-colors ${
                  isHistory
                    ? "bg-white/10 text-foreground"
                    : "text-muted hover:bg-white/5 hover:text-foreground"
                }`}
              >
                {t("history")}
              </Link>
              <Link
                href="/credits"
                className={`rounded-lg px-3 py-1.5 text-sm transition-colors ${
                  pathname === "/credits"
                    ? "bg-white/10 text-foreground"
                    : "text-muted hover:bg-white/5 hover:text-foreground"
                }`}
              >
                {creditsText}
              </Link>
              <div className="mx-2 h-4 w-px bg-card-border" />
              <button
                onClick={signOut}
                className="rounded-lg px-3 py-1.5 text-sm text-muted transition-colors hover:bg-white/5 hover:text-foreground"
              >
                {tc("logOut")}
              </button>
              <div className="mx-1 h-4 w-px bg-card-border" />
              <LanguageToggle />
            </>
          ) : (
            <>
              <LanguageToggle />
              <div className="mx-1 h-4 w-px bg-card-border" />
              <Link
                href="/login"
                className="rounded-lg px-3 py-1.5 text-sm text-muted transition-colors hover:bg-white/5 hover:text-foreground"
              >
                {tc("logIn")}
              </Link>
              <Link
                href="/register"
                className="rounded-lg bg-foreground px-4 py-1.5 text-sm font-medium text-background transition-colors hover:bg-foreground/80"
              >
                {tc("signUp")}
              </Link>
            </>
          )}
        </div>

        {/* Mobile hamburger */}
        <button
          onClick={() => setOpen(!open)}
          className="md:hidden flex flex-col justify-center gap-1.5 p-2"
          aria-label={t("toggleMenu")}
        >
          <span className={`block h-px w-5 bg-foreground transition-all ${open ? "translate-y-[3.5px] rotate-45" : ""}`} />
          <span className={`block h-px w-5 bg-foreground transition-all ${open ? "opacity-0" : ""}`} />
          <span className={`block h-px w-5 bg-foreground transition-all ${open ? "-translate-y-[3.5px] -rotate-45" : ""}`} />
        </button>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="md:hidden border-t border-card-border px-8 py-4 space-y-1">
          {loading ? (
            <div className="h-4 w-20 animate-pulse rounded bg-white/5" />
          ) : user ? (
            <>
              <Link
                href="/"
                onClick={() => setOpen(false)}
                className={`block rounded-lg px-3 py-2 text-sm transition-colors ${
                  isHome
                    ? "bg-white/10 text-foreground"
                    : "text-muted hover:bg-white/5 hover:text-foreground"
                }`}
              >
                {t("new")}
              </Link>
              <Link
                href="/validations"
                onClick={() => setOpen(false)}
                className={`block rounded-lg px-3 py-2 text-sm transition-colors ${
                  isHistory
                    ? "bg-white/10 text-foreground"
                    : "text-muted hover:bg-white/5 hover:text-foreground"
                }`}
              >
                {t("history")}
              </Link>
              <Link
                href="/credits"
                onClick={() => setOpen(false)}
                className={`block rounded-lg px-3 py-2 text-sm transition-colors ${
                  pathname === "/credits"
                    ? "bg-white/10 text-foreground"
                    : "text-muted hover:bg-white/5 hover:text-foreground"
                }`}
              >
                {creditsText}
              </Link>
              <div className="my-2 flex items-center gap-2">
                <LanguageToggle />
              </div>
              <div className="my-2 h-px bg-card-border" />
              <button
                onClick={() => { signOut(); setOpen(false); }}
                className="block w-full text-left rounded-lg px-3 py-2 text-sm text-muted transition-colors hover:bg-white/5 hover:text-foreground"
              >
                {tc("logOut")}
              </button>
            </>
          ) : (
            <>
              <div className="mb-2">
                <LanguageToggle />
              </div>
              <Link
                href="/login"
                onClick={() => setOpen(false)}
                className="block rounded-lg px-3 py-2 text-sm text-muted transition-colors hover:bg-white/5 hover:text-foreground"
              >
                {tc("logIn")}
              </Link>
              <Link
                href="/register"
                onClick={() => setOpen(false)}
                className="block rounded-lg px-3 py-2 text-sm text-muted transition-colors hover:bg-white/5 hover:text-foreground"
              >
                {tc("signUp")}
              </Link>
            </>
          )}
        </div>
      )}
    </nav>
  );
}
