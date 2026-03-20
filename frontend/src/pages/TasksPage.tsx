import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { tasksApi } from "@/api/tasks";
import { Task } from "@/types/task";
// API mapping
import DataTable from "@/components/common/DataTable";
import StatusBadge from "@/components/common/StatusBadge";
import { Plus, Upload, Play, Square, X } from "lucide-react";

export default function TasksPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [statusFilter, setStatusFilter] = useState("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isImportOpen, setIsImportOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["tasks", { status: statusFilter, page }],
    queryFn: async () => {
      return tasksApi.getAll({ status: statusFilter || undefined, skip: page * 50, limit: 50 });
    },
  });

  const handleStartNext = async () => {
    try {
      await tasksApi.startNext();
      toast.success("Started next task in queue");
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    } catch {
      toast.error("Failed to start next task");
    }
  };

  const handleStartAll = async () => {
    try {
      await tasksApi.startAll();
      toast.success("Started all pending tasks");
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    } catch {
      toast.error("Failed to start all tasks");
    }
  };

  const columns = [
    { key: "main_keyword", header: "Keyword" },
    { key: "country", header: "Country" },
    { 
      key: "status", 
      header: "Status",
      render: (t: Task) => <StatusBadge status={t.status} />
    },
    { 
      key: "total_cost", 
      header: "Cost",
      render: (t: Task) => <span className="text-slate-500">${t.total_cost?.toFixed(4) || "0.0000"}</span>
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
          <button 
            onClick={() => setIsImportOpen(true)}
            className="flex items-center gap-2 bg-white hover:bg-slate-50 text-slate-800 px-4 py-2 rounded-md transition-colors text-sm font-medium border shadow-sm"
          >
            <Upload className="w-4 h-4" /> Import CSV
          </button>
          <button 
            onClick={() => setIsCreateOpen(true)}
            className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 rounded-md transition-colors text-sm font-medium shadow-sm"
          >
            <Plus className="w-4 h-4" /> Create Task
          </button>
        </div>
      </div>

      <div className="flex gap-2 bg-white p-3 rounded-lg border shadow-sm item-center">
        <div className="text-sm font-medium text-slate-700 mr-4 self-center px-2">Queue Controls:</div>
        <button onClick={handleStartNext} className="flex items-center gap-2 bg-blue-50 text-blue-700 hover:bg-blue-100 px-3 py-1.5 rounded text-sm transition-colors border border-blue-200 shadow-sm">
          <Play className="w-4 h-4" /> Start Next
        </button>
        <button onClick={handleStartAll} className="flex items-center gap-2 bg-green-50 text-green-700 hover:bg-green-100 px-3 py-1.5 rounded text-sm transition-colors border border-green-200 shadow-sm">
          <Play className="w-4 h-4" /> Start All
        </button>
        <button onClick={() => toast("Stop Queue not supported yet", { icon: "ℹ️"})} className="flex items-center gap-2 bg-red-50 text-red-700 hover:bg-red-100 px-3 py-1.5 rounded text-sm transition-colors border border-red-200 shadow-sm">
          <Square className="w-4 h-4" /> Stop Queue
        </button>
      </div>

      <DataTable 
        columns={columns} 
        data={data || []} 
        isLoading={isLoading} 
        onRowClick={(task) => navigate(`/tasks/${task.id}`)}
      />

      {isCreateOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold">Create Task (Stub)</h2>
              <button onClick={() => setIsCreateOpen(false)}><X className="w-5 h-5 text-gray-500" /></button>
            </div>
            <p className="text-sm text-gray-600 mb-4">This form is a placeholder as requested in TЗ.</p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setIsCreateOpen(false)} className="px-4 py-2 border rounded text-sm">Cancel</button>
              <button onClick={() => { setIsCreateOpen(false); toast("Task created", { icon: "✅" }) }} className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">Save</button>
             </div>
          </div>
        </div>
      )}

      {isImportOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold">Import Tasks (Stub)</h2>
              <button onClick={() => setIsImportOpen(false)}><X className="w-5 h-5 text-gray-500" /></button>
            </div>
            <p className="text-sm text-gray-600 mb-4">File upload stub placeholder as requested in TЗ.</p>
            <div className="mt-4 border-2 border-dashed border-gray-300 rounded p-8 text-center text-gray-500 flex flex-col items-center">
               <Upload className="w-8 h-8 mb-2" />
               Upload CSV
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setIsImportOpen(false)} className="px-4 py-2 border rounded text-sm">Cancel</button>
              <button onClick={() => { setIsImportOpen(false); toast("File uploaded", { icon: "✅" }) }} className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">Import</button>
             </div>
          </div>
        </div>
      )}
    </div>
  );
}
