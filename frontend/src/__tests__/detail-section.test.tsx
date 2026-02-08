import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect } from "vitest";
import { DetailSection } from "@/components/detail-section";

describe("DetailSection", () => {
  it("renders the title", () => {
    render(<DetailSection title="Test Section">Content here</DetailSection>);
    expect(screen.getByText("Test Section")).toBeInTheDocument();
  });

  it("hides children by default", () => {
    render(<DetailSection title="Test Section">Hidden content</DetailSection>);
    expect(screen.queryByText("Hidden content")).not.toBeInTheDocument();
  });

  it("shows children when clicked", async () => {
    const user = userEvent.setup();
    render(<DetailSection title="Test Section">Revealed content</DetailSection>);

    await user.click(screen.getByRole("button"));
    expect(screen.getByText("Revealed content")).toBeInTheDocument();
  });

  it("hides children when clicked again", async () => {
    const user = userEvent.setup();
    render(<DetailSection title="Test Section">Toggle content</DetailSection>);

    const button = screen.getByRole("button");
    await user.click(button);
    expect(screen.getByText("Toggle content")).toBeInTheDocument();

    await user.click(button);
    expect(screen.queryByText("Toggle content")).not.toBeInTheDocument();
  });

  it("sets aria-expanded correctly", async () => {
    const user = userEvent.setup();
    render(<DetailSection title="Test Section">Content</DetailSection>);

    const button = screen.getByRole("button");
    expect(button).toHaveAttribute("aria-expanded", "false");

    await user.click(button);
    expect(button).toHaveAttribute("aria-expanded", "true");
  });
});
