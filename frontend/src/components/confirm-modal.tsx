"use client";

import { useEffect, useRef } from "react";

export function ConfirmModal({
  open,
  title,
  description,
  confirmLabel = "delete",
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  description?: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (open) cancelRef.current?.focus();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onCancel();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onCancel}
      />
      {/* modal */}
      <div className="relative w-full max-w-sm rounded-2xl border border-card-border bg-card p-6 shadow-xl">
        <p className="font-display text-lg font-bold">{title}</p>
        {description && (
          <p className="mt-2 text-sm text-muted leading-relaxed">{description}</p>
        )}
        <div className="mt-6 flex items-center justify-end gap-3">
          <button
            ref={cancelRef}
            onClick={onCancel}
            className="rounded-lg border border-card-border px-4 py-2 text-sm text-muted transition-colors hover:bg-white/5"
          >
            cancel
          </button>
          <button
            onClick={onConfirm}
            className="rounded-lg bg-skip/10 border border-skip/30 px-4 py-2 text-sm text-skip transition-colors hover:bg-skip/20"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
