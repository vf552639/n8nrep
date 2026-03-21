import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import toast from "react-hot-toast";
import { authorsApi } from "@/api/authors";
import { Author } from "@/types/author";
import { ReactTable } from "@/components/common/ReactTable";
import { Plus, User, X } from "lucide-react";

export default function AuthorsPage() {
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["authors"],
    queryFn: async () => {
      return authorsApi.getAll({ limit: 1000 });
    },
  });

  const columns = [
    { 
      accessorKey: "author", 
      header: "Author Name", 
      cell: ({ row }: any) => <div className="font-semibold text-slate-800 flex items-center gap-2"><User className="w-4 h-4 text-slate-400"/> {row.original.author}</div> 
    },
    { 
      accessorKey: "country", 
      header: "Country", 
      cell: ({ row }: any) => <span className="bg-slate-100 px-2 py-0.5 rounded text-sm uppercase">{row.original.country}</span> 
    },
    { 
      accessorKey: "language", 
      header: "Language", 
      cell: ({ row }: any) => <span className="bg-slate-100 px-2 py-0.5 rounded text-sm lowercase">{row.original.language}</span> 
    },
    { 
      accessorKey: "model", 
      header: "Model", 
      cell: ({ row }: any) => <span className="text-amber-700 bg-amber-50 px-2 py-0.5 rounded text-xs font-mono">{row.original.model}</span> 
    },
    { 
      accessorKey: "exclude_words", 
      header: "Exclude Words", 
      cell: ({ row }: any) => (
        <span className="text-xs text-slate-500 max-w-xs truncate block" title={row.original.exclude_words}>
          {row.original.exclude_words || "None"}
        </span>
      )
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-5 rounded-xl border shadow-sm">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 border-l-4 border-indigo-500 pl-3">Virtual Authors</h1>
          <p className="text-sm text-slate-500 mt-1 pl-4">Manage author personas and their specific generation settings.</p>
        </div>
        <button 
          onClick={() => setIsCreateOpen(true)}
          className="flex items-center justify-center gap-2 bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 rounded-lg transition-colors text-sm font-medium shadow-sm w-full sm:w-auto"
        >
          <Plus className="w-4 h-4" /> Add Author
        </button>
      </div>

      <ReactTable 
        columns={columns as any} 
        data={data || []} 
        isLoading={isLoading} 
      />

      {isCreateOpen && (
        <CreateAuthorModal onClose={() => setIsCreateOpen(false)} />
      )}
    </div>
  );
}

function CreateAuthorModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState({
    author: "",
    country: "US",
    language: "en",
    model: "gpt-4o-mini",
    exclude_words: ""
  });

  const mutation = useMutation({
    mutationFn: (data: Partial<Author>) => authorsApi.create(data),
    onSuccess: () => {
      toast.success("Author created successfully");
      queryClient.invalidateQueries({ queryKey: ["authors"] });
      onClose();
    },
    onError: () => toast.error("Failed to create author")
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.author) {
      toast.error("Author Name is required");
      return;
    }
    mutation.mutate(formData);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg overflow-hidden">
        <div className="px-6 py-4 border-b bg-slate-50 flex justify-between items-center">
            <h2 className="text-lg font-bold text-slate-900">Add New Author</h2>
            <button onClick={onClose} className="p-1 hover:bg-slate-200 rounded text-slate-500"><X className="w-5 h-5"/></button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
           <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Author Name *</label>
              <input 
                required
                type="text" 
                value={formData.author}
                onChange={e => setFormData({...formData, author: e.target.value})}
                className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm" 
                placeholder="e.g. John Doe, Editor" 
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
           <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Model</label>
              <input 
                type="text" 
                value={formData.model}
                onChange={e => setFormData({...formData, model: e.target.value})}
                className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm font-mono" 
                placeholder="gpt-4o-mini" 
              />
           </div>
           <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Exclude Words (comma separated)</label>
              <textarea 
                rows={3} 
                value={formData.exclude_words}
                onChange={e => setFormData({...formData, exclude_words: e.target.value})}
                className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm max-h-32" 
                placeholder="word1, word2, phrase 3"
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
               className="px-4 py-2 bg-slate-900 text-white rounded-lg hover:bg-slate-800 text-sm font-medium transition-colors shadow-sm disabled:opacity-50"
             >
               {mutation.isPending ? "Saving..." : "Save Author"}
             </button>
           </div>
        </form>
      </div>
    </div>
  );
}
