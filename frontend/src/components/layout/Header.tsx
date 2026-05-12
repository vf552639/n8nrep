import { useEffect, useState } from "react";
import AccountChip from "@/components/AccountChip";

interface UpdaterStatus {
  kind: string;
  version?: string;
  percent?: number;
  message?: string;
}

interface UpdaterBridge {
  onStatus?: (cb: (status: UpdaterStatus) => void) => () => void;
}

function useUpdaterStatus(): UpdaterStatus | null {
  const [status, setStatus] = useState<UpdaterStatus | null>(null);
  useEffect(() => {
    const updater = (window as unknown as { updater?: UpdaterBridge }).updater;
    const off = updater?.onStatus?.((s) => setStatus(s));
    return () => off?.();
  }, []);
  return status;
}

export default function Header() {
  const status = useUpdaterStatus();
  return (
    <header className="h-16 border-b bg-white flex items-center justify-between px-6 shrink-0">
      <div className="text-lg font-semibold text-slate-800">SEO Content Generator UI</div>
      <div className="flex items-center gap-3">
        {status && status.kind !== "not-available" && (
          <span
            className={`text-xs px-2 py-1 rounded ${
              status.kind === "error"
                ? "bg-red-100 text-red-800"
                : "bg-emerald-100 text-emerald-800"
            }`}
          >
            {status.kind === "available" && `Update available (v${status.version})`}
            {status.kind === "progress" &&
              `Downloading update… ${(status.percent ?? 0).toFixed(0)}%`}
            {status.kind === "error" && `Update error: ${status.message ?? "unknown"}`}
          </span>
        )}
        <AccountChip />
      </div>
    </header>
  );
}
