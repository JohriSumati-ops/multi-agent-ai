"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { memoryApi } from "@/lib/api/memory-api";
import { queryKeys } from "@/lib/api/query-keys";
import { ApiError } from "@/types/api";
import type { MemoryType } from "@/types/memory";
import { isNotifyEnabled } from "@/lib/preferences";
import { logActivity } from "@/features/analytics/activity-log";

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
    mutationFn: async ({ query, topK }: { query: string; topK?: number }) => {
      const startedAt = performance.now();
      try {
        const result = await memoryApi.search(query, topK);
        logActivity({
          type: "memory",
          label: `Search: "${query}"`,
          success: true,
          latencyMs: Math.round(performance.now() - startedAt),
          latencySource: "client",
        });
        return result;
      } catch (err) {
        logActivity({ type: "memory", label: "Search failed", success: false, latencyMs: null, latencySource: null });
        throw err;
      }
    },
  });
}

export function useStoreMemory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: memoryApi.store,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.memory.all });
      if (isNotifyEnabled("memory")) toast.success("Memory stored");
    },
    onError: (err) => {
      if (isNotifyEnabled("memory")) {
        toast.error("Couldn't store memory", {
          description: err instanceof ApiError ? err.message : "Try again in a moment.",
        });
      }
    },
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
      if (isNotifyEnabled("memory")) {
        toast.success(`Deleted ${result.deleted_count} ${result.deleted_count === 1 ? "entry" : "entries"}`);
      }
    },
    onError: (err) => {
      if (isNotifyEnabled("memory")) {
        toast.error("Delete failed", { description: err instanceof ApiError ? err.message : "Try again." });
      }
    },
  });
}

export function usePruneMemory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (keepTopN?: number) => memoryApi.prune(keepTopN),
    onSuccess: (result) => {
      invalidateAllMemory(queryClient);
      if (isNotifyEnabled("memory")) {
        toast.success(
          `Pruned: ${result.expired_deleted} expired, ${result.over_cap_pruned} over cap, ${result.archived} archived`
        );
      }
    },
    onError: (err) => {
      if (isNotifyEnabled("memory")) {
        toast.error("Prune failed", { description: err instanceof ApiError ? err.message : "Try again." });
      }
    },
  });
}

export function useClearMemory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: memoryApi.clear,
    onSuccess: (result) => {
      invalidateAllMemory(queryClient);
      if (isNotifyEnabled("memory")) {
        toast.success(`Cleared ${result.cleared_count} memories`);
      }
    },
    onError: (err) => {
      if (isNotifyEnabled("memory")) {
        toast.error("Clear failed", { description: err instanceof ApiError ? err.message : "Try again." });
      }
    },
  });
}
