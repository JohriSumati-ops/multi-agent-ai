"use client";

import { useMutation, useQuery } from "@tanstack/react-query";

import { retrievalApi } from "@/lib/api/retrieval-api";
import { queryKeys } from "@/lib/api/query-keys";
import type { SearchRequest } from "@/types/retrieval";
import { logActivity } from "@/features/analytics/activity-log";

export function useSemanticSearch() {
  return useMutation({
    mutationFn: async (payload: SearchRequest) => {
      const startedAt = performance.now();
      try {
        const result = await retrievalApi.search(payload);
        logActivity({
          type: "search",
          label: `"${payload.query}" — ${result.result_count} results`,
          success: true,
          latencyMs: Math.round(performance.now() - startedAt),
          latencySource: "client",
        });
        return result;
      } catch (err) {
        logActivity({ type: "search", label: "Search failed", success: false, latencyMs: null, latencySource: null });
        throw err;
      }
    },
  });
}

export function useDocumentRetrievalStatus(documentId: string | null) {
  return useQuery({
    queryKey: queryKeys.retrieval.documentStatus(documentId ?? ""),
    queryFn: () => retrievalApi.documentStatus(documentId as string),
    enabled: !!documentId,
  });
}
