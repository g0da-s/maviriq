"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html lang="en" className="dark">
      <body className="bg-background text-foreground">
        <div className="flex min-h-screen flex-col items-center justify-center gap-4 pt-20">
          <p className="font-display text-lg font-bold">something went wrong</p>
          <p className="text-sm text-muted">an unexpected error occurred</p>
          <button
            onClick={reset}
            className="rounded-lg border border-card-border px-4 py-2 text-sm text-muted transition-colors hover:bg-white/5"
          >
            try again
          </button>
        </div>
      </body>
    </html>
  );
}
