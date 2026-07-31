"use client";

import * as React from "react";
import { toast } from "sonner";
import {
  Plus,
  Pin,
  PinOff,
  Pencil,
  Copy,
  Trash2,
  Download,
  Upload,
  Check,
  X,
  MessageSquare,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import { useWorkspaceSessions } from "@/features/workspace/hooks/use-workspace-sessions";
import { exportSession, downloadTextFile } from "@/features/workspace/export";
import { importSessionJson } from "@/features/workspace/session-store";
import type { WorkspaceSession } from "@/features/workspace/session-store";

export function SessionSidebar({ onSelect }: { onSelect?: () => void }) {
  const { sessions, activeId, newSession, selectSession, rename, togglePin, remove, duplicate } =
    useWorkspaceSessions();
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [draftTitle, setDraftTitle] = React.useState("");
  const [pendingDelete, setPendingDelete] = React.useState<WorkspaceSession | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const sorted = React.useMemo(
    () => [...sessions].sort((a, b) => Number(b.pinned) - Number(a.pinned) || b.updatedAt.localeCompare(a.updatedAt)),
    [sessions]
  );

  function startEdit(session: WorkspaceSession) {
    setEditingId(session.id);
    setDraftTitle(session.title);
  }

  function commitEdit(id: string) {
    rename(id, draftTitle);
    setEditingId(null);
  }

  function onImportFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    file
      .text()
      .then((text) => {
        importSessionJson(text);
        toast.success("Session imported");
      })
      .catch(() => toast.error("Couldn't import that file", { description: "Expected an exported session JSON file." }));
    e.target.value = "";
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-1.5 p-2.5">
        <Button size="sm" className="flex-1 justify-start gap-1.5" onClick={() => newSession()}>
          <Plus className="h-3.5 w-3.5" /> New session
        </Button>
        <Button variant="outline" size="icon" className="h-8 w-8 shrink-0" onClick={() => fileInputRef.current?.click()} aria-label="Import session">
          <Upload className="h-3.5 w-3.5" />
        </Button>
        <input ref={fileInputRef} type="file" accept="application/json" className="hidden" onChange={onImportFile} />
      </div>

      <div className="flex-1 space-y-0.5 overflow-y-auto px-2 pb-2">
        {sorted.length === 0 && (
          <p className="px-2 py-6 text-center text-xs text-muted-foreground">No saved sessions yet.</p>
        )}
        {sorted.map((session) => (
          <div
            key={session.id}
            className={cn(
              "group flex items-center gap-1.5 rounded-md px-2 py-1.5 text-sm",
              session.id === activeId ? "bg-muted text-foreground" : "text-muted-foreground hover:bg-muted/60"
            )}
          >
            {editingId === session.id ? (
              <>
                <Input
                  autoFocus
                  value={draftTitle}
                  onChange={(e) => setDraftTitle(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") commitEdit(session.id);
                    if (e.key === "Escape") setEditingId(null);
                  }}
                  className="h-6 flex-1 px-1.5 text-xs"
                />
                <button type="button" onClick={() => commitEdit(session.id)} aria-label="Save name" className="shrink-0">
                  <Check className="h-3.5 w-3.5 text-success" />
                </button>
                <button type="button" onClick={() => setEditingId(null)} aria-label="Cancel rename" className="shrink-0">
                  <X className="h-3.5 w-3.5" />
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => {
                    selectSession(session.id);
                    onSelect?.();
                  }}
                  className="flex min-w-0 flex-1 items-center gap-1.5 text-left"
                >
                  <MessageSquare className="h-3.5 w-3.5 shrink-0" />
                  <span className="truncate">{session.title}</span>
                  {session.pinned && <Pin className="h-3 w-3 shrink-0 fill-current text-primary" />}
                </button>
                <span className="shrink-0 text-[10px] tabular-nums opacity-0 group-hover:opacity-100">
                  {session.turns.length}
                </span>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button
                      type="button"
                      className="shrink-0 rounded p-0.5 opacity-0 hover:bg-muted group-hover:opacity-100"
                      aria-label={`Options for ${session.title}`}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="12" cy="5" r="1" />
                        <circle cx="12" cy="12" r="1" />
                        <circle cx="12" cy="19" r="1" />
                      </svg>
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => togglePin(session.id)}>
                      {session.pinned ? <PinOff /> : <Pin />} {session.pinned ? "Unpin" : "Pin"}
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => startEdit(session)}>
                      <Pencil /> Rename
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => duplicate(session.id)}>
                      <Copy /> Duplicate
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => {
                        const { content, filename, mime } = exportSession(session, "json");
                        downloadTextFile(content, filename, mime);
                      }}
                    >
                      <Download /> Export
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => setPendingDelete(session)}
                      className="text-destructive focus:text-destructive"
                    >
                      <Trash2 /> Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </>
            )}
          </div>
        ))}
      </div>

      <ConfirmDialog
        open={!!pendingDelete}
        onOpenChange={(open) => !open && setPendingDelete(null)}
        title="Delete session?"
        description={`"${pendingDelete?.title}" and its ${pendingDelete?.turns.length ?? 0} turn(s) will be permanently removed from this browser.`}
        confirmLabel="Delete"
        confirmVariant="destructive"
        onConfirm={() => {
          if (pendingDelete) remove(pendingDelete.id);
          setPendingDelete(null);
        }}
      />
    </div>
  );
}
