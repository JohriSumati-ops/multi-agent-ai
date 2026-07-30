import { apiClient, unwrap } from "@/lib/api/client";
import type { APIResponse } from "@/types/api";
import type { DocumentOut, DocumentChunkOut } from "@/types/document";

export const documentsApi = {
  upload: (file: File, onProgress?: (pct: number) => void) => {
    const form = new FormData();
    form.append("file", file);
    return apiClient
      .post<APIResponse<DocumentOut>>("/documents/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (evt) => {
          if (onProgress && evt.total) onProgress(Math.round((evt.loaded / evt.total) * 100));
        },
      })
      .then(unwrap);
  },

  list: () => apiClient.get<APIResponse<DocumentOut[]>>("/documents").then(unwrap),

  get: (id: string) => apiClient.get<APIResponse<DocumentOut>>(`/documents/${id}`).then(unwrap),

  remove: (id: string) =>
    apiClient.delete<APIResponse<{ deleted: boolean; document_id: string }>>(`/documents/${id}`).then(unwrap),

  chunks: (id: string) =>
    apiClient.get<APIResponse<DocumentChunkOut[]>>(`/documents/${id}/chunks`).then(unwrap),
};
