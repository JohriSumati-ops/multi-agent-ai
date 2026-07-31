"use client";

import * as React from "react";
import { Menu } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Sheet, SheetTrigger, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { SessionSidebar } from "@/features/workspace/components/session-sidebar";
import { QueryComposer } from "@/features/workspace/components/query-composer";
import { ConversationThread } from "@/features/workspace/components/conversation-thread";
import { ExportMenu } from "@/features/workspace/components/export-menu";
import { useWorkspaceSessions } from "@/features/workspace/hooks/use-workspace-sessions";
import { useResearchQuery, useResearchAnswer, useResearchSummarize } from "@/features/research/hooks/use-research";
import type { ResearchMode } from "@/features/research/hooks/use-research";

export default function ResearchPage() {
  const { activeSession, newSession, appendTurn } = useWorkspaceSessions();
  const [mobileOpen, setMobileOpen] = React.useState(false);

  const query = useResearchQuery();
  const answer = useResearchAnswer();
  const summarize = useResearchSummarize();
  const isPending = query.isPending || answer.isPending || summarize.isPending;

  async function handleSubmit(text: string, mode: ResearchMode, documentId: string | null) {
    const session = activeSession ?? newSession();
    const mutation = mode === "answer" ? answer : mode === "summarize" ? summarize : query;
    try {
      const result = await mutation.mutateAsync({ query: text, document_id: documentId });
      appendTurn(session.id, { mode, query: text, documentId, result });
    } catch {
      // Errors already surface via toast in useResearchMutation; nothing further to do here.
    }
  }

  return (
    <div className="-m-4 flex h-[calc(100vh-3.5rem)] lg:-m-6">
      {/* Desktop session sidebar */}
      <aside className="hidden w-64 shrink-0 flex-col border-r border-border lg:flex">
        <SessionSidebar />
      </aside>

      {/* Main conversation column */}
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-2.5">
          <div className="flex min-w-0 items-center gap-2">
            <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" className="shrink-0 lg:hidden" aria-label="Open sessions">
                  <Menu className="h-4 w-4" />
                </Button>
              </SheetTrigger>
              <SheetContent>
                <SheetTitle>Sessions</SheetTitle>
                <SessionSidebar onSelect={() => setMobileOpen(false)} />
              </SheetContent>
            </Sheet>
            <h1 className="truncate text-sm font-semibold text-foreground">
              {activeSession?.title ?? "Research Workspace"}
            </h1>
          </div>
          {activeSession && <ExportMenu session={activeSession} />}
        </div>

        <ConversationThread turns={activeSession?.turns ?? []} isPending={isPending} />
        <QueryComposer onSubmit={handleSubmit} isPending={isPending} />
      </div>
    </div>
  );
}
