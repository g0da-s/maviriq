import { z, type ZodType } from "zod";
import {
  CheckoutResponseSchema,
  CreateValidationResponseSchema,
  ValidationListResponseSchema,
  ValidationRunSchema,
} from "./types";
import type {
  CheckoutResponse,
  CreateValidationResponse,
  ValidationListResponse,
  ValidationRun,
} from "./types";
import { supabase } from "./supabase";

const DeleteResponseSchema = z.object({ status: z.string() });

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

async function getAccessToken(): Promise<string | null> {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}

async function request<T>(
  path: string,
  schema: ZodType<T>,
  options?: RequestInit,
  _isRetry = false,
): Promise<T> {
  const token = await getAccessToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15_000);
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers,
      signal: controller.signal,
      ...options,
    });
    if (res.status === 401 && !_isRetry) {
      // Token expired mid-session — refresh and retry once
      const { data: { session } } = await supabase.auth.refreshSession();
      if (session?.access_token) {
        return request(path, schema, options, true);
      }
    }
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError(res.status, body.detail || `Request failed: ${res.status}`);
    }
    const data = await res.json();
    return schema.parse(data);
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("Request timed out");
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
}

// ── Stripe ──

export function createCheckout(pack: number) {
  return request<CheckoutResponse>("/stripe/checkout", CheckoutResponseSchema, {
    method: "POST",
    body: JSON.stringify({ pack }),
  });
}

// ── Validations ──

export function createValidation(idea: string) {
  return request<CreateValidationResponse>("/validations", CreateValidationResponseSchema, {
    method: "POST",
    body: JSON.stringify({ idea }),
  });
}

export function getValidation(id: string) {
  return request<ValidationRun>(`/validations/${id}`, ValidationRunSchema);
}

export function listValidations(page = 1, perPage = 20) {
  return request<ValidationListResponse>(
    `/validations?page=${page}&per_page=${perPage}`,
    ValidationListResponseSchema,
  );
}

export function deleteValidation(id: string) {
  return request<{ status: string }>(`/validations/${id}`, DeleteResponseSchema, {
    method: "DELETE",
  });
}

const StreamTokenSchema = z.object({ token: z.string() });

export async function getStreamUrl(id: string): Promise<string> {
  const { token } = await request<{ token: string }>(
    `/validations/${id}/stream-token`,
    StreamTokenSchema,
    { method: "POST" },
  );
  return `${API_BASE}/validations/${id}/stream?token=${encodeURIComponent(token)}`;
}
