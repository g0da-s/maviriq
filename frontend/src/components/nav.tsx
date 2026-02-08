"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export function Nav() {
  const pathname = usePathname();
  const isHome = pathname === "/";
  const isHistory = pathname.startsWith("/validations");
  const { user, loading, signOut } = useAuth();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-card-border bg-background/80 backdrop-blur-md">
      <div className="flex items-center justify-between px-8 py-4">
        <Link href="/" className="font-display text-2xl font-bold tracking-tight">
          maverick
        </Link>
        <div className="flex items-center gap-1">
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
                new
              </Link>
              <Link
                href="/validations"
                className={`rounded-lg px-3 py-1.5 text-sm transition-colors ${
                  isHistory
                    ? "bg-white/10 text-foreground"
                    : "text-muted hover:bg-white/5 hover:text-foreground"
                }`}
              >
                history
              </Link>
              <Link
                href="/credits"
                className={`rounded-lg px-3 py-1.5 text-sm transition-colors ${
                  pathname === "/credits"
                    ? "bg-white/10 text-foreground"
                    : "text-muted hover:bg-white/5 hover:text-foreground"
                }`}
              >
                {user.credits} credit{user.credits !== 1 ? "s" : ""}
              </Link>
              <div className="mx-2 h-4 w-px bg-card-border" />
              <button
                onClick={signOut}
                className="rounded-lg px-3 py-1.5 text-sm text-muted transition-colors hover:bg-white/5 hover:text-foreground"
              >
                log out
              </button>
            </>
          ) : (
            <>
              <Link
                href="/login"
                className="rounded-lg px-3 py-1.5 text-sm text-muted transition-colors hover:bg-white/5 hover:text-foreground"
              >
                log in
              </Link>
              <Link
                href="/register"
                className="rounded-lg bg-foreground px-4 py-1.5 text-sm font-medium text-background transition-colors hover:bg-foreground/80"
              >
                sign up
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
