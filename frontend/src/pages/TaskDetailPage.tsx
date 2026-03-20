import { useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { tasksApi } from "@/api/tasks";
import { Task } from "@/types/task";
import StatusBadge from "@/components/common/StatusBadge";
import StepMonitor from "@/components/tasks/StepMonitor";
import SerpViewer from "@/components/tasks/SerpViewer";

export default function TaskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  // Fetch task details
  const { data: task, isLoading } = useQuery({
    queryKey: ["task", id],
    queryFn: () => tasksApi.getOne(id!),
    enabled: !!id,
    refetchInterval: (query) => query.state.data?.status === "processing" ? 5000 : false,
  });

  const handleForceAction = async (action: "complete" | "fail") => {
    try {
      if (!id) return;
      await tasksApi.forceStatus(id, action);
      toast.success(`Task forced to ${action === 'complete' ? 'Completed' : 'Failed'}`);
      queryClient.invalidateQueries({ queryKey: ["task", id] });
    } catch {
      toast.error("Failed to force action. Check console.");
    }
  };

  if (isLoading) return <div className="p-6 text-slate-500">Loading task...</div>;
  if (!task) return <div className="p-6 text-red-500">Task not found</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Task: {task.main_keyword}</h1>
          <div className="text-sm text-slate-500 mt-1">ID: {task.id}</div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex gap-2 bg-slate-50 px-3 py-1.5 rounded-md border text-sm">
             <button 
               onClick={() => handleForceAction("complete")}
               className="text-emerald-700 hover:text-emerald-800 font-medium hover:underline"
             >
               Force Complete
             </button>
             <span className="text-slate-300">|</span>
             <button 
               onClick={() => handleForceAction("fail")}
               className="text-red-700 hover:text-red-800 font-medium hover:underline"
             >
               Force Fail
             </button>
          </div>
          <StatusBadge status={task.status} />
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 space-y-6">
          <div className="bg-white border rounded-xl shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-6 flex items-center gap-2">Pipeline Execution</h2>
            <StepMonitor taskId={task.id} isActive={task.status === "processing"} />
          </div>
          
          <div className="bg-white border rounded-xl shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-4">SERP Data</h2>
            <SerpViewer taskId={task.id} />
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white border rounded-xl shadow-sm p-6">
            <h2 className="text-lg font-semibold border-b pb-4 mb-4">Task Details</h2>
            <ul className="space-y-4 text-sm">
              <li className="flex justify-between items-center">
                <span className="text-slate-500">Country:</span>
                <span className="font-medium bg-slate-100 px-2 py-1 rounded">{task.country}</span>
              </li>
              <li className="flex justify-between items-center">
                <span className="text-slate-500">Language:</span>
                <span className="font-medium bg-slate-100 px-2 py-1 rounded">{task.language}</span>
              </li>
              <li className="flex justify-between items-center">
                <span className="text-slate-500">Cost:</span>
                <span className="font-medium text-emerald-600 font-mono">${task.total_cost?.toFixed(4) || "0.0000"}</span>
              </li>
              <li className="flex justify-between items-center">
                <span className="text-slate-500">Created:</span>
                <span className="font-medium text-slate-700">{new Date(task.created_at).toLocaleString()}</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
