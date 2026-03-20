import { useQuery } from "@tanstack/react-query";
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

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center bg-white p-4 rounded-lg shadow-sm border">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Virtual Authors</h1>
          <p className="text-sm text-slate-500 mt-1">Manage author personas and their specific exclude words.</p>
        </div>
        <button className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 rounded-md transition-colors text-sm font-medium shadow-sm">
          <Plus className="w-4 h-4" /> Add Author
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
