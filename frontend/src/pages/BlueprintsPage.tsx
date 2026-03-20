import { useQuery } from "@tanstack/react-query";
import api from "@/api/client";
import { Blueprint } from "@/types/blueprint";
import DataTable from "@/components/common/DataTable";
import { Plus } from "lucide-react";

export default function BlueprintsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["blueprints"],
    queryFn: async () => {
      const res = await api.get<Blueprint[]>("/blueprints");
      return res.data;
    },
  });

  const columns = [
    { key: "name", header: "Blueprint Name", render: (b: Blueprint) => <span className="font-semibold text-slate-800">{b.name}</span> },
    { key: "description", header: "Description", render: (b: Blueprint) => <span className="text-slate-500">{b.description || "No description"}</span> },
    { key: "created_at", header: "Created At", render: (b: Blueprint) => <span className="text-sm">{new Date(b.created_at).toLocaleDateString()}</span> },
  ];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center bg-white p-4 rounded-lg shadow-sm border">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Site Blueprints</h1>
          <p className="text-sm text-slate-500 mt-1">Manage architectural structures for generating entire websites.</p>
        </div>
        <button className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md transition-colors text-sm font-medium shadow-sm">
          <Plus className="w-4 h-4" /> Create Blueprint
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
