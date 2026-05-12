import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { LogIn, LogOut, KeyRound, RefreshCw } from "lucide-react";
import toast from "react-hot-toast";
import type { LoginStartResponse, LoginStatus } from "@/types/auth";

interface Props {
  provider: "codex" | "claude";
  label: string;
  api: {
    status: () => Promise<LoginStatus>;
    login: () => Promise<LoginStartResponse>;
    logout: () => Promise<{ logged_out: boolean }>;
  };
  /** Optional Electron-side login runner (e.g., window.electron.codex.runLogin). */
  electronLogin?: () => Promise<{ ok: boolean; error?: string }>;
}

export default function LoginPanel({ provider, label, api, electronLogin }: Props) {
  const qc = useQueryClient();
  const queryKey = ["auth", provider, "status"];

  const { data: status, isLoading } = useQuery({
    queryKey,
    queryFn: api.status,
    refetchInterval: (q) => (q.state.data?.logged_in ? false : 3000),
  });

  const loginMutation = useMutation({
    mutationFn: async () => {
      const plan = await api.login();
      if (plan.method === "cli" && electronLogin) {
        const r = await electronLogin();
        if (!r.ok) throw new Error(r.error || "CLI login failed");
      } else if (plan.method === "browser" && plan.url) {
        (window as unknown as { electron?: { openExternal?: (u: string) => void } }).electron?.openExternal?.(plan.url);
      }
      return plan;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey });
      toast.success(`${label}: login flow started`);
    },
    onError: (e: Error) => toast.error(`${label}: ${e.message}`),
  });

  const logoutMutation = useMutation({
    mutationFn: api.logout,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey });
      toast.success(`${label}: logged out`);
    },
  });

  if (isLoading) return <div className="text-sm text-slate-500">Checking {label} login status…</div>;

  return (
    <div className="border rounded-lg p-4 space-y-3 bg-white">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-slate-900">{label}</h3>
          <p className="text-xs text-slate-500 mt-1">
            {status?.logged_in
              ? `Logged in via ${status.method}${status.account_id ? ` (${status.account_id})` : ""}`
              : "Not logged in"}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            className="px-3 py-1.5 text-xs rounded border hover:bg-slate-50 flex items-center gap-1"
            onClick={() => qc.invalidateQueries({ queryKey })}
          >
            <RefreshCw className="w-3 h-3" /> Refresh
          </button>
          {status?.logged_in ? (
            <button
              type="button"
              className="px-3 py-1.5 text-xs rounded bg-red-600 text-white hover:bg-red-700 flex items-center gap-1"
              onClick={() => logoutMutation.mutate()}
              disabled={logoutMutation.isPending}
            >
              <LogOut className="w-3 h-3" /> Logout
            </button>
          ) : (
            <button
              type="button"
              className="px-3 py-1.5 text-xs rounded bg-blue-600 text-white hover:bg-blue-700 flex items-center gap-1"
              onClick={() => loginMutation.mutate()}
              disabled={loginMutation.isPending}
            >
              <LogIn className="w-3 h-3" /> Login
            </button>
          )}
        </div>
      </div>
      {!status?.logged_in && (
        <div className="text-xs text-slate-500 flex items-center gap-1">
          <KeyRound className="w-3 h-3" /> Or set the API key in the General → Integrations tab.
        </div>
      )}
    </div>
  );
}
