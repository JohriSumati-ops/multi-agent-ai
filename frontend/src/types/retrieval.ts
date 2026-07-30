export interface SearchRequest {
  query: string;
  top_k?: number;
  similarity_threshold?: number;
  document_id?: string | null;
}

export interface SimilarChunkRequest {
  chunk_id: string;
  top_k?: number;
  similarity_threshold?: number;
}

export interface RankedResultOut {
  rank: number;
  chunk_id: string;
  document_id: string;
  document_title: string;
  chunk_text: string;
  page_number: number | null;
  chunk_index: number;
  similarity_score: number;
  confidence: number;
  reason: string;
}

export interface SearchResponse {
  query: string;
  result_count: number;
  results: RankedResultOut[];
}

export interface DocumentRetrievalStatus {
  document_id: string;
  title: string;
  status: string;
  chunk_count: number;
  embedded_chunk_count: number;
  is_fully_embedded: boolean;
}

export interface ChunkVectorInfo {
  chunk_id: string;
  document_id: string;
  vector_id: number;
  embedding_model: string;
  dimension: number;
}

export interface ReindexResponse {
  document_id: string;
  chunks_embedded: number;
  status: string;
}

export interface RebuildResponse {
  documents_processed: number;
  chunks_embedded: number;
  vectors_in_index: number;
}
