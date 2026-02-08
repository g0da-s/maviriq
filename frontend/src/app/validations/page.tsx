"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { deleteValidation, listValidations } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { ValidationListItem, ValidationListResponse } from "@/lib/types";
import { VerdictBadge } from "@/components/verdict-badge";
import { ConfirmModal } from "@/components/confirm-modal";

export default function HistoryPage() {
  return (
    <Suspense fallback={
      <div className="mx-auto max-w-3xl px-6 pt-28 pb-16">
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-center gap-4 rounded-2xl border border-card-border bg-card p-5">
              <div className="w-28 shrink-0">
                <div className="h-6 w-16 animate-pulse rounded-full bg-white/5" />
              </div>
              <div className="flex-1 min-w-0 space-y-2">
                <div className="h-4 w-3/4 animate-pulse rounded bg-white/5" />
                <div className="h-3 w-1/3 animate-pulse rounded bg-white/5" />
              </div>
            </div>
          ))}
        </div>
      </div>
    }>
      <HistoryContent />
    </Suspense>
  );
}

function HistoryContent() {
  const searchParams = useSearchParams();
  const page = Math.max(1, Number(searchParams.get("page")) || 1);
  const { user, session, loading: authLoading } = useAuth();
  const router = useRouter();

  const [data, setData] = useState<ValidationListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async (p: number) => {
    if (!session) return;
    setLoading(true);
    setError("");
    try {
      const res = await listValidations(p, 20);
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "failed to load validations");
    } finally {
      setLoading(false);
    }
  }, [session]);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
      return;
    }
    if (session) load(page);
  }, [load, page, authLoading, user, session, router]);

  async function handleDelete() {
    if (!confirmId) return;
    const id = confirmId;
    setConfirmId(null);
    setDeleting(id);
    setError("");
    try {
      await deleteValidation(id);
      load(page);
    } catch (err) {
      setError(err instanceof Error ? err.message : "failed to delete validation");
    } finally {
      setDeleting(null);
    }
  }

  const totalPages = data ? Math.ceil(data.total / data.per_page) : 0;

  return (
    <div className="mx-auto max-w-3xl px-6 pt-28 pb-16">
      <ConfirmModal
        open={confirmId !== null}
        title="delete this validation?"
        description="this action cannot be undone."
        onConfirm={handleDelete}
        onCancel={() => setConfirmId(null)}
      />
      <div className="mb-8 flex items-center justify-between">
        <h1 className="font-display text-3xl font-bold">history</h1>
        <Link
          href="/"
          className="rounded-full border border-card-border px-4 py-1.5 text-sm transition-colors hover:bg-white/5"
        >
          new validation
        </Link>
      </div>

      {error && (
        <div className="mb-4 rounded-xl border border-skip/30 bg-skip/5 px-4 py-3 text-sm text-skip">
          {error}
        </div>
      )}

      {loading && !data ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-center gap-4 rounded-2xl border border-card-border bg-card p-5">
              <div className="w-28 shrink-0">
                <div className="h-6 w-16 animate-pulse rounded-full bg-white/5" />
              </div>
              <div className="flex-1 min-w-0 space-y-2">
                <div className="h-4 w-3/4 animate-pulse rounded bg-white/5" />
                <div className="h-3 w-1/3 animate-pulse rounded bg-white/5" />
              </div>
            </div>
          ))}
        </div>
      ) : error && !data ? null : !data || data.items.length === 0 ? (
        <div className="rounded-2xl border border-card-border bg-card p-12 text-center">
          <p className="text-muted">no validations yet</p>
          <Link href="/" className="mt-4 inline-block text-sm text-build hover:underline">
            validate your first idea
          </Link>
        </div>
      ) : (
        <>
          <div className="space-y-3">
            {data.items.map((item: ValidationListItem) => (
              <div
                key={item.id}
                className="group flex items-center gap-4 rounded-2xl border border-card-border bg-card p-5 transition-colors hover:border-white/10"
              >
                <Link href={`/validations/${item.id}`} className="flex flex-1 items-center gap-4">
                  {/* verdict */}
                  <div className="w-28 shrink-0">
                    {item.verdict ? (
                      <VerdictBadge verdict={item.verdict} size="sm" />
                    ) : (
                      <span className="inline-block rounded-full border border-card-border px-3 py-0.5 text-xs text-muted">
                        {item.status}
                      </span>
                    )}
                  </div>

                  {/* idea */}
                  <div className="flex-1 min-w-0">
                    <p className="truncate text-sm font-medium">{item.idea}</p>
                    <p className="mt-0.5 text-xs text-muted/50">
                      {item.confidence !== null && `${Math.round(item.confidence * 100)}% confidence · `}
                      {item.created_at
                        ? new Date(item.created_at).toLocaleDateString()
                        : item.id}
                    </p>
                  </div>
                </Link>

                {/* delete */}
                <button
                  onClick={() => setConfirmId(item.id)}
                  disabled={deleting === item.id}
                  className="shrink-0 rounded-lg p-2 text-muted/30 opacity-0 transition-all hover:bg-skip/10 hover:text-skip group-hover:opacity-100"
                >
                  {deleting === item.id ? (
                    <div className="h-4 w-4 animate-spin rounded-full border border-skip border-t-transparent" />
                  ) : (
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  )}
                </button>
              </div>
            ))}
          </div>

          {/* pagination */}
          {totalPages > 1 && (
            <div className="mt-8 flex items-center justify-center gap-2">
              <Link
                href={`/validations?page=${page - 1}`}
                className={`rounded-lg border border-card-border px-3 py-1.5 text-sm text-muted transition-colors hover:bg-white/5 ${page <= 1 ? "pointer-events-none opacity-30" : ""}`}
              >
                prev
              </Link>
              <span className="px-3 text-sm text-muted">
                {page} / {totalPages}
              </span>
              <Link
                href={`/validations?page=${page + 1}`}
                className={`rounded-lg border border-card-border px-3 py-1.5 text-sm text-muted transition-colors hover:bg-white/5 ${page >= totalPages ? "pointer-events-none opacity-30" : ""}`}
              >
                next
              </Link>
            </div>
          )}
        </>
      )}
    </div>
  );
}
