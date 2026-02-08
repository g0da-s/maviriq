import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { Nav } from "@/components/nav";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  usePathname: vi.fn(() => "/"),
}));

// Mock next/link
vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: { children: React.ReactNode; href: string } & Record<string, unknown>) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

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

import { usePathname } from "next/navigation";

describe("Nav", () => {
  it("renders the brand link", () => {
    render(<Nav />);
    expect(screen.getByText("maverick")).toBeInTheDocument();
  });

  it("renders history link", () => {
    render(<Nav />);
    expect(screen.getByText("history")).toBeInTheDocument();
  });

  it("renders new link", () => {
    render(<Nav />);
    expect(screen.getByText("new")).toBeInTheDocument();
  });

  it("brand link points to home", () => {
    render(<Nav />);
    const brand = screen.getByText("maverick");
    expect(brand.closest("a")).toHaveAttribute("href", "/");
  });

  it("history link points to /validations", () => {
    render(<Nav />);
    const history = screen.getByText("history");
    expect(history.closest("a")).toHaveAttribute("href", "/validations");
  });

  it("highlights history link when on /validations path", () => {
    vi.mocked(usePathname).mockReturnValue("/validations");
    render(<Nav />);
    const historyLink = screen.getByText("history");
    expect(historyLink.className).toContain("text-foreground");
  });

  it("dims history link when on home path", () => {
    vi.mocked(usePathname).mockReturnValue("/");
    render(<Nav />);
    const historyLink = screen.getByText("history");
    expect(historyLink.className).toContain("text-muted");
  });
});
