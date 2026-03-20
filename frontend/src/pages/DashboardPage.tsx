import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { dashboardApi } from "@/api/dashboard";
import { tasksApi } from "@/api/tasks";
import { DashboardStats, QueueStatus } from "@/types/common";
import StatusBadge from "@/components/common/StatusBadge";
import { Activity, Server } from "lucide-react";

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

  const { data: latestTasks, isLoading: tasksLoading } = useQuery({
    queryKey: ["dashboard-latest-tasks"],
    queryFn: () => tasksApi.getAll({ limit: 10 }),
    refetchInterval: 10000
  });

  const isLoading = statsLoading || queueLoading || tasksLoading;

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

      <div className="bg-white rounded-lg border shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b flex justify-between items-center bg-slate-50">
          <h2 className="text-lg font-semibold flex items-center gap-2"><Activity className="w-5 h-5"/> Latest 10 Tasks</h2>
          <Link to="/tasks" className="text-sm text-blue-600 hover:underline">View All</Link>
        </div>
        <div className="divide-y">
          {latestTasks?.length === 0 && <div className="p-6 text-center text-slate-500">No tasks found</div>}
          {latestTasks?.map(task => (
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
