import { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { tasksApi } from "@/api/tasks";
import StatusBadge from "@/components/common/StatusBadge";
import StepMonitor from "@/components/tasks/StepMonitor";
import { Info, XCircle } from "lucide-react";

type LogEntry = {
  ts?: string;
  msg?: string;
  level?: string;
  step?: string | null;
};

export default function TaskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState("pipeline");

  const { data: task, isLoading } = useQuery({
    queryKey: ["task", id],
    queryFn: () => tasksApi.getOne(id!),
    enabled: !!id,
    refetchInterval: (query) => (query.state.data?.status === "processing" ? 5000 : false),
  });

  const handleForceAction = async (action: "complete" | "fail") => {
    try {
      if (!id) return;
      await tasksApi.forceStatus(id, action);
      toast.success(`Task forced to ${action === "complete" ? "Completed" : "Failed"}`);
      queryClient.invalidateQueries({ queryKey: ["task", id] });
    } catch {
      toast.error("Failed to force action. Check console.");
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center p-6 text-slate-500">Loading task details...</div>
    );
  }
  if (!task) return <div className="p-6 text-red-500">Task not found</div>;

  const tabs = [
    { id: "pipeline", label: "Pipeline Execution" },
    { id: "logs", label: "Execution Logs" },
  ];

  const logs: LogEntry[] = Array.isArray(task.logs) ? task.logs : [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Task: {task.main_keyword}</h1>
          <div className="mt-1 font-mono text-sm text-slate-500">ID: {task.id}</div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex gap-2 rounded-md border bg-slate-50 px-3 py-1.5 text-sm">
            <button
              type="button"
              onClick={() => handleForceAction("complete")}
              className="flex items-center gap-1 font-medium text-emerald-700 hover:text-emerald-800 hover:underline"
            >
              Force Complete
            </button>
            <span className="text-slate-300">|</span>
            <button
              type="button"
              onClick={() => handleForceAction("fail")}
              className="flex items-center gap-1 font-medium text-red-700 hover:text-red-800 hover:underline"
            >
              Force Fail
            </button>
          </div>
          <StatusBadge status={task.status} />
        </div>
      </div>

      <div className="mt-4 flex gap-2 overflow-x-auto border-b">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`whitespace-nowrap border-b-2 px-4 pb-3 text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? "border-blue-600 text-blue-600"
                : "rounded-t-lg border-transparent text-slate-500 hover:bg-slate-50 hover:text-slate-800"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="space-y-6 xl:col-span-2">
          {activeTab === "pipeline" && (
            <div className="animate-in fade-in slide-in-from-bottom-2 rounded-xl border bg-white p-6 shadow-sm duration-300">
              <StepMonitor taskId={task.id} isActive={task.status === "processing"} />
            </div>
          )}

          {activeTab === "logs" && (
            <div className="animate-in fade-in slide-in-from-bottom-2 rounded-xl border bg-white p-6 shadow-sm duration-300">
              <h2 className="mb-4 text-lg font-semibold text-slate-800">Task execution logs</h2>
              <div className="h-[500px] overflow-auto rounded-lg bg-[#1e1e1e] p-4 font-mono text-sm">
                {logs.length > 0 ? (
                  logs.map((log, i) => {
                    const lvl = (log.level || "info").toLowerCase();
                    const isErr = lvl === "error";
                    return (
                      <div key={i} className="mb-1.5 flex flex-wrap gap-x-2 leading-relaxed">
                        <span className="shrink-0 text-slate-500">
                          [{log.ts || ""}]
                        </span>
                        {lvl === "error" ? (
                          <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-400" aria-hidden />
                        ) : (
                          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-500" aria-hidden />
                        )}
                        {log.step && (
                          <span className="rounded bg-slate-700 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-slate-200">
                            {log.step}
                          </span>
                        )}
                        <span
                          className={
                            isErr ? "text-red-300" : "text-slate-300"
                          }
                        >
                          {log.msg ?? ""}
                        </span>
                      </div>
                    );
                  })
                ) : (
                  <div className="italic text-slate-500">
                    No logs for this task yet. Logs are written as the pipeline runs.
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="space-y-6">
          <div className="rounded-xl border bg-white p-6 shadow-sm">
            <h2 className="mb-4 border-b pb-4 text-lg font-semibold text-slate-800">Task details</h2>
            <ul className="space-y-4 text-sm">
              <li className="flex items-center justify-between">
                <span className="text-slate-500">Country:</span>
                <span className="rounded bg-slate-100 px-2 py-1 font-medium">{task.country}</span>
              </li>
              <li className="flex items-center justify-between">
                <span className="text-slate-500">Language:</span>
                <span className="rounded bg-slate-100 px-2 py-1 font-medium">{task.language}</span>
              </li>
              <li className="flex items-center justify-between">
                <span className="text-slate-500">Cost:</span>
                <span className="font-mono font-medium text-emerald-600">
                  ${task.total_cost?.toFixed(4) || "0.0000"}
                </span>
              </li>
              <li className="flex items-center justify-between">
                <span className="text-slate-500">Created at:</span>
                <span className="font-medium text-slate-700">{new Date(task.created_at).toLocaleString()}</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
