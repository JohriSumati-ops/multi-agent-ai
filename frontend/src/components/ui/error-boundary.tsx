"use client";

import * as React from "react";
import { AlertTriangle, RotateCw } from "lucide-react";

import { Button } from "@/components/ui/button";

interface ErrorBoundaryProps {
  children: React.ReactNode;
  /** Shown as the section title in the fallback, e.g. "Memory statistics". */
  label?: string;
  /** Optional custom fallback; receives the reset handler. */
  fallback?: (reset: () => void) => React.ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

/**
 * Class component is required here — React error boundaries have no
 * hook equivalent. Scope these around independent dashboard widgets /
 * feature panels (not the whole app) so one failing chart or panel
 * degrades gracefully instead of blanking the page.
 */
export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // Intentional dev-visible error surface; no error-tracking service is wired up in this project.
    console.error(`[ErrorBoundary${this.props.label ? `: ${this.props.label}` : ""}]`, error, info);
  }

  reset = () => this.setState({ error: null });

  render() {
    if (this.state.error) {
      if (this.props.fallback) return this.props.fallback(this.reset);
      return (
        <div
          role="alert"
          className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-destructive/40 bg-destructive/5 px-4 py-8 text-center"
        >
          <AlertTriangle className="h-5 w-5 text-destructive" />
          <p className="text-sm font-medium text-foreground">
            {this.props.label ? `${this.props.label} couldn't be displayed.` : "Something went wrong."}
          </p>
          <p className="max-w-sm text-xs text-muted-foreground">{this.state.error.message}</p>
          <Button variant="outline" size="sm" onClick={this.reset}>
            <RotateCw className="h-3.5 w-3.5" /> Try again
          </Button>
        </div>
      );
    }
    return this.props.children;
  }
}