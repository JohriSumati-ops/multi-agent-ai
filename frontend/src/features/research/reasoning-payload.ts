/**
 * Structured shape of `ExplainResponse.explainability_payload`.
 *
 * The backend types this field as a loose `dict` (see
 * `backend/models/research_response.py`), but `ResearchService._persist`
 * always populates it with the same shape — mirrored here from
 * `reasoning/source_grounding.py` (`GroundingReport`) and
 * `reasoning/research_synthesis.py` (`SynthesisResult` / `Conflict`).
 * Parsed defensively rather than trusted blindly, since it crosses a
 * loosely-typed boundary.
 */

export interface GroundingPayload {
  is_grounded: boolean;
  verified_chunk_ids: string[];
  fabricated_chunk_ids: string[];
}

export interface ConflictPayload {
  item_a_id: string;
  item_b_id: string;
  shared_terms: string[];
  note: string;
}

export interface SynthesisPayload {
  evidence_count: number;
  conflicts: ConflictPayload[];
  average_relevance: number;
  consensus_note: string;
}

export interface CitationPayload {
  chunk_id: string;
  citation_text: string;
  document_title: string | null;
  page_number: number | null;
  is_memory: boolean;
}

export interface ExplainabilityPayload {
  citations: CitationPayload[];
  grounding: GroundingPayload | null;
  synthesis: SynthesisPayload | null;
  excluded_count: number;
  excluded_reasons: Record<string, string>;
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null;
}

/** Best-effort parse — returns null fields rather than throwing if the shape doesn't match what's expected. */
export function parseExplainabilityPayload(raw: Record<string, unknown>): ExplainabilityPayload {
  const grounding = isRecord(raw.grounding)
    ? {
        is_grounded: Boolean(raw.grounding.is_grounded),
        verified_chunk_ids: Array.isArray(raw.grounding.verified_chunk_ids) ? (raw.grounding.verified_chunk_ids as string[]) : [],
        fabricated_chunk_ids: Array.isArray(raw.grounding.fabricated_chunk_ids)
          ? (raw.grounding.fabricated_chunk_ids as string[])
          : [],
      }
    : null;

  const synthesis = isRecord(raw.synthesis)
    ? {
        evidence_count: Number(raw.synthesis.evidence_count ?? 0),
        conflicts: Array.isArray(raw.synthesis.conflicts) ? (raw.synthesis.conflicts as ConflictPayload[]) : [],
        average_relevance: Number(raw.synthesis.average_relevance ?? 0),
        consensus_note: String(raw.synthesis.consensus_note ?? ""),
      }
    : null;

  return {
    citations: Array.isArray(raw.citations) ? (raw.citations as CitationPayload[]) : [],
    grounding,
    synthesis,
    excluded_count: Number(raw.excluded_count ?? 0),
    excluded_reasons: isRecord(raw.excluded_reasons) ? (raw.excluded_reasons as Record<string, string>) : {},
  };
}
