"use client";

import * as React from "react";
import { UploadCloud, Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";
import { useUploadDocument } from "@/features/documents/hooks/use-documents";

// Mirrors backend/core/config.py: ALLOWED_DOCUMENT_EXTENSIONS, MAX_UPLOAD_SIZE_MB
const ALLOWED_EXTENSIONS = ["pdf", "txt", "md", "docx"];
const MAX_UPLOAD_SIZE_MB = 25;

export function DocumentUploader() {
  const { mutate: upload, isPending, progress } = useUploadDocument();
  const [dragging, setDragging] = React.useState(false);
  const [localError, setLocalError] = React.useState<string | null>(null);
  const inputRef = React.useRef<HTMLInputElement>(null);

  function validateAndUpload(file: File) {
    setLocalError(null);
    const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setLocalError(`Unsupported file type ".${ext}". Allowed: ${ALLOWED_EXTENSIONS.join(", ")}.`);
      return;
    }
    if (file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024) {
      setLocalError(`File is larger than the ${MAX_UPLOAD_SIZE_MB}MB limit.`);
      return;
    }
    upload(file);
  }

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const file = e.dataTransfer.files?.[0];
          if (file) validateAndUpload(file);
        }}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
        }}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed px-6 py-10 text-center transition-colors",
          dragging ? "border-primary bg-primary/5" : "border-input hover:border-accent",
          isPending && "pointer-events-none opacity-70"
        )}
      >
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          accept={ALLOWED_EXTENSIONS.map((e) => `.${e}`).join(",")}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) validateAndUpload(file);
            e.target.value = "";
          }}
        />
        {isPending ? (
          <>
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
            <p className="text-sm text-foreground">Uploading… {progress}%</p>
          </>
        ) : (
          <>
            <UploadCloud className="h-6 w-6 text-muted-foreground" />
            <p className="text-sm text-foreground">
              <span className="font-medium text-primary">Click to upload</span> or drag and drop
            </p>
            <p className="text-xs text-muted-foreground">
              {ALLOWED_EXTENSIONS.join(", ").toUpperCase()} — up to {MAX_UPLOAD_SIZE_MB}MB
            </p>
          </>
        )}
      </div>
      {localError && <p className="mt-2 text-xs text-destructive">{localError}</p>}
    </div>
  );
}
