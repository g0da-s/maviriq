"use client";

import type { ReactNode } from "react";
import { AuthProvider } from "@/lib/auth-context";
import { PostHogProvider } from "@/lib/posthog";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <PostHogProvider>
      <AuthProvider>{children}</AuthProvider>
    </PostHogProvider>
  );
}
