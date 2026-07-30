import type { Metadata } from "next";

import { RetrievalSearch } from "@/features/retrieval/components/retrieval-search";

export const metadata: Metadata = { title: "Retrieval — Research Assistant Console" };

export default function RetrievalPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Semantic retrieval</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Search embedded document chunks by meaning, not just keywords.
        </p>
      </div>
      <RetrievalSearch />
    </div>
  );
}
