import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Competitors } from "@/components/competitors";
import { mockCompetitorResearch } from "./fixtures";

describe("Competitors", () => {
  it("renders market saturation", () => {
    render(<Competitors data={mockCompetitorResearch} />);
    expect(screen.getByText("saturation")).toBeInTheDocument();
    expect(screen.getByText("high")).toBeInTheDocument();
  });

  it("renders average price point", () => {
    render(<Competitors data={mockCompetitorResearch} />);
    expect(screen.getByText("avg price")).toBeInTheDocument();
    expect(screen.getByText("$12/mo")).toBeInTheDocument();
  });

  it("renders competitor count", () => {
    render(<Competitors data={mockCompetitorResearch} />);
    // "competitors" appears twice: in stat card and as section header
    const matches = screen.getAllByText("competitors");
    expect(matches.length).toBe(2);
  });

  it("renders competitor name as link", () => {
    render(<Competitors data={mockCompetitorResearch} />);
    const link = screen.getByText("Calendly");
    expect(link.closest("a")).toHaveAttribute("href", "https://calendly.com");
  });

  it("renders competitor one-liner", () => {
    render(<Competitors data={mockCompetitorResearch} />);
    expect(screen.getByText("Simple scheduling ahead")).toBeInTheDocument();
  });

  it("renders competitor pricing plans", () => {
    render(<Competitors data={mockCompetitorResearch} />);
    expect(screen.getByText("Free: $0/mo")).toBeInTheDocument();
    expect(screen.getByText("Pro: $10/mo")).toBeInTheDocument();
  });

  it("renders competitor strengths", () => {
    render(<Competitors data={mockCompetitorResearch} />);
    expect(screen.getByText("+ Easy to use")).toBeInTheDocument();
    expect(screen.getByText("+ Well-known brand")).toBeInTheDocument();
  });

  it("renders competitor weaknesses", () => {
    render(<Competitors data={mockCompetitorResearch} />);
    expect(screen.getByText("- Limited AI features")).toBeInTheDocument();
    expect(screen.getByText("- No team coordination")).toBeInTheDocument();
  });

  it("renders review sentiment and count", () => {
    render(<Competitors data={mockCompetitorResearch} />);
    expect(screen.getByText("positive (450)")).toBeInTheDocument();
  });

  it("renders underserved needs", () => {
    render(<Competitors data={mockCompetitorResearch} />);
    expect(screen.getByText("AI-powered scheduling")).toBeInTheDocument();
    expect(screen.getByText("Team coordination")).toBeInTheDocument();
  });

  it("renders common complaints", () => {
    render(<Competitors data={mockCompetitorResearch} />);
    expect(screen.getByText("Too expensive")).toBeInTheDocument();
    expect(screen.getByText("Poor integration")).toBeInTheDocument();
  });

  it("hides underserved needs when empty", () => {
    const noNeeds = { ...mockCompetitorResearch, underserved_needs: [] };
    render(<Competitors data={noNeeds} />);
    expect(screen.queryByText("underserved needs")).not.toBeInTheDocument();
  });

  it("hides common complaints when empty", () => {
    const noComplaints = { ...mockCompetitorResearch, common_complaints: [] };
    render(<Competitors data={noComplaints} />);
    expect(screen.queryByText("common complaints")).not.toBeInTheDocument();
  });
});
