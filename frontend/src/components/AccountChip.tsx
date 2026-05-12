import { useQuery } from "@tanstack/react-query";
import api from "@/api/client";

interface ClaudeStatus {
  logged_in: boolean;
  email?: string | null;
}

export default function AccountChip() {
  const { data } = useQuery<ClaudeStatus>({
    queryKey: ["claude-status"],
    queryFn: () => api.get<ClaudeStatus>("/auth/claude/status").then((r) => r.data),
    refetchInterval: 30_000,
    retry: false,
  });

  if (!data) return null;

  if (data.logged_in) {
    return (
      <div
        className="flex items-center gap-1.5 rounded-full border border-green-200 bg-green-50 px-2.5 py-1 text-[11px] font-medium text-green-700"
        title={data.email ?? "Logged in to Claude"}
      >
        <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
        Claude
      </div>
    );
  }

  return (
    <div
      className="flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] font-medium text-slate-500"
      title="Using OpenRouter"
    >
      <span className="h-1.5 w-1.5 rounded-full bg-slate-400" />
      OpenRouter
    </div>
  );
}
