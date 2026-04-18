/**
 * Canonical display form for language names in dropdowns (per whitespace-separated word).
 * Matches backend INITCAP-style normalization for typical values like "french" → "French".
 */
export function normalizeLanguageDisplay(raw: string): string {
  const t = raw.trim();
  if (!t) return t;
  return t
    .split(/\s+/)
    .map((word) => (word ? word.charAt(0).toUpperCase() + word.slice(1).toLowerCase() : ""))
    .join(" ");
}

/** Case-insensitive match for author/site language vs form selection. */
export function languageEquals(
  a: string | undefined | null,
  b: string | undefined | null
): boolean {
  return (a ?? "").trim().toLowerCase() === (b ?? "").trim().toLowerCase();
}
