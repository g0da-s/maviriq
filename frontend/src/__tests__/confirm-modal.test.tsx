import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { ConfirmModal } from "@/components/confirm-modal";

describe("ConfirmModal", () => {
  const defaultProps = {
    open: true,
    title: "Delete this item?",
    onConfirm: vi.fn(),
    onCancel: vi.fn(),
  };

  it("renders nothing when closed", () => {
    const { container } = render(<ConfirmModal {...defaultProps} open={false} />);
    expect(container.innerHTML).toBe("");
  });

  it("renders the title when open", () => {
    render(<ConfirmModal {...defaultProps} />);
    expect(screen.getByText("Delete this item?")).toBeInTheDocument();
  });

  it("renders the description when provided", () => {
    render(<ConfirmModal {...defaultProps} description="This cannot be undone." />);
    expect(screen.getByText("This cannot be undone.")).toBeInTheDocument();
  });

  it("uses default confirm label 'delete'", () => {
    render(<ConfirmModal {...defaultProps} />);
    expect(screen.getByText("delete")).toBeInTheDocument();
  });

  it("uses custom confirm label", () => {
    render(<ConfirmModal {...defaultProps} confirmLabel="remove" />);
    expect(screen.getByText("remove")).toBeInTheDocument();
  });

  it("calls onConfirm when confirm button clicked", async () => {
    const onConfirm = vi.fn();
    const user = userEvent.setup();
    render(<ConfirmModal {...defaultProps} onConfirm={onConfirm} />);

    await user.click(screen.getByText("delete"));
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it("calls onCancel when cancel button clicked", async () => {
    const onCancel = vi.fn();
    const user = userEvent.setup();
    render(<ConfirmModal {...defaultProps} onCancel={onCancel} />);

    await user.click(screen.getByText("cancel"));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("calls onCancel when Escape key is pressed", async () => {
    const onCancel = vi.fn();
    const user = userEvent.setup();
    render(<ConfirmModal {...defaultProps} onCancel={onCancel} />);

    await user.keyboard("{Escape}");
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("calls onCancel when backdrop is clicked", async () => {
    const onCancel = vi.fn();
    const user = userEvent.setup();
    const { container } = render(<ConfirmModal {...defaultProps} onCancel={onCancel} />);

    // The backdrop is the first child div with absolute inset-0
    const backdrop = container.querySelector(".absolute.inset-0");
    expect(backdrop).toBeTruthy();
    await user.click(backdrop!);
    expect(onCancel).toHaveBeenCalledOnce();
  });
});
