import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { dashboardApi } from "@/api/dashboard";
import { tasksApi } from "@/api/tasks";
import { DashboardStats, QueueStatus } from "@/types/common";
import StatusBadge from "@/components/common/StatusBadge";
import { Activity, Server, Search } from "lucide-react";

export default function DashboardPage() {
    const { data: stats, isLoading: statsLoading } = useQuery<DashboardStats>({
    queryKey: ["dashboard-stats"],
    queryFn: dashboardApi.getStats,
    refetchInterval: 10000
  });

  const { data: queue, isLoading: queueLoading } = useQuery<QueueStatus>({
    queryKey: ["dashboard-queue"],
    queryFn: dashboardApi.getQueue,
    refetchInterval: 10000
  });

  const { data: serpHealth } = useQuery({
    queryKey: ["serp-health"],
    queryFn: () => dashboardApi.getSerpHealth(),
    refetchInterval: 300000,
  });

  const { data: latestTasksRes, isLoading: tasksLoading } = useQuery({
    queryKey: ["dashboard-latest-tasks"],
    queryFn: () => tasksApi.getAll({ limit: 10, skip: 0 }),
    refetchInterval: 10000,
  });
  const latestTasks = latestTasksRes?.items;

  const isLoading = statsLoading || queueLoading || tasksLoading;

  const overall = serpHealth?.overall as string | undefined;
  const serpBadgeClass =
    overall === "ok"
      ? "bg-green-50 text-green-800 border-green-200"
      : overall === "unconfigured"
        ? "bg-slate-100 text-slate-600 border-slate-200"
        : overall === "error"
          ? "bg-red-50 text-red-800 border-red-200"
          : "bg-slate-50 text-slate-700 border-slate-200";
  const serpLabel =
    overall === "ok"
      ? "SERP: Online"
      : overall === "unconfigured"
        ? "SERP: Not configured"
        : overall === "error"
          ? "SERP: Degraded"
          : "SERP: —";

  if (isLoading) return <div className="p-8 text-center animate-pulse">Loading dashboard...</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Dashboard</h1>
        <div className="flex gap-4">
           {queue && (
             <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-sm font-medium ${queue.celery_workers_online ? 'bg-green-50 text-green-700 border-green-200' : 'bg-red-50 text-red-700 border-red-200'}`}>
               <Server className="w-4 h-4" />
               Celery: {queue.celery_workers_online ? 'Online' : 'Offline'}
             </div>
           )}
           {serpHealth && (
             <div
               className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-sm font-medium ${serpBadgeClass}`}
               title={[
                 serpHealth.dataforseo &&
                   typeof serpHealth.dataforseo === "object" &&
                   `DataForSEO: ${(serpHealth.dataforseo as { status?: string }).status === "ok" ? "✓" : "✕"} ${(serpHealth.dataforseo as { latency_ms?: number }).latency_ms ?? "—"}ms`,
                 serpHealth.serpapi &&
                   typeof serpHealth.serpapi === "object" &&
                   `SerpAPI: ${(serpHealth.serpapi as { status?: string }).status === "ok" ? "✓" : "✕"} ${(serpHealth.serpapi as { latency_ms?: number }).latency_ms ?? "—"}ms`,
               ]
                 .filter(Boolean)
                 .join(" | ")}
             >
               <Search className="w-4 h-4" />
               {serpLabel}
             </div>
           )}
           {stats && (
             <div className="flex items-center gap-2 px-3 py-1.5 rounded-full border bg-slate-50 text-slate-700 border-slate-200 text-sm font-medium">
               Mode: {stats.sequential_mode ? 'Sequential' : 'Parallel'}
             </div>
           )}
        </div>
      </div>
      
      <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
        <div className="bg-white p-6 rounded-lg border shadow-sm flex flex-col items-center">
          <div className="text-sm font-medium text-slate-500 mb-1">Total Tasks</div>
          <div className="text-3xl font-bold text-slate-800">{stats?.tasks?.total || 0}</div>
        </div>
        <div className="bg-blue-50 p-6 rounded-lg border border-blue-100 shadow-sm flex flex-col items-center">
          <div className="text-sm font-medium text-blue-600 mb-1">Processing</div>
          <div className="text-3xl font-bold text-blue-700">{stats?.tasks?.processing || 0}</div>
        </div>
        <div className="bg-green-50 p-6 rounded-lg border border-green-100 shadow-sm flex flex-col items-center">
          <div className="text-sm font-medium text-green-600 mb-1">Completed</div>
          <div className="text-3xl font-bold text-green-700">{stats?.tasks?.completed || 0}</div>
        </div>
        <div className="bg-red-50 p-6 rounded-lg border border-red-100 shadow-sm flex flex-col items-center">
          <div className="text-sm font-medium text-red-600 mb-1">Failed</div>
          <div className="text-3xl font-bold text-red-700">{stats?.tasks?.failed || 0}</div>
        </div>
        <div className="bg-gray-50 p-6 rounded-lg border shadow-sm flex flex-col items-center">
          <div className="text-sm font-medium text-gray-500 mb-1">Pending</div>
          <div className="text-3xl font-bold text-gray-700">{stats?.tasks?.pending || 0}</div>
        </div>
        <div className="bg-purple-50 p-6 rounded-lg border border-purple-100 shadow-sm flex flex-col items-center">
          <div className="text-sm font-medium text-purple-600 mb-1">Sites</div>
          <div className="text-3xl font-bold text-purple-700">{stats?.sites || 0}</div>
        </div>
      </div>

      {stats?.cost_by_day && stats.cost_by_day.length > 0 && (
        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-slate-900">Pipeline cost (completed tasks, last 30 days)</h2>
          <p className="mb-4 text-sm text-slate-500">
            Sum of <span className="font-mono">total_cost</span> by UTC day when tasks reached completed status.
          </p>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stats.cost_by_day}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} stroke="#64748b" />
                <YAxis tickFormatter={(v) => `$${Number(v).toFixed(2)}`} stroke="#64748b" width={56} />
                <Tooltip
                  formatter={(v: number | string) => [`$${Number(v).toFixed(4)}`, "Cost"]}
                  labelFormatter={(label) => `Date: ${label}`}
                />
                <Bar dataKey="cost" fill="#3b82f6" radius={[4, 4, 0, 0]} maxBarSize={48} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg border shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b flex justify-between items-center bg-slate-50">
          <h2 className="text-lg font-semibold flex items-center gap-2"><Activity className="w-5 h-5"/> Latest 10 Tasks</h2>
          <Link to="/tasks" className="text-sm text-blue-600 hover:underline">View All</Link>
        </div>
        <div className="divide-y">
          {latestTasks?.length === 0 && <div className="p-6 text-center text-slate-500">No tasks found</div>}
          {latestTasks?.map((task) => (
            <Link key={task.id} to={`/tasks/${task.id}`} className="flex items-center justify-between p-4 hover:bg-slate-50 transition-colors">
              <div>
                <div className="font-medium text-slate-900">{task.main_keyword}</div>
                <div className="text-xs text-slate-500 mt-1">{new Date(task.created_at).toLocaleString()} | {task.country} / {task.language}</div>
              </div>
              <StatusBadge status={task.status} />
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
