"use client";

import * as React from "react";

export interface NavigationTimingSnapshot {
  /** Time to first byte, ms */
  ttfb: number | null;
  /** DOM content loaded, ms from navigation start */
  domContentLoaded: number | null;
  /** Full page load, ms from navigation start */
  loadComplete: number | null;
  /** First paint, ms, if the browser reports it */
  firstPaint: number | null;
  /** First contentful paint, ms, if the browser reports it */
  firstContentfulPaint: number | null;
}

/**
 * Reads the real `PerformanceNavigationTiming` and paint entries for the
 * current page load. Genuine browser-reported numbers — there is no
 * backend usage/performance endpoint to source this from, and no metric
 * here is synthesized.
 */
export function useNavigationTiming(): NavigationTimingSnapshot | null {
  const [snapshot, setSnapshot] = React.useState<NavigationTimingSnapshot | null>(null);

  React.useEffect(() => {
    if (typeof window === "undefined" || !("performance" in window)) return;

    function capture() {
      const [nav] = performance.getEntriesByType("navigation") as PerformanceNavigationTiming[];
      const paintEntries = performance.getEntriesByType("paint");
      const fp = paintEntries.find((e) => e.name === "first-paint")?.startTime ?? null;
      const fcp = paintEntries.find((e) => e.name === "first-contentful-paint")?.startTime ?? null;

      if (!nav) return;
      setSnapshot({
        ttfb: Math.round(nav.responseStart - nav.requestStart),
        domContentLoaded: Math.round(nav.domContentLoadedEventEnd - nav.startTime),
        loadComplete: nav.loadEventEnd > 0 ? Math.round(nav.loadEventEnd - nav.startTime) : null,
        firstPaint: fp !== null ? Math.round(fp) : null,
        firstContentfulPaint: fcp !== null ? Math.round(fcp) : null,
      });
    }

    if (document.readyState === "complete") {
      capture();
    } else {
      window.addEventListener("load", capture, { once: true });
      return () => window.removeEventListener("load", capture);
    }
  }, []);

  return snapshot;
}