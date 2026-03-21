/** Parse step.result from API — may be JSON string or already an object */
export function parseStepResultJson(raw: unknown): Record<string, unknown> | null {
  if (raw == null || raw === "") return null;
  if (typeof raw === "object" && raw !== null && !Array.isArray(raw)) {
    return raw as Record<string, unknown>;
  }
  if (typeof raw === "string") {
    try {
      const v = JSON.parse(raw);
      return typeof v === "object" && v !== null && !Array.isArray(v) ? (v as Record<string, unknown>) : null;
    } catch {
      return null;
    }
  }
  return null;
}
