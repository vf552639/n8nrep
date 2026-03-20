import { useQuery } from "@tanstack/react-query";
import api from "@/api/client";
import { Article } from "@/types/article";
import FactCheckPanel from "@/components/tasks/FactCheckPanel";

export default function ArticleFactCheck({ articleId }: { articleId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["article", articleId],
    queryFn: async () => {
      const res = await api.get<Article>(`/articles/${articleId}`);
      return res.data;
    },
  });

  if (isLoading) return <div className="text-slate-500">Loading fact check details...</div>;
  if (!data) return null;

  return (
    <div className="max-w-3xl">
      <h2 className="text-lg font-semibold mb-6 text-slate-800 tracking-tight">Content Fact Checking Results</h2>
      <FactCheckPanel 
        status={data.fact_check_status || "needs_review"} 
        issues={[]} // Stub array to respect the interface, normally this is fetched from a specific field
      />
    </div>
  );
}
