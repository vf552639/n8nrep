import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { projectsApi } from "@/api/projects";
import { sitesApi } from "@/api/sites";
import { blueprintsApi } from "@/api/blueprints";
import { Project } from "@/types/project";
import { ReactTable } from "@/components/common/ReactTable";
import StatusBadge from "@/components/common/StatusBadge";
import { Plus, FolderGit2, X } from "lucide-react";

export default function ProjectsPage() {
  const navigate = useNavigate();
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const { data: projects, isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: async () => projectsApi.getAll({ limit: 100 }),
  });

  const columns = [
    { 
      accessorKey: "name", 
      header: "Project Name", 
      cell: ({ row }: any) => <div className="font-semibold text-slate-800 flex items-center gap-2"><FolderGit2 className="w-4 h-4 text-slate-400"/>{row.original.name}</div> 
    },
    { 
      accessorKey: "seed_keyword", 
      header: "Seed Keyword", 
      cell: ({ row }: any) => <span className="text-slate-600 bg-slate-50 px-2 py-0.5 rounded border leading-tight">{row.original.seed_keyword}</span> 
    },
    { 
      accessorKey: "status", 
      header: "Status", 
      cell: ({ row }: any) => <StatusBadge status={row.original.status} /> 
    },
    { 
      accessorKey: "progress", 
      header: "Progress",
      cell: ({ row }: any) => {
        const p = row.original;
        return (
          <div className="flex items-center gap-3 w-full max-w-[180px]">
            <div className="w-full bg-slate-200 rounded-full h-2.5 overflow-hidden">
              <div className={`h-2.5 rounded-full border-r border-black/10 ${p.progress === 100 ? 'bg-emerald-500' : 'bg-blue-500'}`} style={{ width: `${p.progress || 0}%` }}></div>
            </div>
            <span className="text-xs font-semibold text-slate-600 w-8 text-right">{Math.round(p.progress || 0)}%</span>
          </div>
        )
      }
    },
    { 
      accessorKey: "created_at", 
      header: "Date", 
      cell: ({ row }: any) => <span className="text-slate-500 text-sm whitespace-nowrap">{new Date(row.original.created_at).toLocaleDateString()}</span> 
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-5 rounded-xl border shadow-sm">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 border-l-4 border-slate-700 pl-3">Generative Projects</h1>
          <p className="text-sm text-slate-500 mt-1 pl-4">Manage bulk generation of entire sites from blueprints.</p>
        </div>
        <button 
          onClick={() => setIsCreateOpen(true)}
          className="flex items-center justify-center gap-2 bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 rounded-lg transition-colors text-sm font-medium shadow-sm w-full sm:w-auto"
        >
          <Plus className="w-4 h-4" /> New Project
        </button>
      </div>

      <ReactTable 
        columns={columns as any} 
        data={projects || []} 
        isLoading={isLoading} 
        onRowClick={(p: any) => navigate(`/projects/${p.id}`)}
      />

      {isCreateOpen && (
        <CreateProjectModal onClose={() => setIsCreateOpen(false)} />
      )}
    </div>
  );
}

function CreateProjectModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState({
    name: "",
    blueprint_id: "",
    site_id: "",
    seed_keyword: "",
    country: "US",
    language: "en",
    author_id: ""
  });

  const { data: blueprints } = useQuery({
    queryKey: ["blueprints"],
    queryFn: async () => blueprintsApi.getAll({ limit: 100 }),
  });

  const { data: sites } = useQuery({
    queryKey: ["sites"],
    queryFn: async () => sitesApi.getAll({ limit: 100 }),
  });

  const mutation = useMutation({
    mutationFn: (data: Partial<Project>) => projectsApi.create(data),
    onSuccess: () => {
      toast.success("Project started successfully");
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      onClose();
    },
    onError: () => toast.error("Failed to start project")
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name || !formData.blueprint_id || !formData.site_id || !formData.seed_keyword) {
      toast.error("Please fill in all required fields (Name, Blueprint, Site, Seed Keyword)");
      return;
    }
    const payload: Partial<Project> = { ...formData };
    if (!payload.author_id) delete payload.author_id;
    mutation.mutate(payload);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg overflow-hidden flex flex-col max-h-[90vh]">
        <div className="px-6 py-4 border-b bg-slate-50 flex justify-between items-center shrink-0">
            <h2 className="text-lg font-bold text-slate-900">Create Generative Project</h2>
            <button onClick={onClose} className="p-1 hover:bg-slate-200 rounded text-slate-500"><X className="w-5 h-5"/></button>
        </div>
        <div className="flex-1 overflow-y-auto p-6">
            <form id="create-project-form" onSubmit={handleSubmit} className="space-y-4">
               <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Project Name *</label>
                  <input 
                    required type="text" 
                    value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})}
                    className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm" 
                    placeholder="e.g. Finance Hub" 
                  />
               </div>
               <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Blueprint *</label>
                  <select 
                    required value={formData.blueprint_id} onChange={e => setFormData({...formData, blueprint_id: e.target.value})}
                    className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm bg-white"
                  >
                    <option value="" disabled>Select blueprint...</option>
                    {blueprints?.map(bp => <option key={bp.id} value={bp.id}>{bp.name}</option>)}
                  </select>
               </div>
               <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Target Site *</label>
                  <select 
                    required value={formData.site_id} onChange={e => setFormData({...formData, site_id: e.target.value})}
                    className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm bg-white"
                  >
                    <option value="" disabled>Select target site...</option>
                    {sites?.map(s => <option key={s.id} value={s.id}>{s.name} ({s.domain})</option>)}
                  </select>
               </div>
               <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Seed Keyword *</label>
                  <input 
                    required type="text" 
                    value={formData.seed_keyword} onChange={e => setFormData({...formData, seed_keyword: e.target.value})}
                    className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm" 
                    placeholder="e.g. Best Credit Cards" 
                  />
               </div>
               <div className="grid grid-cols-2 gap-4">
                 <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Country</label>
                    <input 
                      type="text" 
                      value={formData.country} onChange={e => setFormData({...formData, country: e.target.value})}
                      className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm uppercase" 
                    />
                 </div>
                 <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Language</label>
                    <input 
                      type="text" 
                      value={formData.language} onChange={e => setFormData({...formData, language: e.target.value})}
                      className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm lowercase" 
                    />
                 </div>
               </div>
               <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Author ID (Optional)</label>
                  <input 
                    type="text" 
                    value={formData.author_id} onChange={e => setFormData({...formData, author_id: e.target.value})}
                    className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm" 
                    placeholder="Auto-assigns based on country/lang if empty" 
                  />
               </div>
            </form>
        </div>
        <div className="flex justify-end gap-3 px-6 py-4 border-t bg-slate-50 shrink-0">
          <button 
            type="button" onClick={onClose}
            className="px-4 py-2 text-slate-600 hover:bg-slate-200 rounded-lg text-sm font-medium transition-colors"
          >
            Cancel
          </button>
          <button 
            type="submit" form="create-project-form"
            disabled={mutation.isPending}
            className="px-4 py-2 bg-slate-900 text-white rounded-lg hover:bg-slate-800 text-sm font-medium transition-colors shadow-sm disabled:opacity-50"
          >
            {mutation.isPending ? "Starting..." : "Start Project"}
          </button>
        </div>
      </div>
    </div>
  );
}
