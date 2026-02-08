import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ErrorBoundary } from "@/components/error-boundary";

// Mock next/link
vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: { children: React.ReactNode; href: string } & Record<string, unknown>) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

function ThrowingComponent({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) throw new Error("Test error");
  return <p>child content</p>;
}

describe("ErrorBoundary", () => {
  beforeEach(() => {
    // Suppress React error boundary console.error
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  it("renders children when no error", () => {
    render(
      <ErrorBoundary>
        <p>hello world</p>
      </ErrorBoundary>
    );
    expect(screen.getByText("hello world")).toBeInTheDocument();
  });

  it("renders error UI when child throws", () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>
    );
    expect(screen.getByText("something went wrong")).toBeInTheDocument();
    expect(screen.getByText("an unexpected error occurred")).toBeInTheDocument();
  });

  it("shows try again button on error", () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>
    );
    expect(screen.getByText("try again")).toBeInTheDocument();
  });

  it("shows go home link on error", () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>
    );
    const homeLink = screen.getByText("go home");
    expect(homeLink.closest("a")).toHaveAttribute("href", "/");
  });

  it("recovers when try again is clicked and error is resolved", async () => {
    const user = userEvent.setup();

    // We need a component that can toggle between throwing and not
    let shouldThrow = true;
    function Wrapper() {
      if (shouldThrow) throw new Error("Test error");
      return <p>recovered</p>;
    }

    const { rerender } = render(
      <ErrorBoundary>
        <Wrapper />
      </ErrorBoundary>
    );

    expect(screen.getByText("something went wrong")).toBeInTheDocument();

    // Fix the error condition before clicking try again
    shouldThrow = false;

    await user.click(screen.getByText("try again"));

    // After resetting, the ErrorBoundary re-renders children
    rerender(
      <ErrorBoundary>
        <Wrapper />
      </ErrorBoundary>
    );

    expect(screen.getByText("recovered")).toBeInTheDocument();
  });
});
