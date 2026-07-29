export const queryKeys = {
  documents: {
    all: ["documents"] as const,
    list: () => [...queryKeys.documents.all, "list"] as const,
    detail: (id: string) => [...queryKeys.documents.all, "detail", id] as const,
    chunks: (id: string) => [...queryKeys.documents.all, "chunks", id] as const,
  },
  retrieval: {
    all: ["retrieval"] as const,
    search: (query: string, documentId?: string | null) =>
      [...queryKeys.retrieval.all, "search", query, documentId ?? null] as const,
    documentStatus: (id: string) => [...queryKeys.retrieval.all, "status", id] as const,
  },
  memory: {
    all: ["memory"] as const,
    recent: (limit: number) => [...queryKeys.memory.all, "recent", limit] as const,
    history: (type?: string) => [...queryKeys.memory.all, "history", type ?? "all"] as const,
    statistics: () => [...queryKeys.memory.all, "statistics"] as const,
    search: (query: string) => [...queryKeys.memory.all, "search", query] as const,
    session: (sessionId: string) => [...queryKeys.memory.all, "session", sessionId] as const,
  },
  orchestration: {
    all: ["orchestration"] as const,
    capabilities: () => [...queryKeys.orchestration.all, "capabilities"] as const,
    health: () => [...queryKeys.orchestration.all, "health"] as const,
  },
  research: {
    all: ["research"] as const,
    explain: (responseId: string) => [...queryKeys.research.all, "explain", responseId] as const,
  },
  system: {
    health: () => ["system", "health"] as const,
    version: () => ["system", "version"] as const,
  },
};
