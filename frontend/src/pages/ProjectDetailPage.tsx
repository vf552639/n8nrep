import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import api from "@/api/client";
import { Project } from "@/types/project";
import StatusBadge from "@/components/common/StatusBadge";
import { Download, Pause, Play } from "lucide-react";

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();

  const { data: project, isLoading } = useQuery({
    queryKey: ["project", id],
    queryFn: async () => {
      const res = await api.get<Project>(`/projects/${id}`);
      return res.data;
    },
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
            <button className="flex items-center gap-2 bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100 px-3 py-1.5 rounded-md text-sm font-medium transition-colors shadow-sm">
              <Pause className="w-4 h-4" /> Stop Project
            </button>
          )}
          {project.status === "stopped" && (
            <button className="flex items-center gap-2 bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 px-3 py-1.5 rounded-md text-sm font-medium transition-colors shadow-sm">
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

      <div className="bg-white border rounded-xl shadow-sm p-6 overflow-hidden min-h-[400px]">
        <h2 className="text-lg font-semibold text-slate-800 mb-6 border-b pb-4">Project Tasks Execution</h2>
        <div className="text-center text-slate-500 mt-16 bg-slate-50 border border-dashed rounded-lg p-10 max-w-lg mx-auto">
            <Play className="w-10 h-10 mx-auto text-slate-300 mb-4" />
            <div className="font-medium text-slate-700">Task List Monitor Details</div>
            <p className="text-sm mt-1 text-slate-500">Each page task will display progress inline here.</p>
        </div>
      </div>
    </div>
  );
}
