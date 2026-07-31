"use client";

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import { Printer, ArrowLeft } from "lucide-react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { getSessions } from "@/features/workspace/session-store";
import type { WorkspaceSession } from "@/features/workspace/session-store";

export default function SessionPrintPage() {
  const params = useParams<{ sessionId: string }>();
  const router = useRouter();
  const [session, setSession] = React.useState<WorkspaceSession | null | undefined>(undefined);

  React.useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time sync from localStorage, an SSR-unavailable external source; can't be computed during render.
    setSession(getSessions().find((s) => s.id === params.sessionId) ?? null);
  }, [params.sessionId]);

  if (session === undefined) return null;

  if (session === null) {
    return (
      <div className="mx-auto max-w-2xl">
        <EmptyState title="Session not found" description="It may have been deleted from this browser." />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="no-print mb-6 flex items-center justify-between">
        <Button variant="ghost" size="sm" onClick={() => router.push("/research")}>
          <ArrowLeft /> Back to workspace
        </Button>
        <Button size="sm" onClick={() => window.print()}>
          <Printer /> Print / Save as PDF
        </Button>
      </div>

      <article className="space-y-8">
        <header className="space-y-1 border-b border-border pb-4">
          <h1 className="text-2xl font-semibold text-foreground">{session.title}</h1>
          <p className="text-xs text-muted-foreground">
            Exported {new Date().toLocaleString()} · {session.turns.length} turn{session.turns.length === 1 ? "" : "s"}
          </p>
        </header>

        {session.turns.map((turn, i) => (
          <section key={turn.id} className="space-y-2 break-inside-avoid">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              {i + 1}. {turn.mode} · {new Date(turn.timestamp).toLocaleString()}
            </p>
            <p className="font-medium text-foreground">{turn.query}</p>
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
              {turn.result.answer ?? "No answer was generated."}
            </p>
            {turn.result.citations.length > 0 && (
              <div className="text-xs text-muted-foreground">
                <p className="font-medium text-foreground">Citations</p>
                <ul className="list-disc pl-5">
                  {turn.result.citations.map((c, idx) => (
                    <li key={idx}>
                      {c.citation_text} — {c.is_memory ? "memory" : (c.document_title ?? "unknown source")}
                      {c.page_number !== null ? `, p.${c.page_number}` : ""}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        ))}
      </article>
    </div>
  );
}
