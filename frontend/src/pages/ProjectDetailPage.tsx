import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import api from "@/api/client";
import { Project } from "@/types/project";
import StatusBadge from "@/components/common/StatusBadge";
import { Download, Pause, Play, CheckCircle2, CircleDashed, FileText, ChevronRight } from "lucide-react";

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const { data: project, isLoading } = useQuery({
    queryKey: ["project", id],
    queryFn: async () => {
      const res = await api.get<Project>(`/projects/${id}`);
      return res.data;
    },
    refetchInterval: (query) => {
      const p = query.state.data;
      if (p?.status === "generating" || p?.status === "pending") return 3000;
      return false;
    }
  });

  const actionMutation = useMutation({
    mutationFn: (action: "stop" | "resume") => api.post(`/projects/${id}/${action}`),
    onSuccess: (_, action) => {
      toast.success(`Project ${action === "stop" ? "stopped (waiting for current task)" : "resumed"}`);
      queryClient.invalidateQueries({ queryKey: ["project", id] });
    },
    onError: () => toast.error("Action failed")
  });

  if (isLoading) return <div className="p-6 text-slate-500">Loading project...</div>;
  if (!project) return <div className="p-6 text-red-500">Project not found</div>;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">{project.name}</h1>
          <div className="text-sm text-slate-500 mt-2 flex gap-4">
            <span className="flex items-center gap-1">Seed: <span className="font-semibold text-slate-700 bg-slate-100 px-2 rounded">{project.seed_keyword}</span></span>
            <span className="flex items-center gap-1">Target: <span className="font-medium">{project.target_site_id}</span></span>
          </div>
        </div>
        <div className="flex gap-2">
          {project.status === "generating" && (
            <button 
              onClick={() => actionMutation.mutate("stop")}
              disabled={actionMutation.isPending}
              className="flex items-center gap-2 bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100 px-3 py-1.5 rounded-md text-sm font-medium transition-colors shadow-sm disabled:opacity-70"
            >
              <Pause className="w-4 h-4" /> Stop Project
            </button>
          )}
          {project.status === "stopped" && (
            <button 
              onClick={() => actionMutation.mutate("resume")}
              disabled={actionMutation.isPending}
              className="flex items-center gap-2 bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 px-3 py-1.5 rounded-md text-sm font-medium transition-colors shadow-sm disabled:opacity-70"
            >
              <Play className="w-4 h-4" /> Resume
            </button>
          )}
          {project.status === "completed" && (
            <a 
              href={`${import.meta.env.VITE_API_URL || "http://localhost:8000/api"}/projects/${id}/download`}
              download
              className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-md text-sm font-medium shadow-sm transition-colors"
            >
              <Download className="w-4 h-4" /> Download ZIP
            </a>
          )}
        </div>
      </div>

      <div className="bg-white border p-6 rounded-xl shadow-sm">
        <div className="flex justify-between items-center mb-4">
           <h2 className="text-lg font-semibold text-slate-800">Overall Progress</h2>
           <StatusBadge status={project.status} />
        </div>
        <div className="w-full bg-slate-100 rounded-full h-4 relative overflow-hidden my-4 border shadow-inner">
          <div 
            className={`h-4 rounded-full transition-all duration-500 ${project.progress === 100 ? 'bg-emerald-500' : 'bg-blue-500'}`} 
            style={{ width: `${project.progress || 0}%` }}
          />
        </div>
        <div className="text-right text-sm font-bold text-slate-600">{Math.round(project.progress || 0)}% Complete</div>
      </div>

      <div className="bg-white border rounded-xl shadow-sm overflow-hidden min-h-[400px]">
        <div className="p-6 pb-4 border-b">
          <h2 className="text-lg font-semibold text-slate-800">Project Tasks Execution</h2>
        </div>
        
        {project.tasks && project.tasks.length > 0 ? (
          <div className="divide-y">
            {project.tasks.map((task, i) => (
              <div key={task.id} className="p-4 hover:bg-slate-50 transition-colors flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="flex-shrink-0 font-mono text-slate-400 text-sm">#{i + 1}</div>
                  <div className="flex items-center gap-2">
                     {task.status === 'completed' && <CheckCircle2 className="w-5 h-5 text-emerald-500" />}
                     {task.status === 'running' && <CircleDashed className="w-5 h-5 text-blue-500 animate-[spin_3s_linear_infinite]" />}
                     {task.status === 'pending' && <CircleDashed className="w-5 h-5 text-slate-300" />}
                     {task.status === 'failed' && <CircleDashed className="w-5 h-5 text-red-500" />}
                  </div>
                  <div>
                    <div className="font-medium text-slate-800 break-all">{task.main_keyword}</div>
                    <div className="text-xs text-slate-500 mt-0.5 flex gap-2">
                       <span className="bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200 uppercase tracking-tighter">{task.page_type}</span>
                       {task.current_step && <span className="bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded text-xs">{task.current_step}</span>}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-6">
                  <div className="text-sm font-medium text-slate-500">{Math.round(task.progress)}%</div>
                  <Link 
                    to={`/tasks/${task.id}`}
                    className="flex items-center justify-center p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-md transition-colors"
                    title="View Task Detail"
                  >
                    <ChevronRight className="w-5 h-5" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center text-slate-500 mt-16 bg-slate-50 border border-dashed rounded-lg p-10 max-w-lg mx-auto">
              <FileText className="w-10 h-10 mx-auto text-slate-300 mb-4" />
              <div className="font-medium text-slate-700">No tasks generated yet</div>
              <p className="text-sm mt-1 text-slate-500">Once the blueprint is parsed, tasks will populate here.</p>
          </div>
        )}
      </div>
    </div>
  );
}
