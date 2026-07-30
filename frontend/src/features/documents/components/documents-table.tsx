"use client";

import * as React from "react";
import { FileText, Trash2, Eye, Search } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import { useDocuments, useDeleteDocument, useDocumentChunks } from "@/features/documents/hooks/use-documents";
import { DOCUMENT_STATUS_LABEL, DOCUMENT_STATUS_VARIANT } from "@/features/documents/status";
import type { DocumentOut } from "@/types/document";

export function DocumentsTable() {
  const { data: documents, isLoading } = useDocuments();
  const [query, setQuery] = React.useState("");
  const [previewDoc, setPreviewDoc] = React.useState<DocumentOut | null>(null);
  const [deleteDoc, setDeleteDoc] = React.useState<DocumentOut | null>(null);

  const filtered = React.useMemo(() => {
    if (!documents) return [];
    const q = query.trim().toLowerCase();
    if (!q) return documents;
    return documents.filter(
      (d) => d.title.toLowerCase().includes(q) || d.file_name.toLowerCase().includes(q)
    );
  }, [documents, query]);

  return (
    <div className="space-y-3">
      <div className="relative max-w-xs">
        <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Filter documents…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="pl-8"
        />
      </div>

      <div className="rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Title</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Words</TableHead>
              <TableHead>Reading time</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading &&
              Array.from({ length: 4 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={6}>
                    <Skeleton className="h-5 w-full" />
                  </TableCell>
                </TableRow>
              ))}

            {!isLoading && filtered.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center text-sm text-muted-foreground">
                  {documents?.length === 0
                    ? "No documents yet. Upload one to get started."
                    : "No documents match that filter."}
                </TableCell>
              </TableRow>
            )}

            {!isLoading &&
              filtered.map((doc) => (
                <TableRow key={doc.id}>
                  <TableCell className="max-w-64">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                      <div className="min-w-0">
                        <p className="truncate font-medium text-foreground">{doc.title}</p>
                        <p className="truncate font-mono text-[11px] text-muted-foreground">{doc.file_name}</p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{doc.document_type.replace("_", " ")}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={DOCUMENT_STATUS_VARIANT[doc.status]}>
                      {DOCUMENT_STATUS_LABEL[doc.status]}
                    </Badge>
                    {doc.status === "failed" && doc.processing_error && (
                      <p className="mt-1 max-w-48 truncate text-[11px] text-destructive">
                        {doc.processing_error}
                      </p>
                    )}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {doc.word_count?.toLocaleString() ?? "—"}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {doc.reading_time_minutes ? `${Math.round(doc.reading_time_minutes)} min` : "—"}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="icon" onClick={() => setPreviewDoc(doc)} aria-label="Preview chunks">
                      <Eye className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setDeleteDoc(doc)}
                      aria-label="Delete document"
                      className="text-destructive hover:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </div>

      <ChunkPreviewDialog document={previewDoc} onOpenChange={(open) => !open && setPreviewDoc(null)} />
      <DeleteConfirmDialog document={deleteDoc} onOpenChange={(open) => !open && setDeleteDoc(null)} />
    </div>
  );
}

function ChunkPreviewDialog({
  document,
  onOpenChange,
}: {
  document: DocumentOut | null;
  onOpenChange: (open: boolean) => void;
}) {
  const { data: chunks, isLoading } = useDocumentChunks(document?.id ?? null);

  return (
    <Dialog open={!!document} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{document?.title}</DialogTitle>
          <DialogDescription>
            {chunks ? `${chunks.length} chunks` : "Loading chunks…"} · {document?.file_name}
          </DialogDescription>
        </DialogHeader>
        <div className="max-h-96 space-y-3 overflow-y-auto">
          {isLoading && <Skeleton className="h-20 w-full" />}
          {chunks?.map((chunk) => (
            <div key={chunk.id} className="rounded-md border border-border bg-muted/40 p-3">
              <div className="mb-1.5 flex items-center gap-2 font-mono text-[11px] text-muted-foreground">
                <span>chunk #{chunk.chunk_index}</span>
                {chunk.page_number !== null && <span>· page {chunk.page_number}</span>}
                <span>· {chunk.token_count} tokens</span>
              </div>
              <p className="line-clamp-4 text-sm text-foreground">{chunk.chunk_text}</p>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function DeleteConfirmDialog({
  document,
  onOpenChange,
}: {
  document: DocumentOut | null;
  onOpenChange: (open: boolean) => void;
}) {
  const { mutate: remove, isPending } = useDeleteDocument();

  return (
    <Dialog open={!!document} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Delete this document?</DialogTitle>
          <DialogDescription>
            &ldquo;{document?.title}&rdquo; and all of its chunks and embeddings will be permanently removed.
            This can&apos;t be undone.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline">Cancel</Button>
          </DialogClose>
          <Button
            variant="destructive"
            disabled={isPending}
            onClick={() => {
              if (!document) return;
              remove(document.id, { onSuccess: () => onOpenChange(false) });
            }}
          >
            Delete
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
