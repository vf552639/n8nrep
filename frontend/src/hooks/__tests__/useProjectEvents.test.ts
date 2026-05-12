import { renderHook, act } from "@testing-library/react";
import { vi } from "vitest";
import { useProjectEvents } from "../useProjectEvents";

// Mock EventSource
class MockEventSource {
  static instances: MockEventSource[] = [];
  onmessage: ((e: MessageEvent) => void) | null = null;
  onerror: ((e: Event) => void) | null = null;
  closed = false;
  constructor(public url: string) {
    MockEventSource.instances.push(this);
  }
  close() { this.closed = true; }
  emit(data: object) {
    this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent);
  }
}

beforeEach(() => {
  MockEventSource.instances = [];
  (global as any).EventSource = MockEventSource;
});

test("opens EventSource when active=true", () => {
  renderHook(() => useProjectEvents("proj-1", true));
  expect(MockEventSource.instances).toHaveLength(1);
  expect(MockEventSource.instances[0].url).toContain("proj-1");
});

test("collects log events from SSE stream", () => {
  const { result } = renderHook(() => useProjectEvents("proj-1", true));
  act(() => {
    MockEventSource.instances[0].emit({ msg: "step done", level: "info" });
  });
  expect(result.current.events).toHaveLength(1);
  expect(result.current.events[0].msg).toBe("step done");
});

test("calls onDone when type=done received", () => {
  const onDone = vi.fn();
  renderHook(() => useProjectEvents("proj-1", true, onDone));
  act(() => {
    MockEventSource.instances[0].emit({ type: "done", status: "completed" });
  });
  expect(onDone).toHaveBeenCalledWith("completed");
  expect(MockEventSource.instances[0].closed).toBe(true);
});

test("does not open EventSource when active=false", () => {
  renderHook(() => useProjectEvents("proj-1", false));
  expect(MockEventSource.instances).toHaveLength(0);
});
