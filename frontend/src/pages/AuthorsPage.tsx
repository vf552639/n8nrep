import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import api from "@/api/client";
import { Author } from "@/types/author";
import DataTable from "@/components/common/DataTable";
import { Plus } from "lucide-react";

export default function AuthorsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["authors"],
    queryFn: async () => {
      const res = await api.get<Author[]>("/authors");
      return res.data;
    },
  });

  const columns = [
    { key: "author", header: "Author Name", render: (a: Author) => <span className="font-semibold text-slate-800">{a.author}</span> },
    { key: "country", header: "Country", render: (a: Author) => <span className="bg-slate-100 px-2 py-0.5 rounded text-sm">{a.country}</span> },
    { key: "language", header: "Language", render: (a: Author) => <span className="bg-slate-100 px-2 py-0.5 rounded text-sm">{a.language}</span> },
    { key: "model", header: "Model", render: (a: Author) => <span className="text-amber-700 bg-amber-50 px-2 py-0.5 rounded text-xs font-mono">{a.model}</span> },
    { 
      key: "exclude_words", 
      header: "Exclude Words", 
      render: (a: Author) => (
        <span className="text-xs text-slate-500 max-w-xs truncate block" title={a.exclude_words}>
          {a.exclude_words || "None"}
        </span>
      )
    },
  ];

  const [isCreateOpen, setIsCreateOpen] = useState(false);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center bg-white p-4 rounded-lg shadow-sm border">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Virtual Authors</h1>
          <p className="text-sm text-slate-500 mt-1">Manage author personas and their specific exclude words.</p>
        </div>
        <button 
          onClick={() => setIsCreateOpen(true)}
          className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 rounded-md transition-colors text-sm font-medium shadow-sm"
        >
          <Plus className="w-4 h-4" /> Add Author
        </button>
      </div>

      <DataTable 
        columns={columns} 
        data={data || []} 
        isLoading={isLoading} 
      />

      {/* Add Author Modal Stub */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6">
            <h2 className="text-xl font-bold mb-4 text-slate-900">Add New Author</h2>
            <div className="space-y-4">
               <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Author Name</label>
                  <input type="text" className="w-full border rounded-md px-3 py-2 text-sm" placeholder="e.g. John Doe, Editor" />
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
                  <label className="block text-sm font-medium text-slate-700 mb-1">Model</label>
                  <input type="text" className="w-full border rounded-md px-3 py-2 text-sm" placeholder="gpt-4o-mini" />
               </div>
               <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Exclude Words (comma separated)</label>
                  <textarea rows={3} className="w-full border rounded-md px-3 py-2 text-sm" placeholder="word1, word2, phrase 3"></textarea>
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
                Save Author
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
