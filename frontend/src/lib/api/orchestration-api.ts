import { apiClient, unwrap } from "@/lib/api/client";
import type { APIResponse } from "@/types/api";
import type { ExecuteGoalRequest, ExecuteGoalResponse, CapabilityOut, HealthCheckOut } from "@/types/orchestration";

export const orchestrationApi = {
  execute: (payload: ExecuteGoalRequest) =>
    apiClient.post<APIResponse<ExecuteGoalResponse>>("/orchestration/execute", payload).then(unwrap),

  capabilities: () =>
    apiClient.get<APIResponse<CapabilityOut[]>>("/orchestration/capabilities").then(unwrap),

  health: () => apiClient.get<APIResponse<HealthCheckOut[]>>("/orchestration/health").then(unwrap),
};
