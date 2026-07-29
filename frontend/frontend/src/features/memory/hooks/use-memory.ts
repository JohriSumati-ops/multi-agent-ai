"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { memoryApi } from "@/lib/api/memory-api";
import { queryKeys } from "@/lib/api/query-keys";
import { ApiError } from "@/types/api";
import type { MemoryType } from "@/types/memory";

export function useMemoryStatistics() {
  return useQuery({
    queryKey: queryKeys.memory.statistics(),
    queryFn: memoryApi.statistics,
  });
}

export function useRecentMemory(limit = 20) {
  return useQuery({
    queryKey: queryKeys.memory.recent(limit),
    queryFn: () => memoryApi.recent(limit),
  });
}

export function useMemoryHistory(memoryType?: MemoryType) {
  return useQuery({
    queryKey: queryKeys.memory.history(memoryType),
    queryFn: () => memoryApi.history({ memory_type: memoryType, limit: 100 }),
  });
}

export function useMemorySearch() {
  return useMutation({
    mutationFn: ({ query, topK }: { query: string; topK?: number }) => memoryApi.search(query, topK),
  });
}

export function useStoreMemory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: memoryApi.store,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.memory.all });
      toast.success("Memory stored");
    },
    onError: (err) =>
      toast.error("Couldn't store memory", {
        description: err instanceof ApiError ? err.message : "Try again in a moment.",
      }),
  });
}

function invalidateAllMemory(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: queryKeys.memory.all });
}

export function useDeleteMemoryHistory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (memoryType?: MemoryType) => memoryApi.deleteHistory(memoryType),
    onSuccess: (result) => {
      invalidateAllMemory(queryClient);
      toast.success(`Deleted ${result.deleted_count} ${result.deleted_count === 1 ? "entry" : "entries"}`);
    },
    onError: (err) =>
      toast.error("Delete failed", { description: err instanceof ApiError ? err.message : "Try again." }),
  });
}

export function usePruneMemory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (keepTopN?: number) => memoryApi.prune(keepTopN),
    onSuccess: (result) => {
      invalidateAllMemory(queryClient);
      toast.success(
        `Pruned: ${result.expired_deleted} expired, ${result.over_cap_pruned} over cap, ${result.archived} archived`
      );
    },
    onError: (err) =>
      toast.error("Prune failed", { description: err instanceof ApiError ? err.message : "Try again." }),
  });
}

export function useClearMemory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: memoryApi.clear,
    onSuccess: (result) => {
      invalidateAllMemory(queryClient);
      toast.success(`Cleared ${result.cleared_count} memories`);
    },
    onError: (err) =>
      toast.error("Clear failed", { description: err instanceof ApiError ? err.message : "Try again." }),
  });
}
