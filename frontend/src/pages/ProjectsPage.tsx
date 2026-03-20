import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import api from "@/api/client";
import { Project } from "@/types/project";
import { PaginatedList } from "@/types/common";
import DataTable from "@/components/common/DataTable";
import StatusBadge from "@/components/common/StatusBadge";
import { Plus } from "lucide-react";

export default function ProjectsPage() {
  const navigate = useNavigate();

  const { data, isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: async () => {
      const res = await api.get<PaginatedList<Project>>("/projects", {
        params: { limit: 50, skip: 0 }
      });
      return res.data;
    },
  });

  const columns = [
    { key: "name", header: "Project Name", render: (p: Project) => <span className="font-medium text-slate-800">{p.name}</span> },
    { key: "seed_keyword", header: "Seed Keyword", render: (p: Project) => <span className="text-slate-600 bg-slate-50 px-2 py-0.5 rounded border leading-tight">{p.seed_keyword}</span> },
    { key: "status", header: "Status", render: (p: Project) => <StatusBadge status={p.status} /> },
    { 
      key: "progress", 
      header: "Progress",
      render: (p: Project) => (
        <div className="flex items-center gap-3 w-full max-w-[180px]">
          <div className="w-full bg-slate-200 rounded-full h-2.5 overflow-hidden">
            <div className={`h-2.5 rounded-full ${p.progress === 100 ? 'bg-emerald-500' : 'bg-blue-500'}`} style={{ width: `${p.progress || 0}%` }}></div>
          </div>
          <span className="text-xs font-semibold text-slate-600 w-8 text-right">{Math.round(p.progress || 0)}%</span>
        </div>
      )
    },
    { key: "created_at", header: "Date", render: (p: Project) => <span className="text-slate-500 text-sm whitespace-nowrap">{new Date(p.created_at).toLocaleDateString()}</span> },
  ];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center bg-white p-4 rounded-lg shadow-sm border">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Generative Projects</h1>
          <p className="text-sm text-slate-500 mt-1">Manage bulk generation of entire sites from blueprints.</p>
        </div>
        <button className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 rounded-md transition-colors text-sm font-medium shadow-sm">
          <Plus className="w-4 h-4" /> New Project
        </button>
      </div>

      <DataTable 
        columns={columns} 
        data={data?.items || []} 
        isLoading={isLoading} 
        onRowClick={(p) => navigate(`/projects/${p.id}`)}
      />
    </div>
  );
}
