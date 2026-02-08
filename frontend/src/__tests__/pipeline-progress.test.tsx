import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { PipelineProgress } from "@/components/pipeline-progress";
import { mockCompletedRun } from "./fixtures";

// Mock auth context
vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({
    user: { id: "u1", email: "test@test.com", credits: 3, created_at: "2025-01-01" },
    token: "test-token",
    loading: false,
    logout: vi.fn(),
    login: vi.fn(),
    refreshUser: vi.fn(),
  }),
}));

// Mock API
vi.mock("@/lib/api", () => ({
  getStreamUrl: vi.fn((id: string) => `http://localhost:8000/api/validations/${id}/stream`),
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

  it("renders all 4 agent names", () => {
    render(<PipelineProgress runId="run-123" onComplete={onComplete} onError={onError} />);

    expect(screen.getByText("pain & user discovery")).toBeInTheDocument();
    expect(screen.getByText("competitor research")).toBeInTheDocument();
    expect(screen.getByText("viability analysis")).toBeInTheDocument();
    expect(screen.getByText("synthesis & verdict")).toBeInTheDocument();
  });

  it("connects to the correct SSE URL", () => {
    render(<PipelineProgress runId="run-123" onComplete={onComplete} onError={onError} />);

    expect(MockEventSource.instances).toHaveLength(1);
    expect(MockEventSource.instances[0].url).toBe(
      "http://localhost:8000/api/validations/run-123/stream"
    );
  });

  it("starts with agent 1 running", () => {
    render(<PipelineProgress runId="run-123" onComplete={onComplete} onError={onError} />);

    // Agent 1 should show its description (running state)
    expect(
      screen.getByText("searching reddit, hn, forums for real pain points")
    ).toBeInTheDocument();
  });

  it("advances to next agent on agent_completed event", () => {
    render(<PipelineProgress runId="run-123" onComplete={onComplete} onError={onError} />);

    const es = MockEventSource.instances[0];

    act(() => {
      es.emit("agent_completed", { agent: 1, name: "pain_discovery", output: {} });
    });

    // Agent 2 should now be running
    expect(
      screen.getByText("mapping competitors, pricing, reviews on g2 & capterra")
    ).toBeInTheDocument();
  });

  it("shows verdict on pipeline_completed", async () => {
    vi.mocked(getValidation).mockResolvedValue(mockCompletedRun);

    render(<PipelineProgress runId="run-123" onComplete={onComplete} onError={onError} />);

    const es = MockEventSource.instances[0];

    await act(async () => {
      es.emit("pipeline_completed", { id: "run-123", verdict: "BUILD", confidence: 0.78 });
    });

    expect(screen.getByText("build")).toBeInTheDocument();
    expect(screen.getByText("78% confidence")).toBeInTheDocument();
  });

  it("calls onComplete with fetched run after pipeline_completed", async () => {
    vi.mocked(getValidation).mockResolvedValue(mockCompletedRun);

    render(<PipelineProgress runId="run-123" onComplete={onComplete} onError={onError} />);

    const es = MockEventSource.instances[0];

    await act(async () => {
      es.emit("pipeline_completed", { id: "run-123", verdict: "BUILD", confidence: 0.78 });
    });

    expect(getValidation).toHaveBeenCalledWith("run-123", "test-token");
    expect(onComplete).toHaveBeenCalledWith(mockCompletedRun);
  });

  it("calls onError on pipeline_error", () => {
    render(<PipelineProgress runId="run-123" onComplete={onComplete} onError={onError} />);

    const es = MockEventSource.instances[0];

    act(() => {
      es.emit("pipeline_error", { error: "Agent failed" });
    });

    expect(onError).toHaveBeenCalledWith("Agent failed");
    expect(screen.getByText("pipeline failed — check server logs")).toBeInTheDocument();
  });

  it("closes EventSource on unmount", () => {
    const { unmount } = render(
      <PipelineProgress runId="run-123" onComplete={onComplete} onError={onError} />
    );

    const es = MockEventSource.instances[0];
    unmount();

    expect(es.close).toHaveBeenCalled();
  });

  it("calls onError when getValidation fails after pipeline_completed", async () => {
    vi.mocked(getValidation).mockRejectedValue(new Error("fetch failed"));

    render(<PipelineProgress runId="run-123" onComplete={onComplete} onError={onError} />);

    const es = MockEventSource.instances[0];

    await act(async () => {
      es.emit("pipeline_completed", { id: "run-123", verdict: "BUILD", confidence: 0.78 });
    });

    expect(onError).toHaveBeenCalledWith("failed to fetch results");
  });
});
