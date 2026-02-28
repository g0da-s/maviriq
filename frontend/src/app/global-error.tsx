"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";

const translations: Record<string, { somethingWentWrong: string; unexpectedError: string; tryAgain: string }> = {
  en: { somethingWentWrong: "something went wrong", unexpectedError: "an unexpected error occurred", tryAgain: "try again" },
  lt: { somethingWentWrong: "kažkas nepavyko", unexpectedError: "įvyko netikėta klaida", tryAgain: "bandyti dar kartą" },
};

function getLocale(): string {
  try {
    const match = document.cookie.match(/(?:^|; )locale=([^;]*)/);
    return match?.[1] || "en";
  } catch {
    return "en";
  }
}

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const locale = getLocale();
  const t = translations[locale] || translations.en;

  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html lang={locale} className="dark">
      <body className="bg-background text-foreground">
        <div className="flex min-h-screen flex-col items-center justify-center gap-4 pt-20">
          <p className="font-display text-lg font-bold">{t.somethingWentWrong}</p>
          <p className="text-sm text-muted">{t.unexpectedError}</p>
          <button
            onClick={reset}
            className="rounded-lg border border-card-border px-4 py-2 text-sm text-muted transition-colors hover:bg-white/5"
          >
            {t.tryAgain}
          </button>
        </div>
      </body>
    </html>
  );
}
