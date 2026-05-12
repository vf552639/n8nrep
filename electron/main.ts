import { app, BrowserWindow, dialog } from "electron";
import { spawn, ChildProcess } from "child_process";
import * as path from "path";
import * as net from "net";
import * as http from "http";
import { registerLoginHandlers } from "./login_handlers";

let sidecar: ChildProcess | null = null;
let mainWindow: BrowserWindow | null = null;

function findFreePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.listen(0, "127.0.0.1", () => {
      const addr = server.address() as net.AddressInfo;
      server.close(() => resolve(addr.port));
    });
    server.on("error", reject);
  });
}

function waitForSidecar(port: number, maxMs = 30_000): Promise<void> {
  const deadline = Date.now() + maxMs;
  return new Promise((resolve, reject) => {
    function poll() {
      if (Date.now() > deadline) {
        reject(new Error(`Sidecar did not start within ${maxMs}ms`));
        return;
      }
      http
        .get(`http://127.0.0.1:${port}/api/health`, (res) => {
          // Always consume the response body to avoid socket stalls
          res.resume();
          if (res.statusCode === 200) resolve();
          else setTimeout(poll, 500);
        })
        .on("error", () => setTimeout(poll, 500));
    }
    poll();
  });
}

async function startSidecar(port: number): Promise<void> {
  const env = {
    ...process.env,
    DESKTOP_MODE: "true",
    AUTH_DISABLED: "true",
    PORT: String(port),
    LOG_LEVEL: "INFO",
  };

  if (app.isPackaged) {
    const sidecarPath = path.join(process.resourcesPath, "sidecar");
    sidecar = spawn(sidecarPath, [], { env, stdio: "pipe" });
  } else {
    // Dev: run python via uvicorn
    const projectRoot = path.resolve(__dirname, "..", "..");
    sidecar = spawn(
      "python3",
      ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(port)],
      { cwd: projectRoot, env, stdio: "pipe" }
    );
  }

  sidecar.stdout?.on("data", (d: Buffer) => process.stdout.write(d));
  sidecar.stderr?.on("data", (d: Buffer) => process.stderr.write(d));
  sidecar.on("exit", (code) => {
    console.log(`Sidecar exited with code ${code}`);
  });
}

async function createWindow(port: number): Promise<void> {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    title: "n8nrep",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  if (app.isPackaged) {
    const indexPath = path.join(__dirname, "..", "frontend", "dist", "index.html");
    await mainWindow.loadFile(indexPath, { query: { backendPort: String(port) } });
  } else {
    // Dev: Vite dev server — pass port via query
    await mainWindow.loadURL(`http://localhost:5173?backendPort=${port}`);
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

function killSidecar(): void {
  if (sidecar) {
    sidecar.kill();
    sidecar = null;
  }
}

app.whenReady().then(async () => {
  try {
    const port = await findFreePort();
    await startSidecar(port);
    await waitForSidecar(port);
    await createWindow(port);
    if (mainWindow) registerLoginHandlers(mainWindow);
  } catch (err) {
    dialog.showErrorBox(
      "Startup failed",
      err instanceof Error ? err.message : String(err)
    );
    app.quit();
  }
});

app.on("window-all-closed", () => {
  killSidecar();
  app.quit();
});

// before-quit fires after window-all-closed; sidecar is already null at this point
// but the handler is kept as a safety net for direct app.quit() calls
app.on("before-quit", () => {
  killSidecar();
});
