import { apiClient, unwrap } from "@/lib/api/client";
import type { APIResponse } from "@/types/api";
import type {
  SearchRequest,
  SearchResponse,
  SimilarChunkRequest,
  DocumentRetrievalStatus,
  ChunkVectorInfo,
  ReindexResponse,
  RebuildResponse,
} from "@/types/retrieval";

export const retrievalApi = {
  search: (payload: SearchRequest) =>
    apiClient.post<APIResponse<SearchResponse>>("/retrieval/search", payload).then(unwrap),

  findSimilar: (payload: SimilarChunkRequest) =>
    apiClient.post<APIResponse<SearchResponse>>("/retrieval/similar", payload).then(unwrap),

  documentStatus: (documentId: string) =>
    apiClient
      .get<APIResponse<DocumentRetrievalStatus>>(`/retrieval/document/${documentId}`)
      .then(unwrap),

  chunkVectorInfo: (chunkId: string) =>
    apiClient.get<APIResponse<ChunkVectorInfo>>(`/retrieval/chunks/${chunkId}`).then(unwrap),

  reindexDocument: (documentId: string) =>
    apiClient
      .post<APIResponse<ReindexResponse>>(`/retrieval/reindex?document_id=${documentId}`)
      .then(unwrap),

  rebuildIndex: () => apiClient.post<APIResponse<RebuildResponse>>("/retrieval/rebuild").then(unwrap),
};
