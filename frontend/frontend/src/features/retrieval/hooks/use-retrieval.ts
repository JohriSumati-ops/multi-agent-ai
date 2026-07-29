"use client";

import { useMutation, useQuery } from "@tanstack/react-query";

import { retrievalApi } from "@/lib/api/retrieval-api";
import { queryKeys } from "@/lib/api/query-keys";
import type { SearchRequest } from "@/types/retrieval";

export function useSemanticSearch() {
  return useMutation({
    mutationFn: (payload: SearchRequest) => retrievalApi.search(payload),
  });
}

export function useDocumentRetrievalStatus(documentId: string | null) {
  return useQuery({
    queryKey: queryKeys.retrieval.documentStatus(documentId ?? ""),
    queryFn: () => retrievalApi.documentStatus(documentId as string),
    enabled: !!documentId,
  });
}
