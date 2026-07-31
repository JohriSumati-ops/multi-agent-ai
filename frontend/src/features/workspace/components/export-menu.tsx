"use client";

import Link from "next/link";
import { Download, FileText, FileJson, FileType, Printer } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { exportSession, downloadTextFile } from "@/features/workspace/export";
import type { WorkspaceSession } from "@/features/workspace/session-store";

export function ExportMenu({ session }: { session: WorkspaceSession }) {
  const disabled = session.turns.length === 0;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" disabled={disabled}>
          <Download /> Export session
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>Export &ldquo;{session.title}&rdquo;</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={() => {
            const { content, filename, mime } = exportSession(session, "markdown");
            downloadTextFile(content, filename, mime);
          }}
        >
          <FileText /> Markdown (conversation, sources, citations)
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => {
            const { content, filename, mime } = exportSession(session, "text");
            downloadTextFile(content, filename, mime);
          }}
        >
          <FileType /> Plain text
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => {
            const { content, filename, mime } = exportSession(session, "json");
            downloadTextFile(content, filename, mime);
          }}
        >
          <FileJson /> JSON (full metadata)
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link href={`/research/print/${session.id}`} target="_blank" rel="noopener noreferrer">
            <Printer /> PDF (via print dialog)
          </Link>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
