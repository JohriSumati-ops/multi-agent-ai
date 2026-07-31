const STOPWORDS = new Set(["the", "a", "an", "is", "are", "was", "were", "of", "to", "in", "on", "and", "or", "for", "with"]);

/** Splits `text` into segments, marking which ones match a significant term from `query`, for highlighting matched text in search results. */
export function splitForHighlight(text: string, query: string): { text: string; match: boolean }[] {
  const terms = Array.from(
    new Set(
      query
        .toLowerCase()
        .split(/\W+/)
        .filter((w) => w.length > 2 && !STOPWORDS.has(w))
    )
  );
  if (terms.length === 0) return [{ text, match: false }];

  const pattern = new RegExp(`(${terms.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "gi");
  const parts = text.split(pattern);
  const termSet = new Set(terms);
  return parts.filter((p) => p.length > 0).map((part) => ({ text: part, match: termSet.has(part.toLowerCase()) }));
}
