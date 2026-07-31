/**
 * Export Center logic.
 *
 * The backend has no document-generation endpoint for research output —
 * exporting is done entirely client-side. Markdown/Text/JSON are real,
 * complete serializations of the data already on screen. "PDF" is the
 * browser's native print-to-PDF against a print-optimized view
 * (`/research/print/[sessionId]`) rather than a fabricated server PDF —
 * an honest mechanism rather than a button that silently does nothing.
 */

import type { ConversationTurn, WorkspaceSession } from "@/features/workspace/session-store";

export type ExportFormat = "markdown" | "text" | "json";

function formatTurnMarkdown(turn: ConversationTurn, index: number): string {
  const lines: string[] = [];
  lines.push(`## ${index + 1}. ${turn.query}`);
  lines.push("");
  lines.push(`*${turn.mode} · ${new Date(turn.timestamp).toLocaleString()}*`);
  lines.push("");
  lines.push(turn.result.answer ?? "_No answer was generated._");
  lines.push("");
  if (turn.result.citations.length > 0) {
    lines.push("**Citations:**");
    for (const c of turn.result.citations) {
      const src = c.is_memory ? "memory" : c.document_title ?? "unknown source";
      const page = c.page_number !== null ? `, p.${c.page_number}` : "";
      lines.push(`- ${c.citation_text} (${src}${page})`);
    }
    lines.push("");
  }
  if (turn.result.sources_used.length > 0) {
    lines.push("**Sources used:** " + turn.result.sources_used.map((s) => s.document_title).join(", "));
    lines.push("");
  }
  return lines.join("\n");
}

export function sessionToMarkdown(session: WorkspaceSession): string {
  const header = [
    `# ${session.title}`,
    "",
    `Exported ${new Date().toLocaleString()} · ${session.turns.length} turn${session.turns.length === 1 ? "" : "s"}`,
    "",
    "---",
    "",
  ].join("\n");
  return header + session.turns.map(formatTurnMarkdown).join("\n---\n\n");
}

export function sessionToText(session: WorkspaceSession): string {
  const lines: string[] = [session.title, "=".repeat(session.title.length), ""];
  session.turns.forEach((turn, i) => {
    lines.push(`${i + 1}. Q: ${turn.query}`);
    lines.push(`A: ${turn.result.answer ?? "No answer was generated."}`);
    lines.push("");
  });
  return lines.join("\n");
}

export function sessionToJson(session: WorkspaceSession): string {
  return JSON.stringify(session, null, 2);
}

export function turnToMarkdown(turn: ConversationTurn): string {
  return formatTurnMarkdown(turn, 0).replace(/^## 1\. /, "## ");
}

export function turnToText(turn: ConversationTurn): string {
  return `Q: ${turn.query}\n\nA: ${turn.result.answer ?? "No answer was generated."}`;
}

export function exportSession(session: WorkspaceSession, format: ExportFormat): { content: string; filename: string; mime: string } {
  const slug = session.title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "") || "session";
  if (format === "markdown") return { content: sessionToMarkdown(session), filename: `${slug}.md`, mime: "text/markdown" };
  if (format === "text") return { content: sessionToText(session), filename: `${slug}.txt`, mime: "text/plain" };
  return { content: sessionToJson(session), filename: `${slug}.json`, mime: "application/json" };
}

/** Triggers a browser download of a text blob — no server round-trip needed. */
export function downloadTextFile(content: string, filename: string, mime: string): void {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
