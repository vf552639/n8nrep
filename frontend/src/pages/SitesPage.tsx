import { useQuery } from "@tanstack/react-query";
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

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center bg-white p-4 rounded-lg shadow-sm border">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Sites Management</h1>
          <p className="text-sm text-slate-500 mt-1">Manage target websites and their HTML templates.</p>
        </div>
        <button className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md transition-colors text-sm font-medium shadow-sm">
          <Plus className="w-4 h-4" /> Add Site
        </button>
      </div>

      <DataTable 
        columns={columns} 
        data={data || []} 
        isLoading={isLoading} 
      />
    </div>
  );
}
