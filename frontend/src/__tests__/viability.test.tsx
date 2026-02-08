import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Viability } from "@/components/viability";
import { mockViability } from "./fixtures";

describe("Viability", () => {
  it("renders opportunity score as percentage", () => {
    render(<Viability data={mockViability} />);
    // 0.72 → 72
    expect(screen.getByText("72")).toBeInTheDocument();
  });

  it("shows 'strong opportunity' for score >= 70", () => {
    render(<Viability data={mockViability} />);
    expect(screen.getByText("strong opportunity")).toBeInTheDocument();
  });

  it("shows 'moderate opportunity' for score 50-69", () => {
    const moderate = { ...mockViability, opportunity_score: 0.55 };
    render(<Viability data={moderate} />);
    expect(screen.getByText("moderate opportunity")).toBeInTheDocument();
  });

  it("shows 'weak opportunity' for score < 50", () => {
    const weak = { ...mockViability, opportunity_score: 0.3 };
    render(<Viability data={weak} />);
    expect(screen.getByText("weak opportunity")).toBeInTheDocument();
  });

  it("renders people_pay as yes/no", () => {
    render(<Viability data={mockViability} />);
    expect(screen.getByText("yes")).toBeInTheDocument();
  });

  it("renders people_pay reasoning", () => {
    render(<Viability data={mockViability} />);
    expect(
      screen.getByText("Strong willingness to pay observed across multiple segments")
    ).toBeInTheDocument();
  });

  it("renders reachability", () => {
    render(<Viability data={mockViability} />);
    expect(screen.getByText("moderate")).toBeInTheDocument();
  });

  it("renders market gap", () => {
    render(<Viability data={mockViability} />);
    expect(
      screen.getByText("No AI-first scheduler exists for engineering teams")
    ).toBeInTheDocument();
  });

  it("renders signals with direction icons", () => {
    render(<Viability data={mockViability} />);
    expect(screen.getByText("Growing demand for AI tools")).toBeInTheDocument();
    expect(screen.getByText("Enterprise budgets tightening")).toBeInTheDocument();
    // positive direction icon
    expect(screen.getByText("+")).toBeInTheDocument();
    // negative direction icon
    expect(screen.getByText("-")).toBeInTheDocument();
  });

  it("renders signal confidence as percentage", () => {
    render(<Viability data={mockViability} />);
    expect(screen.getByText(/85%/)).toBeInTheDocument();
    expect(screen.getByText(/60%/)).toBeInTheDocument();
  });

  it("renders risk factors", () => {
    render(<Viability data={mockViability} />);
    expect(screen.getByText("Competitive market")).toBeInTheDocument();
    expect(screen.getByText("Enterprise sales cycle")).toBeInTheDocument();
  });

  it("hides signals section when empty", () => {
    const noSignals = { ...mockViability, signals: [] };
    render(<Viability data={noSignals} />);
    expect(screen.queryByText("signals")).not.toBeInTheDocument();
  });

  it("hides risk factors section when empty", () => {
    const noRisks = { ...mockViability, risk_factors: [] };
    render(<Viability data={noRisks} />);
    expect(screen.queryByText("risk factors")).not.toBeInTheDocument();
  });
});
