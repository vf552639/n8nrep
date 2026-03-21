import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import api from "@/api/client";
import { Article } from "@/types/article";
import { ReactTable } from "@/components/common/ReactTable";

export default function ArticlesPage() {
  const navigate = useNavigate();

  const { data, isLoading } = useQuery({
    queryKey: ["articles"],
    queryFn: async () => {
      const res = await api.get<Article[]>("/articles", {
        params: { limit: 1000 },
      });
      return res.data;
    },
  });

  const columns = [
    { 
      accessorKey: "title", 
      header: "Title", 
      cell: ({ row }: any) => <div className="max-w-xs truncate font-medium text-slate-800" title={row.original.title}>{row.original.title || "Untitled Article"}</div> 
    },
    { 
      accessorKey: "word_count", 
      header: "Words", 
      cell: ({ row }: any) => <span className="text-slate-600 font-mono">{row.original.word_count?.toLocaleString() || 0}</span> 
    },
    { 
      accessorKey: "fact_check_status", 
      header: "Fact Check", 
      cell: ({ row }: any) => {
        const raw = (row.original.fact_check_status || "").toString().toLowerCase();
        if (!raw) return <span className="text-slate-400 text-xs">N/A</span>;
        const label =
          raw === "pass" ? "pass" : raw === "warn" ? "warn" : raw === "fail" ? "fail" : raw.replace(/_/g, " ");
        const color =
          raw === "pass"
            ? "text-emerald-700 bg-emerald-50 border-emerald-100"
            : raw === "warn"
              ? "text-amber-700 bg-amber-50 border-amber-100"
              : raw === "fail"
                ? "text-red-700 bg-red-50 border-red-100"
                : "text-slate-700 bg-slate-50 border-slate-200";
        return (
          <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide border ${color}`}>
            {label}
          </span>
        );
      }
    },
    { 
      accessorKey: "created_at", 
      header: "Date", 
      cell: ({ row }: any) => <span className="text-slate-500 whitespace-nowrap">{new Date(row.original.created_at).toLocaleDateString()}</span> 
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center bg-white p-5 rounded-xl border shadow-sm">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 border-l-4 border-emerald-500 pl-3">Generated Articles</h1>
        <div className="text-sm text-slate-500 bg-slate-50 px-3 py-1.5 rounded-md border">
           Total: <span className="font-bold text-slate-700">{data?.length || 0}</span>
        </div>
      </div>
      <ReactTable 
        columns={columns as any} 
        data={data || []} 
        isLoading={isLoading} 
        onRowClick={(article: any) => navigate(`/articles/${article.id}`)}
      />
    </div>
  );
}
