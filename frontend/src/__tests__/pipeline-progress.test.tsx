import { render, screen, act, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { PipelineProgress } from "@/components/pipeline-progress";
import { mockCompletedRun, mockRunningRun, mockMidPipelineRun } from "./fixtures";

// Mock next-intl — returns the key as the translated string
vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

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
    // Default: getValidation returns a fresh running run (no agents completed)
    vi.mocked(getValidation).mockResolvedValue(mockRunningRun);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders all agent names", async () => {
    await renderAndWaitForES({ runId: "run-123", onComplete, onError });

    // i18n keys are returned as-is by our mock
    expect(screen.getByText("agent0Name")).toBeInTheDocument();
    expect(screen.getByText("agent1Name")).toBeInTheDocument();
    expect(screen.getByText("agent2Name")).toBeInTheDocument();
    expect(screen.getByText("agent3Name")).toBeInTheDocument();
    expect(screen.getByText("agent4Name")).toBeInTheDocument();
    expect(screen.getByText("agent5Name")).toBeInTheDocument();
  });

  it("connects to the correct SSE URL", async () => {
    await renderAndWaitForES({ runId: "run-123", onComplete, onError });

    expect(MockEventSource.instances.length).toBeGreaterThanOrEqual(1);
    expect(latestES().url).toBe(
      "http://localhost:8000/api/validations/run-123/stream"
    );
  });

  it("starts with agent 0 (context research) running", async () => {
    await renderAndWaitForES({ runId: "run-123", onComplete, onError });

    // Agent 0 should show its description (running state) — our mock returns the key
    expect(screen.getByText("agent0Desc")).toBeInTheDocument();
  });

  it("marks agent as done on agent_completed event", async () => {
    await renderAndWaitForES({ runId: "run-123", onComplete, onError });

    const es = latestES();

    await act(async () => {
      es.emit("agent_completed", { agent: 0, output: {} });
    });

    // Agent 0 should show "complete" (i18n key)
    const completeTexts = screen.getAllByText("complete");
    expect(completeTexts.length).toBeGreaterThanOrEqual(1);
  });

  it("lights up agents 1-4 after agent 0 completes", async () => {
    await renderAndWaitForES({ runId: "run-123", onComplete, onError });

    const es = latestES();

    await act(async () => {
      es.emit("agent_completed", { agent: 0, output: {} });
    });

    // Agents 1-4 should show their descriptions (running state)
    expect(screen.getByText("agent1Desc")).toBeInTheDocument();
    expect(screen.getByText("agent2Desc")).toBeInTheDocument();
    expect(screen.getByText("agent3Desc")).toBeInTheDocument();
    expect(screen.getByText("agent4Desc")).toBeInTheDocument();
  });

  it("calls onComplete with fetched run after pipeline_completed", async () => {
    vi.mocked(getValidation)
      .mockResolvedValueOnce(mockRunningRun) // initial status check
      .mockResolvedValueOnce(mockCompletedRun); // fetch after pipeline_completed

    await renderAndWaitForES({ runId: "run-123", onComplete, onError });

    const es = latestES();

    await act(async () => {
      es.emit("pipeline_completed", { id: "run-123", verdict: "BUILD", confidence: 0.78 });
    });

    expect(onComplete).toHaveBeenCalledWith(mockCompletedRun);
  });

  it("calls onError on pipeline_error", async () => {
    await renderAndWaitForES({ runId: "run-123", onComplete, onError });

    const es = latestES();

    act(() => {
      es.emit("pipeline_error", { error: "Agent failed" });
    });

    // mapBackendError falls through to "somethingWentWrong", t() returns the key
    expect(onError).toHaveBeenCalledWith("somethingWentWrong");
  });

  it("closes EventSource on unmount", async () => {
    const { unmount } = await renderAndWaitForES({ runId: "run-123", onComplete, onError });

    const es = latestES();
    unmount();

    expect(es.close).toHaveBeenCalled();
  });

  it("calls onError when getValidation fails after pipeline_completed", async () => {
    vi.mocked(getValidation)
      .mockResolvedValueOnce(mockRunningRun) // initial status check
      .mockRejectedValueOnce(new Error("fetch failed")); // fetch after pipeline_completed

    await renderAndWaitForES({ runId: "run-123", onComplete, onError });

    const es = latestES();

    await act(async () => {
      es.emit("pipeline_completed", { id: "run-123", verdict: "BUILD", confidence: 0.78 });
    });

    expect(onError).toHaveBeenCalledWith("failedToFetchResults");
  });

  it("pre-populates completed agents from DB on reconnect", async () => {
    // Simulate a mid-pipeline state: agent 0 and 1 already completed
    vi.mocked(getValidation).mockResolvedValue(mockMidPipelineRun);

    await renderAndWaitForES({ runId: "run-mid", onComplete, onError });

    // Agents 0 and 1 should show "complete" immediately
    const completeTexts = screen.getAllByText("complete");
    expect(completeTexts.length).toBeGreaterThanOrEqual(2);

    // Agents 2, 3, 4 should be running (show descriptions)
    expect(screen.getByText("agent2Desc")).toBeInTheDocument();
    expect(screen.getByText("agent3Desc")).toBeInTheDocument();
    expect(screen.getByText("agent4Desc")).toBeInTheDocument();
  });

  it("completes immediately when pipeline already finished", async () => {
    vi.mocked(getValidation).mockResolvedValue(mockCompletedRun);

    await act(async () => {
      render(
        <PipelineProgress runId="run-123" onComplete={onComplete} onError={onError} />
      );
    });

    expect(onComplete).toHaveBeenCalledWith(mockCompletedRun);
  });
});
