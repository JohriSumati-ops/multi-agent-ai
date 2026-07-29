"use client";

import { useMutation, useQuery } from "@tanstack/react-query";

import { orchestrationApi } from "@/lib/api/orchestration-api";
import { queryKeys } from "@/lib/api/query-keys";
import type { ExecuteGoalRequest } from "@/types/orchestration";

export function useCapabilities() {
  return useQuery({
    queryKey: queryKeys.orchestration.capabilities(),
    queryFn: orchestrationApi.capabilities,
  });
}

export function useOrchestrationHealth() {
  return useQuery({
    queryKey: queryKeys.orchestration.health(),
    queryFn: orchestrationApi.health,
    refetchInterval: 30_000,
  });
}

export function useExecuteGoal() {
  return useMutation({
    mutationFn: (payload: ExecuteGoalRequest) => orchestrationApi.execute(payload),
  });
}
