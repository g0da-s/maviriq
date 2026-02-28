"use client";

import { useTranslations } from "next-intl";
import { useNetworkStatus } from "@/hooks/use-network-status";

export function OfflineBanner() {
  const t = useTranslations("offline");
  const online = useNetworkStatus();

  if (online) return null;

  return (
    <div
      role="alert"
      className="fixed top-0 left-0 right-0 z-50 bg-skip px-4 py-2 text-center text-sm font-medium text-background"
    >
      {t("message")}
    </div>
  );
}
