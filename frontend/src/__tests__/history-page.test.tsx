import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import HistoryPage from "@/app/validations/page";
import { mockValidationList } from "./fixtures";

// Mock next/navigation
const mockSearchParams = new URLSearchParams();
vi.mock("next/navigation", () => ({
  useSearchParams: () => mockSearchParams,
}));

// Mock next/link
vi.mock("next/link", () => ({
  default: ({ children, href, className, ...props }: { children: React.ReactNode; href: string; className?: string } & Record<string, unknown>) => (
    <a href={href} className={className} {...props}>{children}</a>
  ),
}));

// Mock API
vi.mock("@/lib/api", () => ({
  listValidations: vi.fn(),
  deleteValidation: vi.fn(),
}));

import { listValidations, deleteValidation } from "@/lib/api";

describe("HistoryPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading skeletons initially", () => {
    vi.mocked(listValidations).mockReturnValue(new Promise(() => {}));
    const { container } = render(<HistoryPage />);
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("renders validation list items", async () => {
    vi.mocked(listValidations).mockResolvedValue(mockValidationList);
    render(<HistoryPage />);

    expect(await screen.findByText("AI meeting scheduler")).toBeInTheDocument();
    expect(screen.getByText("Blockchain pet food tracker")).toBeInTheDocument();
    expect(screen.getByText("Developer tool for code review")).toBeInTheDocument();
  });

  it("renders verdict badges for completed items", async () => {
    vi.mocked(listValidations).mockResolvedValue(mockValidationList);
    render(<HistoryPage />);

    expect(await screen.findByText("build")).toBeInTheDocument();
    expect(screen.getByText("skip")).toBeInTheDocument();
    expect(screen.getByText("maybe")).toBeInTheDocument();
  });

  it("shows confidence percentages", async () => {
    vi.mocked(listValidations).mockResolvedValue(mockValidationList);
    render(<HistoryPage />);

    expect(await screen.findByText(/78% confidence/)).toBeInTheDocument();
    expect(screen.getByText(/92% confidence/)).toBeInTheDocument();
  });

  it("renders empty state when no validations", async () => {
    vi.mocked(listValidations).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      per_page: 20,
    });
    render(<HistoryPage />);

    expect(await screen.findByText("no validations yet")).toBeInTheDocument();
    expect(screen.getByText("validate your first idea")).toBeInTheDocument();
  });

  it("shows error message on API failure", async () => {
    vi.mocked(listValidations).mockRejectedValue(new Error("Network error"));
    render(<HistoryPage />);

    expect(await screen.findByText("Network error")).toBeInTheDocument();
  });

  it("opens confirm modal when delete button clicked", async () => {
    vi.mocked(listValidations).mockResolvedValue(mockValidationList);
    const user = userEvent.setup();

    render(<HistoryPage />);

    await screen.findByText("AI meeting scheduler");

    // Find delete buttons (there should be one per item)
    const deleteButtons = screen.getAllByRole("button");
    await user.click(deleteButtons[0]);

    expect(screen.getByText("delete this validation?")).toBeInTheDocument();
  });

  it("calls deleteValidation and reloads on confirm", async () => {
    vi.mocked(listValidations).mockResolvedValue(mockValidationList);
    vi.mocked(deleteValidation).mockResolvedValue({ status: "deleted" });
    const user = userEvent.setup();

    render(<HistoryPage />);

    await screen.findByText("AI meeting scheduler");

    const deleteButtons = screen.getAllByRole("button");
    await user.click(deleteButtons[0]);

    await user.click(screen.getByText("delete"));

    await waitFor(() => {
      expect(deleteValidation).toHaveBeenCalledWith("run-1");
    });

    // Should reload the list
    expect(listValidations).toHaveBeenCalledTimes(2);
  });

  it("closes confirm modal on cancel", async () => {
    vi.mocked(listValidations).mockResolvedValue(mockValidationList);
    const user = userEvent.setup();

    render(<HistoryPage />);

    await screen.findByText("AI meeting scheduler");

    const deleteButtons = screen.getAllByRole("button");
    await user.click(deleteButtons[0]);

    expect(screen.getByText("delete this validation?")).toBeInTheDocument();

    await user.click(screen.getByText("cancel"));

    expect(screen.queryByText("delete this validation?")).not.toBeInTheDocument();
  });

  it("renders page title", async () => {
    vi.mocked(listValidations).mockResolvedValue(mockValidationList);
    render(<HistoryPage />);

    expect(await screen.findByText("history")).toBeInTheDocument();
  });

  it("renders 'new validation' link", async () => {
    vi.mocked(listValidations).mockResolvedValue(mockValidationList);
    render(<HistoryPage />);

    const link = await screen.findByText("new validation");
    expect(link.closest("a")).toHaveAttribute("href", "/");
  });
});
