/** Safe string for toasts / UI — FastAPI may return `detail` as string, array of validation errors, or object. */
export function formatApiErrorDetail(detail: unknown): string {
  if (detail == null) return "";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        try {
          return JSON.stringify(item);
        } catch {
          return String(item);
        }
      })
      .filter(Boolean)
      .join("; ");
  }
  if (typeof detail === "object" && detail !== null && "message" in detail) {
    const o = detail as { message?: unknown; existing_project_id?: unknown };
    let s = o.message != null ? String(o.message) : "";
    if (o.existing_project_id != null) {
      s += ` (existing id: ${String(o.existing_project_id)})`;
    }
    return s || JSON.stringify(detail);
  }
  if (typeof detail === "object") {
    try {
      return JSON.stringify(detail);
    } catch {
      return "Request failed";
    }
  }
  return String(detail);
}
