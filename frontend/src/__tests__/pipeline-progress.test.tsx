import { render, screen, act, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { PipelineProgress } from "@/components/pipeline-progress";
import { mockCompletedRun } from "./fixtures";

// Mock auth context
vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({
    user: { id: "u1", email: "test@test.com", credits: 3, created_at: "2025-01-01" },
    session: { access_token: "test-token" },
    loading: false,
    signUp: vi.fn(),
    signIn: vi.fn(),
    signOut: vi.fn(),
    refreshUser: vi.fn(),
  }),
}));

// Mock API — getStreamUrl is async now
vi.mock("@/lib/api", () => ({
  getStreamUrl: vi.fn((id: string) => Promise.resolve(`http://localhost:8000/api/validations/${id}/stream`)),
  getValidation: vi.fn(),
}));

import { getValidation } from "@/lib/api";

// Mock EventSource
type EventHandler = (event: MessageEvent) => void;

class MockEventSource {
  static instances: MockEventSource[] = [];
  url: string;
  listeners: Record<string, EventHandler[]> = {};

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  addEventListener(event: string, handler: EventHandler) {
    if (!this.listeners[event]) this.listeners[event] = [];
    this.listeners[event].push(handler);
  }

  close = vi.fn();

  // Test helper: emit an event
  emit(event: string, data: unknown) {
    const handlers = this.listeners[event] || [];
    handlers.forEach((handler) => {
      handler({ data: JSON.stringify(data) } as MessageEvent);
    });
  }
}

/** Get the most recent MockEventSource instance (handles React strict mode double-mount). */
function latestES() {
  return MockEventSource.instances[MockEventSource.instances.length - 1];
}

/** Render and wait for EventSource to be instantiated (async connect). */
async function renderAndWaitForES(
  props: { runId: string; onComplete: ReturnType<typeof vi.fn>; onError: ReturnType<typeof vi.fn> }
) {
  let result!: ReturnType<typeof render>;
  await act(async () => {
    result = render(<PipelineProgress {...props} />);
  });
  await waitFor(() => expect(MockEventSource.instances.length).toBeGreaterThan(0));
  return result;
}

describe("PipelineProgress", () => {
  const onComplete = vi.fn();
  const onError = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    MockEventSource.instances = [];
    vi.stubGlobal("EventSource", MockEventSource);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders all 4 agent names", async () => {
    await renderAndWaitForES({ runId: "run-123", onComplete, onError });

    expect(screen.getByText("pain & user discovery")).toBeInTheDocument();
    expect(screen.getByText("competitor research")).toBeInTheDocument();
    expect(screen.getByText("viability analysis")).toBeInTheDocument();
    expect(screen.getByText("synthesis & verdict")).toBeInTheDocument();
  });

  it("connects to the correct SSE URL", async () => {
    await renderAndWaitForES({ runId: "run-123", onComplete, onError });

    expect(MockEventSource.instances.length).toBeGreaterThanOrEqual(1);
    expect(latestES().url).toBe(
      "http://localhost:8000/api/validations/run-123/stream"
    );
  });

  it("starts with agent 1 running", async () => {
    await renderAndWaitForES({ runId: "run-123", onComplete, onError });

    // Agent 1 should show its description (running state)
    expect(
      screen.getByText("searching reddit, hn, forums for real pain points")
    ).toBeInTheDocument();
  });

  it("marks agent as done on agent_completed event", async () => {
    await renderAndWaitForES({ runId: "run-123", onComplete, onError });

    const es = latestES();

    await act(async () => {
      es.emit("agent_completed", { agent: 1, name: "pain_discovery", output: {} });
    });

    // Agent 1 should show "complete"
    const completeTexts = screen.getAllByText("complete");
    expect(completeTexts.length).toBeGreaterThanOrEqual(1);
  });

  it("shows verdict on pipeline_completed", async () => {
    vi.mocked(getValidation).mockResolvedValue(mockCompletedRun);

    await renderAndWaitForES({ runId: "run-123", onComplete, onError });

    const es = latestES();

    await act(async () => {
      es.emit("pipeline_completed", { id: "run-123", verdict: "BUILD", confidence: 0.78 });
    });

    expect(screen.getByText("build")).toBeInTheDocument();
    expect(screen.getByText("78% confidence")).toBeInTheDocument();
  });

  it("calls onComplete with fetched run after pipeline_completed", async () => {
    vi.mocked(getValidation).mockResolvedValue(mockCompletedRun);

    await renderAndWaitForES({ runId: "run-123", onComplete, onError });

    const es = latestES();

    await act(async () => {
      es.emit("pipeline_completed", { id: "run-123", verdict: "BUILD", confidence: 0.78 });
    });

    expect(getValidation).toHaveBeenCalledWith("run-123");
    expect(onComplete).toHaveBeenCalledWith(mockCompletedRun);
  });

  it("calls onError on pipeline_error", async () => {
    await renderAndWaitForES({ runId: "run-123", onComplete, onError });

    const es = latestES();

    act(() => {
      es.emit("pipeline_error", { error: "Agent failed" });
    });

    expect(onError).toHaveBeenCalledWith("Agent failed");
    expect(screen.getByText("pipeline failed — check server logs")).toBeInTheDocument();
  });

  it("closes EventSource on unmount", async () => {
    const { unmount } = await renderAndWaitForES({ runId: "run-123", onComplete, onError });

    const es = latestES();
    unmount();

    expect(es.close).toHaveBeenCalled();
  });

  it("calls onError when getValidation fails after pipeline_completed", async () => {
    vi.mocked(getValidation).mockRejectedValue(new Error("fetch failed"));

    await renderAndWaitForES({ runId: "run-123", onComplete, onError });

    const es = latestES();

    await act(async () => {
      es.emit("pipeline_completed", { id: "run-123", verdict: "BUILD", confidence: 0.78 });
    });

    expect(onError).toHaveBeenCalledWith("failed to fetch results");
  });
});
