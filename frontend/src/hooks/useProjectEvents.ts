import { useEffect, useRef, useState } from "react";

export interface ProjectEvent {
  ts?: string;
  msg?: string;
  level?: string;
  step?: string;
  type?: string;
  status?: string;
}

export function useProjectEvents(
  projectId: string | undefined,
  active: boolean,
  onDone?: (status: string) => void
) {
  const [events, setEvents] = useState<ProjectEvent[]>([]);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!active || !projectId) return;

    const es = new EventSource(`/api/sse/projects/${projectId}/events`);
    esRef.current = es;

    es.onmessage = (e) => {
      try {
        const evt: ProjectEvent = JSON.parse(e.data);
        if (evt.type === "done") {
          onDone?.(evt.status ?? "completed");
          es.close();
          esRef.current = null;
          return;
        }
        setEvents((prev) => [...prev.slice(-499), evt]);
      } catch {
        // malformed SSE data — ignore
      }
    };

    es.onerror = () => {
      // Browser will auto-reconnect; no action needed
    };

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [projectId, active]);

  return { events };
}
