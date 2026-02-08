import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  createValidation,
  getValidation,
  listValidations,
  deleteValidation,
  getStreamUrl,
} from "@/lib/api";
import { mockCompletedRun, mockValidationList } from "./fixtures";

const mockFetch = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", mockFetch);
});

afterEach(() => {
  vi.restoreAllMocks();
});

function jsonResponse(data: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
  });
}

function errorResponse(detail: string, status = 400) {
  return Promise.resolve({
    ok: false,
    status,
    json: () => Promise.resolve({ detail }),
  });
}

describe("createValidation", () => {
  it("sends POST with idea and returns parsed response", async () => {
    const responseData = {
      id: "run-123",
      idea: "test idea",
      status: "pending",
      stream_url: "/api/validations/run-123/stream",
    };
    mockFetch.mockReturnValue(jsonResponse(responseData));

    const result = await createValidation("test idea");

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/validations",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ idea: "test idea" }),
        headers: { "Content-Type": "application/json" },
      })
    );
    expect(result).toEqual(responseData);
  });

  it("throws on API error with detail message", async () => {
    mockFetch.mockReturnValue(errorResponse("Idea is too short"));

    await expect(createValidation("ab")).rejects.toThrow("Idea is too short");
  });

  it("throws on API error with status when no detail", async () => {
    mockFetch.mockReturnValue(
      Promise.resolve({
        ok: false,
        status: 500,
        json: () => Promise.reject(new Error("parse error")),
      })
    );

    await expect(createValidation("test")).rejects.toThrow("Request failed: 500");
  });
});

describe("getValidation", () => {
  it("fetches a single validation by id", async () => {
    mockFetch.mockReturnValue(jsonResponse(mockCompletedRun));

    const result = await getValidation("run-123");

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/validations/run-123",
      expect.objectContaining({
        headers: { "Content-Type": "application/json" },
      })
    );
    expect(result.id).toBe("run-123");
    expect(result.status).toBe("completed");
  });

  it("throws on 404", async () => {
    mockFetch.mockReturnValue(errorResponse("Not found", 404));

    await expect(getValidation("missing")).rejects.toThrow("Not found");
  });
});

describe("listValidations", () => {
  it("fetches paginated list with defaults", async () => {
    mockFetch.mockReturnValue(jsonResponse(mockValidationList));

    const result = await listValidations();

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/validations?page=1&per_page=20",
      expect.objectContaining({
        headers: { "Content-Type": "application/json" },
      })
    );
    expect(result.items).toHaveLength(3);
    expect(result.total).toBe(3);
  });

  it("passes custom page and perPage", async () => {
    mockFetch.mockReturnValue(jsonResponse(mockValidationList));

    await listValidations(2, 10);

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/validations?page=2&per_page=10",
      expect.anything()
    );
  });
});

describe("deleteValidation", () => {
  it("sends DELETE request", async () => {
    mockFetch.mockReturnValue(jsonResponse({ status: "deleted" }));

    const result = await deleteValidation("run-123");

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/validations/run-123",
      expect.objectContaining({
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
      })
    );
    expect(result.status).toBe("deleted");
  });

  it("throws on server error", async () => {
    mockFetch.mockReturnValue(errorResponse("Internal error", 500));

    await expect(deleteValidation("run-123")).rejects.toThrow("Internal error");
  });
});

describe("getStreamUrl", () => {
  it("returns the correct SSE URL", () => {
    const url = getStreamUrl("run-123");
    expect(url).toBe("http://localhost:8000/api/validations/run-123/stream");
  });
});

describe("request timeout", () => {
  it("throws on timeout", async () => {
    mockFetch.mockImplementation(
      (_url: string, opts: RequestInit) =>
        new Promise((_resolve, reject) => {
          opts.signal?.addEventListener("abort", () => {
            reject(new DOMException("The operation was aborted.", "AbortError"));
          });
        })
    );

    // We mock AbortController to fire immediately
    const originalAbortController = globalThis.AbortController;
    const mockAbort = vi.fn();
    const mockSignal = {
      aborted: false,
      addEventListener: vi.fn((_event: string, handler: () => void) => {
        // Trigger abort immediately
        setTimeout(handler, 0);
      }),
      removeEventListener: vi.fn(),
    };

    vi.stubGlobal(
      "AbortController",
      class {
        signal = mockSignal;
        abort = () => {
          mockSignal.aborted = true;
          mockAbort();
        };
      }
    );

    await expect(getValidation("run-123")).rejects.toThrow("Request timed out");

    vi.stubGlobal("AbortController", originalAbortController);
  });
});
