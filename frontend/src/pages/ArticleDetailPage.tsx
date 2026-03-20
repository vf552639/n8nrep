import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import api from "@/api/client";
import { Article } from "@/types/article";
import ArticleFactCheck from "@/components/articles/ArticleFactCheck";

export default function ArticleDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState("preview");

  const { data: article, isLoading } = useQuery({
    queryKey: ["article", id],
    queryFn: async () => {
      const res = await api.get<Article>(`/articles/${id}`);
      return res.data;
    },
    enabled: !!id,
  });

  if (isLoading) return <div className="p-6 text-slate-500">Loading article...</div>;
  if (!article) return <div className="p-6 text-red-500">Article not found</div>;

  return (
    <div className="space-y-6 h-full flex flex-col min-h-screen">
      <div className="flex justify-between items-start shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">{article.title || "Untitled Article"}</h1>
          <div className="text-sm text-slate-500 mt-2 flex gap-4 divide-x divide-slate-300">
            <span className="pr-4">{article.word_count || 0} words</span>
            <span className="px-4">{article.char_count || 0} chars</span>
            <span className="px-4 text-emerald-600 font-mono">${article.cost?.toFixed(4) || "0.0000"}</span>
            <span className="pl-4">{new Date(article.created_at).toLocaleString()}</span>
          </div>
        </div>
        <div className="flex gap-2">
          <a
            href={`${import.meta.env.VITE_API_URL || "http://localhost:8000/api"}/articles/${id}/download`}
            className="bg-white hover:bg-slate-50 shadow-sm text-slate-800 px-4 py-2 rounded-md transition-colors text-sm font-medium border"
            download
          >
            Download HTML
          </a>
        </div>
      </div>

      <div className="flex gap-1 border-b shrink-0">
        {["preview", "html", "metadata", "fact_check"].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`pb-2 px-3 text-sm font-medium capitalize transition-colors border-b-2 ${
              activeTab === tab 
                ? "border-blue-600 text-blue-600" 
                : "border-transparent text-slate-500 hover:text-slate-800 hover:bg-slate-50 rounded-t-lg"
            }`}
          >
            {tab.replace("_", " ")}
          </button>
        ))}
      </div>

      <div className="flex-1 bg-white border shadow-sm rounded-lg overflow-hidden min-h-[600px] flex flex-col">
        {activeTab === "preview" && (
          <iframe 
            srcDoc={article.full_page_html || article.html_content || "No content available"}
            className="w-full h-full border-none flex-1 min-h-[600px]"
            sandbox="allow-same-origin"
          />
        )}
        {activeTab === "html" && (
          <div className="p-6 overflow-auto h-full flex-1 bg-slate-900 min-h-[600px] font-mono text-sm">
            <pre className="whitespace-pre-wrap text-emerald-400">{article.full_page_html || article.html_content}</pre>
          </div>
        )}
        {activeTab === "metadata" && (
          <div className="p-8 space-y-6 max-w-4xl">
            <div>
              <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-2">Meta Title</h3>
              <p className="text-lg text-slate-900 bg-slate-50 p-4 rounded-lg border shadow-sm">{article.title}</p>
              <div className="text-sm text-slate-400 mt-2 font-mono">{article.title?.length || 0} characters</div>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-2 mt-8">Meta Description</h3>
              <p className="text-slate-900 bg-slate-50 p-4 rounded-lg border shadow-sm leading-relaxed">{article.description}</p>
              <div className="text-sm text-slate-400 mt-2 font-mono">{article.description?.length || 0} characters</div>
            </div>
          </div>
        )}
        {activeTab === "fact_check" && (
          <div className="p-8 h-full overflow-auto bg-slate-50/50">
             <ArticleFactCheck articleId={id as string} />
          </div>
        )}
      </div>
    </div>
  );
}
