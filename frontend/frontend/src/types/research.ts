export interface ResearchQueryRequest {
  query: string;
  document_id?: string | null;
}

export interface SourceUsedOut {
  chunk_id: string;
  document_title: string;
  relevance: string;
}

export interface CitationOut {
  chunk_id: string;
  citation_text: string;
  document_title: string | null;
  page_number: number | null;
  is_memory: boolean;
}

export interface ResearchAnswerOut {
  used_llm: boolean;
  answer: string | null;
  sources_used: SourceUsedOut[];
  citations: CitationOut[];
  confidence: number | null;
  reasoning_summary: string | null;
  memory_references: string[];
  retrieved_chunk_ids: string[];
  is_grounded: boolean | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  latency_ms: number;
  fallback_reason: string | null;
  response_id: string | null;
}

export interface ConflictOut {
  item_a_id: string;
  item_b_id: string;
  shared_terms: string[];
  note: string;
}

export interface ReasoningResponse {
  evidence_count: number;
  conflicts: ConflictOut[];
  average_relevance: number;
  consensus_note: string;
}

export interface ExplainResponse {
  response_id: string;
  query_text: string;
  answer_text: string;
  confidence: number;
  reasoning_summary: string;
  sources_used: Record<string, unknown>[];
  memory_references: string[];
  retrieved_chunk_ids: string[];
  prompt_tokens: number | null;
  completion_tokens: number | null;
  latency_ms: number | null;
  explainability_payload: Record<string, unknown>;
}
