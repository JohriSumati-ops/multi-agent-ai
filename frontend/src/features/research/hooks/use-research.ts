"use client";

import { toast } from "sonner";
import { useMutation, useQuery } from "@tanstack/react-query";

import { researchApi } from "@/lib/api/research-api";
import { queryKeys } from "@/lib/api/query-keys";
import { ApiError } from "@/types/api";
import type { ResearchQueryRequest } from "@/types/research";
import { isNotifyEnabled } from "@/lib/preferences";
import { logActivity } from "@/features/analytics/activity-log";

export function useResearchQuery() {
  return useMutation({
    mutationFn: (payload: ResearchQueryRequest) => researchApi.query(payload),
    onSuccess: (result) => {
      // The research endpoint reports its own latency_ms — use the real
      // server-measured figure rather than a client-side stopwatch.
      logActivity({
        type: "research",
        label: `Query answered${result.used_llm ? "" : " (retrieval-only, no LLM)"}`,
        success: true,
        latencyMs: result.latency_ms,
        latencySource: "server",
      });
      if (isNotifyEnabled("research")) {
        toast.success("Research answer ready", {
          description: result.is_grounded === false ? "Answer may not be fully grounded in sources." : undefined,
        });
      }
    },
    onError: (err) => {
      logActivity({ type: "research", label: "Query failed", success: false, latencyMs: null, latencySource: null });
      if (isNotifyEnabled("research")) {
        toast.error("Research query failed", {
          description: err instanceof ApiError ? err.message : "Try again in a moment.",
        });
      }
    },
  });
}

export function useResearchSummarize() {
  return useMutation({
    mutationFn: (payload: ResearchQueryRequest) => researchApi.summarize(payload),
  });
}

export function useResearchReason() {
  return useMutation({
    mutationFn: (payload: ResearchQueryRequest) => researchApi.reason(payload),
  });
}

export function useExplainResponse(responseId: string | null) {
  return useQuery({
    queryKey: queryKeys.research.explain(responseId ?? ""),
    queryFn: () => researchApi.explain(responseId as string),
    enabled: !!responseId,
  });
}
