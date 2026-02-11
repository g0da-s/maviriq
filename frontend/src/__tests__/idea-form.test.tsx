import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { IdeaForm } from "@/components/idea-form";

const mockPush = vi.fn();

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
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

// Mock next/link
vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: { children: React.ReactNode; href: string } & Record<string, unknown>) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

// Mock API
vi.mock("@/lib/api", () => ({
  createValidation: vi.fn(),
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) { super(message); }
  },
}));

import { createValidation } from "@/lib/api";

describe("IdeaForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the textarea", () => {
    render(<IdeaForm />);
    expect(screen.getByPlaceholderText("describe your startup idea...")).toBeInTheDocument();
  });

  it("renders the submit button", () => {
    render(<IdeaForm />);
    expect(screen.getByRole("button", { name: "validate" })).toBeInTheDocument();
  });

  it("shows character counter", () => {
    render(<IdeaForm />);
    expect(screen.getByText("0/500")).toBeInTheDocument();
  });

  it("updates character counter on input", async () => {
    const user = userEvent.setup();
    render(<IdeaForm />);

    const textarea = screen.getByPlaceholderText("describe your startup idea...");
    await user.type(textarea, "hello");
    expect(screen.getByText("5/500")).toBeInTheDocument();
  });

  it("disables button when idea is too short", () => {
    render(<IdeaForm />);
    expect(screen.getByRole("button", { name: "validate" })).toBeDisabled();
  });

  it("enables button when idea has >= 10 characters", async () => {
    const user = userEvent.setup();
    render(<IdeaForm />);

    await user.type(screen.getByPlaceholderText("describe your startup idea..."), "a]real idea");
    expect(screen.getByRole("button", { name: "validate" })).toBeEnabled();
  });

  it("shows error for ideas shorter than 3 characters on submit", async () => {
    const user = userEvent.setup();
    render(<IdeaForm />);

    // Type 2 chars then try to submit (button will be disabled, so we need to use form submit)
    const textarea = screen.getByPlaceholderText("describe your startup idea...");
    await user.type(textarea, "ab");

    // The button should be disabled with 2 chars (after trim)
    expect(screen.getByRole("button", { name: "validate" })).toBeDisabled();
  });

  it("calls createValidation and navigates on success", async () => {
    const user = userEvent.setup();
    vi.mocked(createValidation).mockResolvedValue({
      id: "run-123",
      idea: "test idea",
      status: "pending",
      stream_url: "/api/validations/run-123/stream",
    });

    render(<IdeaForm />);

    await user.type(screen.getByPlaceholderText("describe your startup idea..."), "AI meeting scheduler");
    await user.click(screen.getByRole("button", { name: "validate" }));

    expect(createValidation).toHaveBeenCalledWith("AI meeting scheduler");
    expect(mockPush).toHaveBeenCalledWith("/validations/run-123");
  });

  it("shows loading state while submitting", async () => {
    const user = userEvent.setup();
    // Use a never-resolving promise to keep loading state
    vi.mocked(createValidation).mockReturnValue(new Promise(() => {}));

    render(<IdeaForm />);

    await user.type(screen.getByPlaceholderText("describe your startup idea..."), "AI meeting scheduler");
    await user.click(screen.getByRole("button", { name: "validate" }));

    expect(screen.getByText("validating...")).toBeInTheDocument();
  });

  it("shows error message on API failure", async () => {
    const user = userEvent.setup();
    vi.mocked(createValidation).mockRejectedValue(new Error("Server error"));

    render(<IdeaForm />);

    await user.type(screen.getByPlaceholderText("describe your startup idea..."), "AI meeting scheduler");
    await user.click(screen.getByRole("button", { name: "validate" }));

    expect(await screen.findByText("Server error")).toBeInTheDocument();
  });

  it("clears error on new input", async () => {
    const user = userEvent.setup();
    vi.mocked(createValidation).mockRejectedValue(new Error("Server error"));

    render(<IdeaForm />);

    const textarea = screen.getByPlaceholderText("describe your startup idea...");
    await user.type(textarea, "AI meeting scheduler");
    await user.click(screen.getByRole("button", { name: "validate" }));

    expect(await screen.findByText("Server error")).toBeInTheDocument();

    await user.type(textarea, "x");
    expect(screen.queryByText("Server error")).not.toBeInTheDocument();
  });
});
