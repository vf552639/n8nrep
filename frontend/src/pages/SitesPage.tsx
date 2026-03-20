import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/api/client";
import { Site } from "@/types/site";
import DataTable from "@/components/common/DataTable";
import { Plus } from "lucide-react";

export default function SitesPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["sites"],
    queryFn: async () => {
      const res = await api.get<Site[]>("/sites");
      return res.data;
    },
  });

  const columns = [
    { key: "name", header: "Site Name", render: (s: Site) => <span className="font-medium text-slate-800">{s.name}</span> },
    { key: "domain", header: "Domain", render: (s: Site) => <span className="text-blue-600 hover:underline">{s.domain}</span> },
    { key: "country", header: "Country" },
    { key: "language", header: "Language" },
    { 
      key: "is_active", 
      header: "Status", 
      render: (s: Site) => (
        <span className={`px-2 py-1 rounded text-xs font-semibold ${s.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-800'}`}>
          {s.is_active ? "Active" : "Inactive"}
        </span>
      ) 
    },
  ];

  const navigate = useNavigate();
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center bg-white p-4 rounded-lg shadow-sm border">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Sites Management</h1>
          <p className="text-sm text-slate-500 mt-1">Manage target websites and their HTML templates.</p>
        </div>
        <button 
          onClick={() => setIsCreateOpen(true)}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md transition-colors text-sm font-medium shadow-sm"
        >
          <Plus className="w-4 h-4" /> Add Site
        </button>
      </div>

      <DataTable 
        columns={columns} 
        data={data || []} 
        isLoading={isLoading} 
        onRowClick={(site) => navigate(`/sites/${site.id}`)}
      />

      {/* Add Site Modal Stub */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
            <h2 className="text-xl font-bold mb-4 text-slate-900">Add New Site</h2>
            <div className="space-y-4">
               <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Site Name</label>
                  <input type="text" className="w-full border rounded-md px-3 py-2 text-sm" placeholder="e.g. My Awesome Blog" />
               </div>
               <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Domain</label>
                  <input type="text" className="w-full border rounded-md px-3 py-2 text-sm" placeholder="e.g. awesome-blog.com" />
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
                Save Site
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
