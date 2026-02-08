import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { PainPoints } from "@/components/pain-points";
import { mockPainDiscovery } from "./fixtures";

describe("PainPoints", () => {
  it("renders the pain summary", () => {
    render(<PainPoints data={mockPainDiscovery} />);
    expect(
      screen.getByText("Meeting scheduling is a significant pain point for tech professionals.")
    ).toBeInTheDocument();
  });

  it("renders primary target user label", () => {
    render(<PainPoints data={mockPainDiscovery} />);
    // "Engineering Managers" appears in both primary target user and user segments
    const matches = screen.getAllByText("Engineering Managers");
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });

  it("renders primary target user description", () => {
    render(<PainPoints data={mockPainDiscovery} />);
    expect(screen.getByText("Mid-level managers at tech companies")).toBeInTheDocument();
  });

  it("renders pain point quotes", () => {
    render(<PainPoints data={mockPainDiscovery} />);
    expect(screen.getByText(/Scheduling meetings is a nightmare/)).toBeInTheDocument();
    expect(screen.getByText(/I spend 2 hours a week just scheduling/)).toBeInTheDocument();
  });

  it("renders pain point sources", () => {
    render(<PainPoints data={mockPainDiscovery} />);
    expect(screen.getByText("Reddit")).toBeInTheDocument();
  });

  it("shows pain points count", () => {
    render(<PainPoints data={mockPainDiscovery} />);
    expect(screen.getByText("pain points (2)")).toBeInTheDocument();
  });

  it("renders user segments when more than 1", () => {
    render(<PainPoints data={mockPainDiscovery} />);
    expect(screen.getByText("user segments (2)")).toBeInTheDocument();
    expect(screen.getByText("Startup Founders")).toBeInTheDocument();
  });

  it("hides user segments when only 1", () => {
    const singleSegment = {
      ...mockPainDiscovery,
      user_segments: [mockPainDiscovery.user_segments[0]],
    };
    render(<PainPoints data={singleSegment} />);
    expect(screen.queryByText(/user segments/)).not.toBeInTheDocument();
  });

  it("renders pain severity dots", () => {
    const { container } = render(<PainPoints data={mockPainDiscovery} />);
    // Each pain point has 5 dots, 2 pain points = 10 dots
    const allDots = container.querySelectorAll(".rounded-full.h-1\\.5");
    expect(allDots.length).toBe(10);
  });
});
