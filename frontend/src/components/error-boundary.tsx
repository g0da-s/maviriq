"use client";

import React from "react";
import Link from "next/link";

interface Props {
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-4 pt-20">
          <p className="font-display text-lg font-bold">something went wrong</p>
          <p className="text-sm text-muted">an unexpected error occurred</p>
          <div className="flex gap-3 mt-2">
            <button
              onClick={() => this.setState({ hasError: false })}
              className="rounded-lg border border-card-border px-4 py-2 text-sm text-muted transition-colors hover:bg-white/5"
            >
              try again
            </button>
            <Link
              href="/"
              className="rounded-lg border border-card-border px-4 py-2 text-sm text-muted transition-colors hover:bg-white/5"
            >
              go home
            </Link>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
