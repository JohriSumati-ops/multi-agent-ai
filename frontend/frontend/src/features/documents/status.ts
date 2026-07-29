import type { BadgeProps } from "@/components/ui/badge";
import type { DocumentStatus } from "@/types/document";

export const DOCUMENT_STATUS_LABEL: Record<DocumentStatus, string> = {
  uploaded: "Uploaded",
  parsing: "Parsing",
  parsed: "Parsed",
  chunked: "Chunked",
  embedding: "Embedding",
  ready: "Ready",
  failed: "Failed",
};

export const DOCUMENT_STATUS_VARIANT: Record<DocumentStatus, NonNullable<BadgeProps["variant"]>> = {
  uploaded: "muted",
  parsing: "info",
  parsed: "info",
  chunked: "secondary",
  embedding: "warning",
  ready: "success",
  failed: "destructive",
};
