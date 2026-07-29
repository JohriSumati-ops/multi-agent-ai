export type DocumentStatus =
  | "uploaded"
  | "parsing"
  | "parsed"
  | "chunked"
  | "embedding"
  | "ready"
  | "failed";

export type DocumentFormat = "pdf" | "txt" | "md" | "docx";

export type DocumentType =
  | "pdf"
  | "lecture_notes"
  | "research_paper"
  | "coding_notes"
  | "other";

export type ChunkingStrategy = "fixed_size" | "paragraph" | "sentence" | "sliding_window";

export interface DocumentOut {
  id: string;
  created_at: string;
  updated_at: string;
  owner_id: string;
  title: string;
  file_name: string;
  file_format: DocumentFormat | null;
  document_type: DocumentType;
  status: DocumentStatus;
  subject: string | null;
  description: string | null;
  processing_error: string | null;
  author: string | null;
  page_count: number | null;
  language: string | null;
  word_count: number | null;
  char_count: number | null;
  reading_time_minutes: number | null;
}

export interface DocumentChunkOut {
  id: string;
  created_at: string;
  updated_at: string;
  document_id: string;
  chunk_index: number;
  chunk_text: string;
  page_number: number | null;
  start_position: number;
  end_position: number;
  token_count: number;
  char_count: number;
  chunking_strategy: ChunkingStrategy;
}
