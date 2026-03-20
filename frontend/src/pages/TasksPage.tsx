import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import api from "@/api/client";
import { Task } from "@/types/task";
import { PaginatedList } from "@/types/common";
import DataTable from "@/components/common/DataTable";
import StatusBadge from "@/components/common/StatusBadge";
import { Plus, Upload, Play, Square } from "lucide-react";

export default function TasksPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(0);
  const [statusFilter, setStatusFilter] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["tasks", { status: statusFilter, page }],
    queryFn: async () => {
      const res = await api.get<PaginatedList<Task>>("/tasks", {
        params: { status: statusFilter || undefined, skip: page * 50, limit: 50 },
      });
      return res.data;
    },
  });

  const columns = [
    { key: "main_keyword", header: "Keyword" },
    { key: "country", header: "Country" },
    { 
      key: "status", 
      header: "Status",
      render: (t: Task) => <StatusBadge status={t.status} />
    },
    { 
      key: "progress", 
      header: "Progress",
      render: (t: Task) => (
        <div className="w-full bg-slate-200 rounded-full h-2.5 max-w-[100px]">
          <div className="bg-blue-600 h-2.5 rounded-full" style={{ width: `${t.progress || 0}%` }}></div>
        </div>
      )
    },
    { 
      key: "cost", 
      header: "Cost",
      render: (t: Task) => <span className="text-slate-500">${t.cost?.toFixed(4) || "0.0000"}</span>
    },
    { 
      key: "created_at", 
      header: "Date",
      render: (t: Task) => new Date(t.created_at).toLocaleString()
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Tasks</h1>
        <div className="flex gap-2">
          <select 
            className="border rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="processing">Processing</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>
          <button className="flex items-center gap-2 bg-white hover:bg-slate-50 text-slate-800 px-4 py-2 rounded-md transition-colors text-sm font-medium border shadow-sm">
            <Upload className="w-4 h-4" /> Import CSV
          </button>
          <button className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 rounded-md transition-colors text-sm font-medium shadow-sm">
            <Plus className="w-4 h-4" /> Create Task
          </button>
        </div>
      </div>

      <div className="flex gap-2 bg-white p-3 rounded-lg border shadow-sm item-center">
        <div className="text-sm font-medium text-slate-700 mr-4 self-center px-2">Queue Controls:</div>
        <button className="flex items-center gap-2 bg-blue-50 text-blue-700 hover:bg-blue-100 px-3 py-1.5 rounded text-sm transition-colors border border-blue-200 shadow-sm">
          <Play className="w-4 h-4" /> Start Next
        </button>
        <button className="flex items-center gap-2 bg-green-50 text-green-700 hover:bg-green-100 px-3 py-1.5 rounded text-sm transition-colors border border-green-200 shadow-sm">
          <Play className="w-4 h-4" /> Start All
        </button>
        <button className="flex items-center gap-2 bg-red-50 text-red-700 hover:bg-red-100 px-3 py-1.5 rounded text-sm transition-colors border border-red-200 shadow-sm">
          <Square className="w-4 h-4" /> Stop Queue
        </button>
      </div>

      <DataTable 
        columns={columns} 
        data={data?.items || []} 
        isLoading={isLoading} 
        onRowClick={(task) => navigate(`/tasks/${task.id}`)}
      />
    </div>
  );
}
