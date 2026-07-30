"use client";

import { toast } from "sonner";
import { useMutation, useQuery } from "@tanstack/react-query";

import { orchestrationApi } from "@/lib/api/orchestration-api";
import { queryKeys } from "@/lib/api/query-keys";
import { ApiError } from "@/types/api";
import type { ExecuteGoalRequest } from "@/types/orchestration";
import { isNotifyEnabled } from "@/lib/preferences";
import { logActivity } from "@/features/analytics/activity-log";

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
    mutationFn: async (payload: ExecuteGoalRequest) => {
      const startedAt = performance.now();
      try {
        const result = await orchestrationApi.execute(payload);
        const { plan } = result;
        logActivity({
          type: "orchestration",
          label: `${payload.goal} (${plan.succeeded}/${plan.task_count} tasks succeeded)`,
          success: plan.failed === 0,
          latencyMs: Math.round(performance.now() - startedAt),
          latencySource: "client",
        });
        if (isNotifyEnabled("orchestration")) {
          if (plan.failed === 0) {
            toast.success(`Goal executed: ${plan.succeeded}/${plan.task_count} tasks succeeded`);
          } else {
            toast.warning(`Goal completed with failures: ${plan.failed} of ${plan.task_count} tasks failed`);
          }
        }
        return result;
      } catch (err) {
        logActivity({
          type: "orchestration",
          label: "Execution failed",
          success: false,
          latencyMs: null,
          latencySource: null,
        });
        if (isNotifyEnabled("orchestration")) {
          toast.error("Execution failed", {
            description: err instanceof ApiError ? err.message : "Try again in a moment.",
          });
        }
        throw err;
      }
    },
  });
}
