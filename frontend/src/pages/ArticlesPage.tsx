import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import api from "@/api/client";
import { Article } from "@/types/article";
import { PaginatedList } from "@/types/common";
import DataTable from "@/components/common/DataTable";

export default function ArticlesPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(0);

  const { data, isLoading } = useQuery({
    queryKey: ["articles", { page }],
    queryFn: async () => {
      const res = await api.get<PaginatedList<Article>>("/articles", {
        params: { skip: page * 50, limit: 50 },
      });
      return res.data;
    },
  });

  const columns = [
    { key: "title", header: "Title", render: (a: Article) => <div className="max-w-xs truncate font-medium text-slate-800" title={a.title}>{a.title}</div> },
    { key: "word_count", header: "Words", render: (a: Article) => <span className="text-slate-600">{a.word_count?.toLocaleString() || 0} words</span> },
    { 
      key: "fact_check_status", header: "Fact Check", 
      render: (a: Article) => {
        if (!a.fact_check_status) return <span className="text-slate-400 text-xs">N/A</span>;
        const color = a.fact_check_status === 'passed' ? 'text-emerald-700 bg-emerald-50' : a.fact_check_status === 'needs_review' ? 'text-amber-700 bg-amber-50' : 'text-red-700 bg-red-50';
        return <span className={`px-2 py-0.5 rounded text-xs font-medium uppercase tracking-wide border ${color}`}>{a.fact_check_status.replace('_', ' ')}</span>
      }
    },
    { key: "cost", header: "Cost", render: (a: Article) => <span className="text-emerald-600 font-mono">${a.cost?.toFixed(4) || "0.0000"}</span> },
    { key: "created_at", header: "Date", render: (a: Article) => <span className="text-slate-500 whitespace-nowrap">{new Date(a.created_at).toLocaleDateString()}</span> },
  ];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Generated Articles</h1>
      </div>
      <DataTable 
        columns={columns} 
        data={data?.items || []} 
        isLoading={isLoading} 
        onRowClick={(article) => navigate(`/articles/${article.id}`)}
      />
    </div>
  );
}
