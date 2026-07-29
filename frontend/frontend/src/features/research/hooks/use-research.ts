"use client";

import { useMutation, useQuery } from "@tanstack/react-query";

import { researchApi } from "@/lib/api/research-api";
import { queryKeys } from "@/lib/api/query-keys";
import type { ResearchQueryRequest } from "@/types/research";

export function useResearchQuery() {
  return useMutation({
    mutationFn: (payload: ResearchQueryRequest) => researchApi.query(payload),
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
