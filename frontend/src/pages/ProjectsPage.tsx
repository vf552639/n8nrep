import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import api from "@/api/client";
import { Project } from "@/types/project";
import DataTable from "@/components/common/DataTable";
import StatusBadge from "@/components/common/StatusBadge";
import { Plus } from "lucide-react";

export default function ProjectsPage() {
  const navigate = useNavigate();
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: async () => {
      const res = await api.get<Project[]>("/projects", {
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
        <button 
          onClick={() => setIsCreateOpen(true)}
          className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 rounded-md transition-colors text-sm font-medium shadow-sm"
        >
          <Plus className="w-4 h-4" /> New Project
        </button>
      </div>

      <DataTable 
        columns={columns} 
        data={data || []} 
        isLoading={isLoading} 
        onRowClick={(p) => navigate(`/projects/${p.id}`)}
      />

      {isCreateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6">
            <h2 className="text-xl font-bold mb-4 text-slate-900">Create Generative Project</h2>
            <div className="space-y-4 max-h-[60vh] overflow-y-auto p-1">
               <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Project Name</label>
                  <input type="text" className="w-full border rounded-md px-3 py-2 text-sm" placeholder="e.g. Finance Hub" />
               </div>
               <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Blueprint ID</label>
                  <input type="text" className="w-full border rounded-md px-3 py-2 text-sm" placeholder="Select blueprint..." />
               </div>
               <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Seed Keyword</label>
                  <input type="text" className="w-full border rounded-md px-3 py-2 text-sm" placeholder="e.g. Best Credit Cards" />
               </div>
               <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Target Site / Domain</label>
                  <input type="text" className="w-full border rounded-md px-3 py-2 text-sm" placeholder="financehub.com" />
               </div>
               <div className="grid grid-cols-2 gap-4">
                 <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Country</label>
                    <input type="text" className="w-full border rounded-md px-3 py-2 text-sm" placeholder="us" />
                 </div>
                 <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Language</label>
                    <input type="text" className="w-full border rounded-md px-3 py-2 text-sm" placeholder="en" />
                 </div>
               </div>
               <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Author ID (Optional)</label>
                  <input type="text" className="w-full border rounded-md px-3 py-2 text-sm" placeholder="Auto-assigns based on country/lang if empty" />
               </div>
            </div>
            <div className="flex justify-end gap-3 mt-8">
              <button 
                onClick={() => setIsCreateOpen(false)}
                className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-md text-sm font-medium"
              >
                Cancel
              </button>
              <button 
                onClick={() => setIsCreateOpen(false)}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium"
              >
                Start Project
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
