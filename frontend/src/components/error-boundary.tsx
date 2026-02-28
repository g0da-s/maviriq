"use client";

import React from "react";
import Link from "next/link";
import * as Sentry from "@sentry/nextjs";
import { useTranslations } from "next-intl";

interface Props {
  children: React.ReactNode;
}

interface InnerProps {
  children: React.ReactNode;
  somethingWentWrong: string;
  unexpectedError: string;
  tryAgain: string;
  goHome: string;
}

interface State {
  hasError: boolean;
}

class ErrorBoundaryInner extends React.Component<InnerProps, State> {
  constructor(props: InnerProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    Sentry.captureException(error, { extra: { componentStack: errorInfo.componentStack } });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-4 pt-20">
          <p className="font-display text-lg font-bold">{this.props.somethingWentWrong}</p>
          <p className="text-sm text-muted">{this.props.unexpectedError}</p>
          <div className="flex gap-3 mt-2">
            <button
              onClick={() => this.setState({ hasError: false })}
              className="rounded-lg border border-card-border px-4 py-2 text-sm text-muted transition-colors hover:bg-white/5"
            >
              {this.props.tryAgain}
            </button>
            <Link
              href="/"
              className="rounded-lg border border-card-border px-4 py-2 text-sm text-muted transition-colors hover:bg-white/5"
            >
              {this.props.goHome}
            </Link>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export function ErrorBoundary({ children }: Props) {
  const t = useTranslations("common");
  return (
    <ErrorBoundaryInner
      somethingWentWrong={t("somethingWentWrong")}
      unexpectedError={t("unexpectedError")}
      tryAgain={t("tryAgain")}
      goHome={t("goHome")}
    >
      {children}
    </ErrorBoundaryInner>
  );
}
