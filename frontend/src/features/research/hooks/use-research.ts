"use client";

import { toast } from "sonner";
import { useMutation, useQuery } from "@tanstack/react-query";

import { researchApi } from "@/lib/api/research-api";
import { queryKeys } from "@/lib/api/query-keys";
import { ApiError } from "@/types/api";
import type { ResearchAnswerOut, ResearchQueryRequest } from "@/types/research";
import { isNotifyEnabled } from "@/lib/preferences";
import { logActivity } from "@/features/analytics/activity-log";

export type ResearchMode = "query" | "answer" | "summarize";

const MODE_FN: Record<ResearchMode, (payload: ResearchQueryRequest) => Promise<ResearchAnswerOut>> = {
  query: researchApi.query,
  answer: researchApi.answer,
  summarize: researchApi.summarize,
};

const MODE_LABEL: Record<ResearchMode, string> = {
  query: "Research query",
  answer: "Direct answer",
  summarize: "Summary",
};

function useResearchMutation(mode: ResearchMode) {
  return useMutation({
    mutationFn: (payload: ResearchQueryRequest) => MODE_FN[mode](payload),
    onSuccess: (result) => {
      // The research endpoint reports its own latency_ms — use the real
      // server-measured figure rather than a client-side stopwatch.
      logActivity({
        type: "research",
        label: `${MODE_LABEL[mode]} answered${result.used_llm ? "" : " (retrieval-only, no LLM)"}`,
        success: true,
        latencyMs: result.latency_ms,
        latencySource: "server",
      });
      if (isNotifyEnabled("research")) {
        toast.success(`${MODE_LABEL[mode]} ready`, {
          description: result.is_grounded === false ? "Answer may not be fully grounded in sources." : undefined,
        });
      }
    },
    onError: (err) => {
      logActivity({
        type: "research",
        label: `${MODE_LABEL[mode]} failed`,
        success: false,
        latencyMs: null,
        latencySource: null,
      });
      if (isNotifyEnabled("research")) {
        toast.error(`${MODE_LABEL[mode]} failed`, {
          description: err instanceof ApiError ? err.message : "Try again in a moment.",
        });
      }
    },
  });
}

export function useResearchQuery() {
  return useResearchMutation("query");
}

export function useResearchAnswer() {
  return useResearchMutation("answer");
}

export function useResearchSummarize() {
  return useResearchMutation("summarize");
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
