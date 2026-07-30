import { describe, it, expect } from "vitest";

import { DOCUMENT_STATUS_LABEL, DOCUMENT_STATUS_VARIANT } from "@/features/documents/status";
import type { DocumentStatus } from "@/types/document";

const ALL_STATUSES: DocumentStatus[] = [
  "uploaded",
  "parsing",
  "parsed",
  "chunked",
  "embedding",
  "ready",
  "failed",
];

describe("document status mappings", () => {
  it.each(ALL_STATUSES)("has a label for status %s", (status) => {
    expect(DOCUMENT_STATUS_LABEL[status]).toBeTruthy();
  });

  it.each(ALL_STATUSES)("has a badge variant for status %s", (status) => {
    expect(DOCUMENT_STATUS_VARIANT[status]).toBeTruthy();
  });

  it("marks 'failed' as a destructive-styled status", () => {
    expect(DOCUMENT_STATUS_VARIANT.failed).toBe("destructive");
  });

  it("marks 'ready' as a success-styled status", () => {
    expect(DOCUMENT_STATUS_VARIANT.ready).toBe("success");
  });
});
