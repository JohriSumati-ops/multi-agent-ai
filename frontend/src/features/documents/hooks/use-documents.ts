"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { documentsApi } from "@/lib/api/documents-api";
import { queryKeys } from "@/lib/api/query-keys";
import { ApiError } from "@/types/api";
import { isNotifyEnabled } from "@/lib/preferences";
import { logActivity } from "@/features/analytics/activity-log";

export function useDocuments() {
  return useQuery({
    queryKey: queryKeys.documents.list(),
    queryFn: documentsApi.list,
  });
}

export function useDocument(id: string | null) {
  return useQuery({
    queryKey: queryKeys.documents.detail(id ?? ""),
    queryFn: () => documentsApi.get(id as string),
    enabled: !!id,
  });
}

export function useDocumentChunks(id: string | null) {
  return useQuery({
    queryKey: queryKeys.documents.chunks(id ?? ""),
    queryFn: () => documentsApi.chunks(id as string),
    enabled: !!id,
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();
  const [progress, setProgress] = React.useState(0);

  const startedAtRef = React.useRef(0);

  const mutation = useMutation({
    mutationFn: (file: File) => {
      startedAtRef.current = performance.now();
      return documentsApi.upload(file, setProgress);
    },
    onSuccess: (doc) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.list() });
      logActivity({
        type: "upload",
        label: doc.title,
        success: true,
        latencyMs: Math.round(performance.now() - startedAtRef.current),
        latencySource: "client",
      });
      if (isNotifyEnabled("documents")) {
        toast.success(`"${doc.title}" uploaded`, {
          description: "Processing will continue in the background — status will update automatically.",
        });
      }
      setProgress(0);
    },
    onError: (err) => {
      const message = err instanceof ApiError ? err.message : "Upload failed. Try again.";
      logActivity({ type: "upload", label: "Upload failed", success: false, latencyMs: null, latencySource: null });
      if (isNotifyEnabled("documents")) {
        toast.error("Upload failed", { description: message });
      }
      setProgress(0);
    },
  });

  return { ...mutation, progress };
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => documentsApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.list() });
      if (isNotifyEnabled("documents")) {
        toast.success("Document deleted");
      }
    },
    onError: (err) => {
      const message = err instanceof ApiError ? err.message : "Couldn't delete this document.";
      if (isNotifyEnabled("documents")) {
        toast.error("Delete failed", { description: message });
      }
    },
  });
}
