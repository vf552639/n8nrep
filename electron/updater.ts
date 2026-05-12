import { app, dialog, BrowserWindow } from "electron";
import { autoUpdater } from "electron-updater";

export function registerAutoUpdater(mainWindow: BrowserWindow): void {
  if (!process.env.AUTO_UPDATE_FEED_URL && app.isPackaged) {
    console.log("auto-update: AUTO_UPDATE_FEED_URL not set; skipping");
    return;
  }

  autoUpdater.autoDownload = true;
  autoUpdater.autoInstallOnAppQuit = true;

  autoUpdater.on("update-available", (info) => {
    console.log("auto-update: update-available", info.version);
    mainWindow.webContents.send("updater:status", {
      kind: "available",
      version: info.version,
    });
  });

  autoUpdater.on("update-not-available", () => {
    mainWindow.webContents.send("updater:status", { kind: "not-available" });
  });

  autoUpdater.on("download-progress", (p) => {
    mainWindow.webContents.send("updater:status", {
      kind: "progress",
      percent: p.percent,
    });
  });

  autoUpdater.on("update-downloaded", async (info) => {
    const r = await dialog.showMessageBox(mainWindow, {
      type: "info",
      buttons: ["Restart now", "Later"],
      defaultId: 0,
      cancelId: 1,
      title: "Update ready",
      message: `n8nrep ${info.version} downloaded.`,
      detail: "Restart to install. Your work is preserved.",
    });
    if (r.response === 0) autoUpdater.quitAndInstall();
  });

  autoUpdater.on("error", (err) => {
    console.error("auto-update: error", err);
    mainWindow.webContents.send("updater:status", {
      kind: "error",
      message: String(err?.message ?? err),
    });
  });

  autoUpdater
    .checkForUpdates()
    .catch((e) => console.error("auto-update: checkForUpdates failed", e));
}
