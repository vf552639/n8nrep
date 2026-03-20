import { useQuery } from "@tanstack/react-query";
import api from "@/api/client";
import { DashboardStats } from "@/types/common";

export default function DashboardPage() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: async () => {
      const res = await api.get<DashboardStats>("/dashboard/stats");
      return res.data;
    },
  });

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight text-slate-900">Dashboard</h1>
      
      {isLoading ? (
        <div>Loading stats...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div className="bg-white p-6 rounded-lg border shadow-sm flex flex-col items-center">
            <div className="text-sm font-medium text-slate-500 mb-1">Total Tasks</div>
            <div className="text-3xl font-bold text-slate-800">{stats?.total || 0}</div>
          </div>
          <div className="bg-blue-50 p-6 rounded-lg border border-blue-100 shadow-sm flex flex-col items-center">
            <div className="text-sm font-medium text-blue-600 mb-1">Processing</div>
            <div className="text-3xl font-bold text-blue-700">{stats?.processing || 0}</div>
          </div>
          <div className="bg-green-50 p-6 rounded-lg border border-green-100 shadow-sm flex flex-col items-center">
            <div className="text-sm font-medium text-green-600 mb-1">Completed</div>
            <div className="text-3xl font-bold text-green-700">{stats?.completed || 0}</div>
          </div>
          <div className="bg-red-50 p-6 rounded-lg border border-red-100 shadow-sm flex flex-col items-center">
            <div className="text-sm font-medium text-red-600 mb-1">Failed</div>
            <div className="text-3xl font-bold text-red-700">{stats?.failed || 0}</div>
          </div>
          <div className="bg-gray-50 p-6 rounded-lg border shadow-sm flex flex-col items-center">
            <div className="text-sm font-medium text-gray-500 mb-1">Pending</div>
            <div className="text-3xl font-bold text-gray-700">{stats?.pending || 0}</div>
          </div>
        </div>
      )}
    </div>
  );
}
