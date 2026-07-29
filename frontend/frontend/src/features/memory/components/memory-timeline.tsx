"use client";

import * as React from "react";
import { Clock, ShieldCheck, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useMemoryHistory, useDeleteMemoryHistory } from "@/features/memory/hooks/use-memory";
import type { MemoryRecordOut, MemoryType } from "@/types/memory";

const TYPE_OPTIONS: { value: MemoryType | "all"; label: string }[] = [
  { value: "all", label: "All types" },
  { value: "short_term", label: "Short-term" },
  { value: "long_term", label: "Long-term" },
  { value: "conversation", label: "Conversation" },
  { value: "document", label: "Document" },
];

export function MemoryTimeline() {
  const [type, setType] = React.useState<MemoryType | "all">("all");
  const { data: memories, isLoading } = useMemoryHistory(type === "all" ? undefined : type);
  const { mutate: deleteHistory, isPending: deleting } = useDeleteMemoryHistory();

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Select value={type} onValueChange={(v) => setType(v as MemoryType | "all")}>
          <SelectTrigger className="w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {TYPE_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button
          variant="ghost"
          size="sm"
          disabled={deleting}
          className="text-destructive hover:text-destructive"
          onClick={() => deleteHistory(type === "all" ? undefined : type)}
        >
          <Trash2 className="h-3.5 w-3.5" />
          Delete {type === "all" ? "all history" : "this type"}
        </Button>
      </div>

      <div className="space-y-2">
        {isLoading && Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-16 w-full" />)}

        {!isLoading && memories?.length === 0 && (
          <p className="rounded-lg border border-dashed border-border py-10 text-center text-sm text-muted-foreground">
            No memory entries for this filter.
          </p>
        )}

        {memories?.map((m) => <MemoryEntry key={m.id} memory={m} />)}
      </div>
    </div>
  );
}

function MemoryEntry({ memory }: { memory: MemoryRecordOut }) {
  return (
    <div className="rounded-lg border border-border p-3">
      <div className="mb-1.5 flex flex-wrap items-center gap-2">
        <Badge variant="outline" className="font-mono">
          {memory.memory_type}
        </Badge>
        <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
          <ShieldCheck className="h-3 w-3" /> importance {memory.importance_score.toFixed(2)}
        </span>
        <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
          <Clock className="h-3 w-3" /> {new Date(memory.created_at).toLocaleString()}
        </span>
        {memory.expires_at && (
          <span className="text-[11px] text-warning">
            expires {new Date(memory.expires_at).toLocaleDateString()}
          </span>
        )}
      </div>
      <p className="text-sm text-foreground">{memory.content}</p>
    </div>
  );
}
