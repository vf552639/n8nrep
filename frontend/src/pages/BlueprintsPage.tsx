import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import toast from "react-hot-toast";
import { blueprintsApi } from "@/api/blueprints";
import { Blueprint } from "@/types/blueprint";
import { ReactTable } from "@/components/common/ReactTable";
import { Plus, LayoutTemplate, X } from "lucide-react";

export default function BlueprintsPage() {
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const { data: blueprints, isLoading } = useQuery({
    queryKey: ["blueprints"],
    queryFn: async () => {
      return blueprintsApi.getAll({ limit: 1000 });
    },
  });

  const columns = [
    { 
      accessorKey: "name", 
      header: "Blueprint Name", 
      cell: ({ row }: any) => <div className="font-semibold text-slate-800 flex items-center gap-2"><LayoutTemplate className="w-4 h-4 text-slate-400"/> {row.original.name}</div> 
    },
    { 
      accessorKey: "description", 
      header: "Description", 
      cell: ({ row }: any) => <span className="text-slate-500">{row.original.description || "No description"}</span> 
    },
    { 
      accessorKey: "created_at", 
      header: "Created At", 
      cell: ({ row }: any) => <span className="text-sm text-slate-500">{new Date(row.original.created_at).toLocaleDateString()}</span> 
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-5 rounded-xl border shadow-sm">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 border-l-4 border-purple-500 pl-3">Site Blueprints</h1>
          <p className="text-sm text-slate-500 mt-1 pl-4">Manage architectural structures for generating entire websites.</p>
        </div>
        <button 
          onClick={() => setIsCreateOpen(true)}
          className="flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors text-sm font-medium shadow-sm w-full sm:w-auto"
        >
          <Plus className="w-4 h-4" /> Create Blueprint
        </button>
      </div>

      <ReactTable 
        columns={columns as any} 
        data={blueprints || []} 
        isLoading={isLoading} 
      />

      {isCreateOpen && (
        <CreateBlueprintModal onClose={() => setIsCreateOpen(false)} />
      )}
    </div>
  );
}

function CreateBlueprintModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState({
    name: "",
    description: "",
  });

  const mutation = useMutation({
    mutationFn: (data: Partial<Blueprint>) => blueprintsApi.create(data),
    onSuccess: () => {
      toast.success("Blueprint created successfully");
      queryClient.invalidateQueries({ queryKey: ["blueprints"] });
      onClose();
    },
    onError: () => toast.error("Failed to create blueprint")
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name) {
      toast.error("Blueprint Name is required");
      return;
    }
    mutation.mutate(formData);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden">
        <div className="px-6 py-4 border-b bg-slate-50 flex justify-between items-center">
            <h2 className="text-lg font-bold text-slate-900">Create New Blueprint</h2>
            <button onClick={onClose} className="p-1 hover:bg-slate-200 rounded text-slate-500"><X className="w-5 h-5"/></button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
           <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Blueprint Name *</label>
              <input 
                required
                type="text" 
                value={formData.name}
                onChange={e => setFormData({...formData, name: e.target.value})}
                className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm" 
                placeholder="e.g. Finance Blog Silo Structure" 
              />
           </div>
           <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
              <textarea 
                rows={3} 
                value={formData.description}
                onChange={e => setFormData({...formData, description: e.target.value})}
                className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm" 
                placeholder="Optional description"
              />
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
               {mutation.isPending ? "Creating..." : "Create Blueprint"}
             </button>
           </div>
        </form>
      </div>
    </div>
  );
}
