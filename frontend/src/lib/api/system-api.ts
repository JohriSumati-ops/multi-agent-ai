import { apiClient, unwrap } from "@/lib/api/client";
import type { APIResponse, HealthStatus, VersionInfo } from "@/types/api";

export const systemApi = {
  health: () => apiClient.get<APIResponse<HealthStatus>>("/health").then(unwrap),
  version: () => apiClient.get<APIResponse<VersionInfo>>("/version").then(unwrap),
};
