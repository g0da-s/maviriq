"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function Nav() {
  const pathname = usePathname();
  const isHome = pathname === "/";
  const isHistory = pathname.startsWith("/validations");

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-card-border bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <Link href="/" className="font-display text-xl font-bold tracking-tight">
          maverick
        </Link>
        <div className="flex items-center gap-6">
          <Link
            href="/validations"
            className={`text-sm transition-colors hover:text-foreground ${
              isHistory ? "text-foreground" : "text-muted"
            }`}
          >
            history
          </Link>
          <Link
            href="/"
            className={`rounded-full border px-4 py-1.5 text-sm transition-colors ${
              isHome
                ? "border-foreground/20 bg-white/5 text-foreground"
                : "border-card-border text-muted hover:bg-white/5"
            }`}
          >
            new validation
          </Link>
        </div>
      </div>
    </nav>
  );
}
