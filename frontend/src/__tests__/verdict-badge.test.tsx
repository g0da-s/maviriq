import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { VerdictBadge } from "@/components/verdict-badge";

describe("VerdictBadge", () => {
  it("renders BUILD verdict as lowercase", () => {
    render(<VerdictBadge verdict="BUILD" />);
    expect(screen.getByText("build")).toBeInTheDocument();
  });

  it("renders SKIP verdict as lowercase", () => {
    render(<VerdictBadge verdict="SKIP" />);
    expect(screen.getByText("skip")).toBeInTheDocument();
  });

  it("renders MAYBE verdict as lowercase", () => {
    render(<VerdictBadge verdict="MAYBE" />);
    expect(screen.getByText("maybe")).toBeInTheDocument();
  });

  it("applies BUILD color classes", () => {
    const { container } = render(<VerdictBadge verdict="BUILD" />);
    const badge = container.querySelector("span");
    expect(badge?.className).toContain("border-build");
    expect(badge?.className).toContain("text-build");
  });

  it("applies SKIP color classes", () => {
    const { container } = render(<VerdictBadge verdict="SKIP" />);
    const badge = container.querySelector("span");
    expect(badge?.className).toContain("border-skip");
    expect(badge?.className).toContain("text-skip");
  });

  it("applies MAYBE color classes", () => {
    const { container } = render(<VerdictBadge verdict="MAYBE" />);
    const badge = container.querySelector("span");
    expect(badge?.className).toContain("border-maybe");
    expect(badge?.className).toContain("text-maybe");
  });

  it("defaults to md size", () => {
    const { container } = render(<VerdictBadge verdict="BUILD" />);
    const badge = container.querySelector("span");
    expect(badge?.className).toContain("px-4");
    expect(badge?.className).toContain("text-sm");
  });

  it("applies sm size classes", () => {
    const { container } = render(<VerdictBadge verdict="BUILD" size="sm" />);
    const badge = container.querySelector("span");
    expect(badge?.className).toContain("px-3");
    expect(badge?.className).toContain("text-xs");
  });

  it("applies lg size classes", () => {
    const { container } = render(<VerdictBadge verdict="BUILD" size="lg" />);
    const badge = container.querySelector("span");
    expect(badge?.className).toContain("px-6");
    expect(badge?.className).toContain("text-2xl");
  });
});
