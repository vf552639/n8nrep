import { contextBridge, shell } from "electron";

contextBridge.exposeInMainWorld("electron", {
  openExternal: (url: string) => shell.openExternal(url),
});
