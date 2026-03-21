import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { sitesApi } from "@/api/sites";
import { Site } from "@/types/site";
import { ReactTable } from "@/components/common/ReactTable";
import { Plus, Globe, X } from "lucide-react";

export default function SitesPage() {
  const navigate = useNavigate();
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const { data: sites, isLoading } = useQuery({
    queryKey: ["sites"],
    queryFn: async () => {
      return sitesApi.getAll();
    },
  });

  const columns = [
    { 
      accessorKey: "name", 
      header: "Site Name", 
      cell: ({ row }: any) => <div className="font-semibold text-slate-800 flex items-center gap-2"><Globe className="w-4 h-4 text-slate-400"/> {row.original.name}</div> 
    },
    { 
      accessorKey: "domain", 
      header: "Domain", 
      cell: ({ row }: any) => <span className="text-blue-600 font-medium hover:underline cursor-pointer">{row.original.domain}</span> 
    },
    { accessorKey: "country", header: "Country" },
    { accessorKey: "language", header: "Language" },
    { 
      accessorKey: "is_active", 
      header: "Status", 
      cell: ({ row }: any) => (
        <span className={`px-2 py-1 rounded text-xs font-semibold ${row.original.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-800'}`}>
          {row.original.is_active ? "Active" : "Inactive"}
        </span>
      ) 
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-5 rounded-xl border shadow-sm">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 border-l-4 border-blue-500 pl-3">Sites Management</h1>
          <p className="text-sm text-slate-500 mt-1 pl-4">Manage target websites and their HTML templates.</p>
        </div>
        <button 
          onClick={() => setIsCreateOpen(true)}
          className="flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors text-sm font-medium shadow-sm w-full sm:w-auto"
        >
          <Plus className="w-4 h-4" /> Add Site
        </button>
      </div>

      <ReactTable 
        columns={columns as any} 
        data={sites || []} 
        isLoading={isLoading} 
        onRowClick={(site: any) => navigate(`/sites/${site.id}`)}
      />

      {isCreateOpen && (
        <CreateSiteModal onClose={() => setIsCreateOpen(false)} />
      )}
    </div>
  );
}

function CreateSiteModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState({
    name: "",
    domain: "",
    country: "US",
    language: "en"
  });

  const mutation = useMutation({
    mutationFn: (data: Partial<Site>) => sitesApi.create(data),
    onSuccess: () => {
      toast.success("Site created successfully");
      queryClient.invalidateQueries({ queryKey: ["sites"] });
      onClose();
    },
    onError: () => toast.error("Failed to create site")
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name || !formData.domain) {
      toast.error("Name and Domain are required");
      return;
    }
    mutation.mutate(formData);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden">
        <div className="px-6 py-4 border-b bg-slate-50 flex justify-between items-center">
            <h2 className="text-lg font-bold text-slate-900">Add New Site</h2>
            <button onClick={onClose} className="p-1 hover:bg-slate-200 rounded text-slate-500"><X className="w-5 h-5"/></button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
           <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Site Name *</label>
              <input 
                required
                type="text" 
                value={formData.name}
                onChange={e => setFormData({...formData, name: e.target.value})}
                className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm" 
                placeholder="e.g. My Awesome Blog" 
              />
           </div>
           <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Domain *</label>
              <input 
                required
                type="text" 
                value={formData.domain}
                onChange={e => setFormData({...formData, domain: e.target.value})}
                className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm" 
                placeholder="e.g. awesome-blog.com" 
              />
           </div>
           <div className="grid grid-cols-2 gap-4">
             <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Country</label>
                <input 
                  type="text" 
                  value={formData.country}
                  onChange={e => setFormData({...formData, country: e.target.value})}
                  className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm uppercase" 
                />
             </div>
             <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Language</label>
                <input 
                  type="text" 
                  value={formData.language}
                  onChange={e => setFormData({...formData, language: e.target.value})}
                  className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm lowercase" 
                />
             </div>
           </div>
           <div className="flex justify-end gap-3 mt-8 pt-4 border-t">
             <button 
               type="button"
               onClick={onClose}
               className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg text-sm font-medium transition-colors"
             >
               Cancel
             </button>
             <button 
               type="submit"
               disabled={mutation.isPending}
               className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium transition-colors shadow-sm disabled:opacity-50"
             >
               {mutation.isPending ? "Saving..." : "Save Site"}
             </button>
           </div>
        </form>
      </div>
    </div>
  );
}
