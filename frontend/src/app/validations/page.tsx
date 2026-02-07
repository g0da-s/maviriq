"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { deleteValidation, listValidations } from "@/lib/api";
import type { ValidationListItem, ValidationListResponse } from "@/lib/types";
import { VerdictBadge } from "@/components/verdict-badge";

export default function HistoryPage() {
  const [data, setData] = useState<ValidationListResponse | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);

  const load = useCallback(async (p: number) => {
    setLoading(true);
    try {
      const res = await listValidations(p);
      setData(res);
      setPage(p);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(1);
  }, [load]);

  async function handleDelete(id: string) {
    if (!confirm("delete this validation?")) return;
    setDeleting(id);
    try {
      await deleteValidation(id);
      load(page);
    } catch {
      // ignore
    } finally {
      setDeleting(null);
    }
  }

  const totalPages = data ? Math.ceil(data.total / data.per_page) : 0;

  return (
    <div className="mx-auto max-w-3xl px-6 pt-28 pb-16">
      <div className="mb-8 flex items-center justify-between">
        <h1 className="font-display text-3xl font-bold">history</h1>
        <Link
          href="/"
          className="rounded-full border border-card-border px-4 py-1.5 text-sm transition-colors hover:bg-white/5"
        >
          new validation
        </Link>
      </div>

      {loading && !data ? (
        <div className="flex justify-center py-20">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-foreground border-t-transparent" />
        </div>
      ) : !data || data.items.length === 0 ? (
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
                  onClick={() => handleDelete(item.id)}
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
              <button
                onClick={() => load(page - 1)}
                disabled={page <= 1}
                className="rounded-lg border border-card-border px-3 py-1.5 text-sm text-muted transition-colors hover:bg-white/5 disabled:opacity-30"
              >
                prev
              </button>
              <span className="px-3 text-sm text-muted">
                {page} / {totalPages}
              </span>
              <button
                onClick={() => load(page + 1)}
                disabled={page >= totalPages}
                className="rounded-lg border border-card-border px-3 py-1.5 text-sm text-muted transition-colors hover:bg-white/5 disabled:opacity-30"
              >
                next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
