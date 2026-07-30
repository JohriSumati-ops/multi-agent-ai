import { apiClient, unwrap } from "@/lib/api/client";
import type { APIResponse } from "@/types/api";
import type {
  MemoryStoreRequest,
  MemoryRecordOut,
  MemorySearchResponse,
  SessionStateResponse,
  MemoryStatisticsResponse,
  PruneResponse,
  DeleteHistoryResponse,
  ClearMemoryResponse,
  MemoryType,
} from "@/types/memory";

export const memoryApi = {
  store: (payload: MemoryStoreRequest) =>
    apiClient.post<APIResponse<MemoryRecordOut>>("/memory/store", payload).then(unwrap),

  session: (sessionId: string) =>
    apiClient
      .get<APIResponse<SessionStateResponse>>("/memory/session", { params: { session_id: sessionId } })
      .then(unwrap),

  history: (params?: { memory_type?: MemoryType; limit?: number }) =>
    apiClient.get<APIResponse<MemoryRecordOut[]>>("/memory/history", { params }).then(unwrap),

  recent: (limit = 10) =>
    apiClient.get<APIResponse<MemoryRecordOut[]>>("/memory/recent", { params: { limit } }).then(unwrap),

  search: (query: string, top_k = 5, similarity_threshold = 0.3) =>
    apiClient
      .get<APIResponse<MemorySearchResponse>>("/memory/search", { params: { query, top_k, similarity_threshold } })
      .then(unwrap),

  statistics: () => apiClient.get<APIResponse<MemoryStatisticsResponse>>("/memory/statistics").then(unwrap),

  endSession: (sessionId: string) =>
    apiClient
      .delete<APIResponse<{ session_id: string; ended: boolean }>>("/memory/session", {
        params: { session_id: sessionId },
      })
      .then(unwrap),

  deleteHistory: (memory_type?: MemoryType) =>
    apiClient
      .delete<APIResponse<DeleteHistoryResponse>>("/memory/history", { params: { memory_type } })
      .then(unwrap),

  prune: (keep_top_n_long_term = 1000) =>
    apiClient
      .delete<APIResponse<PruneResponse>>("/memory/prune", { params: { keep_top_n_long_term } })
      .then(unwrap),

  clear: () => apiClient.post<APIResponse<ClearMemoryResponse>>("/memory/clear").then(unwrap),
};
