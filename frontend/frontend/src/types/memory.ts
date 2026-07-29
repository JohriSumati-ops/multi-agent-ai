export type MemoryType = "short_term" | "long_term" | "conversation" | "document";

export interface MemoryStoreRequest {
  content: string;
  persist_long_term?: boolean;
  importance_score?: number;
  conversation_id?: string | null;
  document_id?: string | null;
}

export interface MemoryRecordOut {
  id: string;
  user_id: string;
  memory_type: MemoryType;
  content: string;
  importance_score: number;
  expires_at: string | null;
  conversation_id: string | null;
  document_id: string | null;
  created_at: string;
}

export interface MemorySearchResultOut {
  rank: number;
  memory_id: string;
  content: string;
  similarity_score: number;
  confidence: number;
  reason: string;
}

export interface MemorySearchResponse {
  query: string;
  result_count: number;
  results: MemorySearchResultOut[];
}

export interface SessionStateResponse {
  session_id: string;
  state: Record<string, unknown>;
}

export interface MemoryStatisticsResponse {
  total_memories: number;
  counts_by_type: Record<string, number>;
  total_accesses: number;
  expired_pending_cleanup: number;
  most_accessed_memory_ids: string[];
  memory_health: string;
}

export interface PruneResponse {
  expired_deleted: number;
  over_cap_pruned: number;
  archived: number;
}

export interface DeleteHistoryResponse {
  deleted_count: number;
  memory_type: string | null;
}

export interface ClearMemoryResponse {
  cleared_count: number;
}
