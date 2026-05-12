import { ipcMain, BrowserWindow } from "electron";
import { spawn } from "child_process";

export function registerLoginHandlers(mainWindow: BrowserWindow): void {
  ipcMain.handle("auth:codex:run-login", async (): Promise<{ ok: boolean; error?: string }> => {
    return new Promise((resolve) => {
      const child = spawn("codex", ["login"], {
        stdio: ["ignore", "pipe", "pipe"],
        env: process.env,
      });
      let stderr = "";
      child.stdout?.on("data", (d: Buffer) =>
        mainWindow.webContents.send("auth:codex:log", d.toString())
      );
      child.stderr?.on("data", (d: Buffer) => {
        stderr += d.toString();
        mainWindow.webContents.send("auth:codex:log", d.toString());
      });
      child.on("error", (err) => resolve({ ok: false, error: err.message }));
      child.on("exit", (code) => {
        if (code === 0) resolve({ ok: true });
        else
          resolve({
            ok: false,
            error: `codex login exited with code ${code}: ${stderr.slice(-500)}`,
          });
      });
    });
  });
}
