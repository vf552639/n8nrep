import { contextBridge, ipcRenderer, shell } from "electron";

contextBridge.exposeInMainWorld("electron", {
  openExternal: (url: string) => shell.openExternal(url),
  codex: {
    runLogin: (): Promise<{ ok: boolean; error?: string }> =>
      ipcRenderer.invoke("auth:codex:run-login"),
    onLog: (cb: (line: string) => void) => {
      const handler = (_: unknown, line: string) => cb(line);
      ipcRenderer.on("auth:codex:log", handler);
      return () => ipcRenderer.off("auth:codex:log", handler);
    },
  },
});

interface UpdaterStatus {
  kind: string;
  [key: string]: unknown;
}

contextBridge.exposeInMainWorld("updater", {
  onStatus: (cb: (status: UpdaterStatus) => void) => {
    const handler = (_: unknown, status: UpdaterStatus) => cb(status);
    ipcRenderer.on("updater:status", handler);
    return () => ipcRenderer.off("updater:status", handler);
  },
});
