import { useParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useMemo } from "react";
import Editor from "@monaco-editor/react";
import toast from "react-hot-toast";
import api from "@/api/client";
import { articlesApi } from "@/api/articles";
import { Article } from "@/types/article";
import ArticleFactCheck from "@/components/articles/ArticleFactCheck";

function formatMetaFieldLabel(key: string) {
  return key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
}

function MetaFieldBlock({ fieldKey, value }: { fieldKey: string; value: unknown }) {
  const isString = typeof value === "string";
  const text = isString ? value : JSON.stringify(value, null, 2);
  const len = isString ? value.length : text.length;

  const charHint =
    fieldKey === "title" ? (
      <div className="text-sm mt-2 font-mono flex flex-wrap items-center gap-2">
        <span
          className={len >= 50 && len <= 60 ? "text-emerald-600" : "text-red-600"}
        >
          {len} characters
        </span>
        <span className="text-slate-400">· recommended 50–60</span>
      </div>
    ) : fieldKey === "description" ? (
      <div className="text-sm mt-2 font-mono flex flex-wrap items-center gap-2">
        <span
          className={len >= 150 && len <= 160 ? "text-emerald-600" : "text-red-600"}
        >
          {len} characters
        </span>
        <span className="text-slate-400">· recommended 150–160</span>
      </div>
    ) : null;

  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-2">
        {formatMetaFieldLabel(fieldKey)}
      </h3>
      {isString ? (
        <p className="text-slate-900 bg-slate-50 p-4 rounded-lg border shadow-sm leading-relaxed whitespace-pre-wrap">
          {value as string}
        </p>
      ) : (
        <pre className="text-sm text-slate-800 bg-slate-50 p-4 rounded-lg border shadow-sm overflow-x-auto whitespace-pre-wrap font-mono">
          {text}
        </pre>
      )}
      {charHint}
    </div>
  );
}

export default function ArticleDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState("preview");
  const [editingHtml, setEditingHtml] = useState(false);
  const [htmlDraft, setHtmlDraft] = useState("");

  const { data: article, isLoading } = useQuery({
    queryKey: ["article", id],
    queryFn: async () => {
      const res = await api.get<Article>(`/articles/${id}`);
      return res.data;
    },
    enabled: !!id,
  });

  const saveMutation = useMutation({
    mutationFn: () => articlesApi.update(id!, { html_content: htmlDraft }),
    onSuccess: () => {
      toast.success("Article saved");
      setEditingHtml(false);
      queryClient.invalidateQueries({ queryKey: ["article", id] });
    },
    onError: (e: unknown) => {
      const ax = e as { response?: { data?: { detail?: string } } };
      toast.error(ax.response?.data?.detail || "Save failed");
    },
  });

  const startEdit = () => {
    const src = article?.html_content || "";
    setHtmlDraft(src);
    setEditingHtml(true);
    setActiveTab("html");
  };

  const cancelEdit = () => {
    setEditingHtml(false);
  };

  const handleDownload = async () => {
    if (!id) return;
    try {
      const blob = await articlesApi.downloadBlob(id, "html");
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const safe = (article?.title || "article").replace(/[^\w\s-]/g, "").trim() || "article";
      a.download = `${safe}.html`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Download failed");
    }
  };

  const handleExportDocx = async () => {
    if (!id) return;
    try {
      const blob = await articlesApi.downloadBlob(id, "docx");
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const safe = (article?.title || "article").replace(/[^\w\s-]/g, "").trim() || "article";
      a.download = `${safe}.docx`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("DOCX downloaded");
    } catch {
      toast.error("Export DOCX failed");
    }
  };

  const metaEntries = useMemo(() => {
    const m = article?.meta_data;
    if (!m || typeof m !== "object" || Array.isArray(m)) return [];
    return Object.entries(m).filter(([, v]) => v != null);
  }, [article?.meta_data]);

  if (isLoading) return <div className="p-6 text-slate-500">Loading article...</div>;
  if (!article) return <div className="p-6 text-red-500">Article not found</div>;

  return (
    <div className="space-y-6 h-full flex flex-col min-h-screen">
      <div className="flex justify-between items-start shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">{article.title || "Untitled Article"}</h1>
          {article.main_keyword && (
            <p className="text-sm text-slate-600 mt-1">
              Keyword: <span className="font-medium text-slate-800">{article.main_keyword}</span>
            </p>
          )}
          <div className="text-sm text-slate-500 mt-2 flex flex-wrap gap-4 divide-x divide-slate-300">
            <span className="pr-4">{article.word_count || 0} words</span>
            <span className="px-4">{article.char_count ?? 0} chars</span>
            <span className="px-4 text-emerald-600 font-mono">
              ${(article.total_cost ?? article.cost ?? 0).toFixed(4)}
            </span>
            <span className="pl-4">{new Date(article.created_at).toLocaleString()}</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={handleDownload}
            className="bg-white hover:bg-slate-50 shadow-sm text-slate-800 px-4 py-2 rounded-md transition-colors text-sm font-medium border"
          >
            Download HTML
          </button>
          <button
            type="button"
            onClick={handleExportDocx}
            className="bg-white hover:bg-slate-50 shadow-sm text-slate-800 px-4 py-2 rounded-md transition-colors text-sm font-medium border"
          >
            Export DOCX
          </button>
          {!editingHtml ? (
            <button
              type="button"
              onClick={startEdit}
              className="bg-slate-800 hover:bg-slate-900 shadow-sm text-white px-4 py-2 rounded-md transition-colors text-sm font-medium"
            >
              Edit HTML
            </button>
          ) : (
            <>
              <button
                type="button"
                onClick={() => saveMutation.mutate()}
                disabled={saveMutation.isPending}
                className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-md text-sm font-medium disabled:opacity-50"
              >
                {saveMutation.isPending ? "Saving…" : "Save"}
              </button>
              <button
                type="button"
                onClick={cancelEdit}
                className="border border-slate-300 bg-white px-4 py-2 rounded-md text-sm hover:bg-slate-50"
              >
                Cancel
              </button>
            </>
          )}
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
        {activeTab === "html" &&
          (editingHtml ? (
            <div className="min-h-[600px] flex-1 border-t border-slate-200">
              <Editor
                height="640px"
                defaultLanguage="html"
                theme="vs-dark"
                value={htmlDraft}
                onChange={(v) => setHtmlDraft(v || "")}
                options={{ minimap: { enabled: true }, wordWrap: "on" }}
              />
            </div>
          ) : (
            <div className="p-6 overflow-auto h-full flex-1 bg-slate-900 min-h-[600px] font-mono text-sm">
              <pre className="whitespace-pre-wrap text-emerald-400">
                {article.full_page_html || article.html_content}
              </pre>
            </div>
          ))}
        {activeTab === "metadata" && (
          <div className="p-8 space-y-6 max-w-4xl">
            <p className="text-sm text-slate-600 bg-slate-50 border border-slate-200 rounded-lg px-4 py-3">
              These values are produced by the <strong className="text-slate-800">meta_generation</strong> pipeline step
              from your final article HTML.
            </p>
            {metaEntries.length > 0 ? (
              <div className="space-y-10">
                {metaEntries.map(([key, value]) => (
                  <MetaFieldBlock key={key} fieldKey={key} value={value} />
                ))}
              </div>
            ) : (
              <>
                <div>
                  <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-2">Meta Title</h3>
                  <p className="text-lg text-slate-900 bg-slate-50 p-4 rounded-lg border shadow-sm">{article.title}</p>
                  <div className="text-sm mt-2 font-mono flex flex-wrap items-center gap-2">
                    <span
                      className={
                        (article.title?.length || 0) >= 50 && (article.title?.length || 0) <= 60
                          ? "text-emerald-600"
                          : "text-red-600"
                      }
                    >
                      {article.title?.length || 0} characters
                    </span>
                    <span className="text-slate-400">· recommended 50–60</span>
                  </div>
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-2 mt-8">Meta Description</h3>
                  <p className="text-slate-900 bg-slate-50 p-4 rounded-lg border shadow-sm leading-relaxed">{article.description}</p>
                  <div className="text-sm mt-2 font-mono flex flex-wrap items-center gap-2">
                    <span
                      className={
                        (article.description?.length || 0) >= 150 && (article.description?.length || 0) <= 160
                          ? "text-emerald-600"
                          : "text-red-600"
                      }
                    >
                      {article.description?.length || 0} characters
                    </span>
                    <span className="text-slate-400">· recommended 150–160</span>
                  </div>
                </div>
              </>
            )}
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
