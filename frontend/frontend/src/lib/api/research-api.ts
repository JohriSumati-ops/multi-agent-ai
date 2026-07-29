import { apiClient, unwrap } from "@/lib/api/client";
import type { APIResponse } from "@/types/api";
import type { ResearchQueryRequest, ResearchAnswerOut, ReasoningResponse, ExplainResponse } from "@/types/research";

export const researchApi = {
  query: (payload: ResearchQueryRequest) =>
    apiClient.post<APIResponse<ResearchAnswerOut>>("/research/query", payload).then(unwrap),

  answer: (payload: ResearchQueryRequest) =>
    apiClient.post<APIResponse<ResearchAnswerOut>>("/research/answer", payload).then(unwrap),

  summarize: (payload: ResearchQueryRequest) =>
    apiClient.post<APIResponse<ResearchAnswerOut>>("/research/summarize", payload).then(unwrap),

  reason: (payload: ResearchQueryRequest) =>
    apiClient.post<APIResponse<ReasoningResponse>>("/research/reason", payload).then(unwrap),

  explain: (responseId: string) =>
    apiClient.get<APIResponse<ExplainResponse>>(`/research/explain/${responseId}`).then(unwrap),
};
