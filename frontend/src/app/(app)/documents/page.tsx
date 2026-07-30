import type { Metadata } from "next";

import { DocumentUploader } from "@/features/documents/components/document-uploader";
import { DocumentsTable } from "@/features/documents/components/documents-table";

export const metadata: Metadata = { title: "Documents — Research Assistant Console" };

export default function DocumentsPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Documents</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Upload source material for the pipeline to parse, chunk, and embed.
        </p>
      </div>
      <DocumentUploader />
      <DocumentsTable />
    </div>
  );
}
