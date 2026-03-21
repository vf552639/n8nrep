import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/api/client";
import { Article, FactCheckIssue } from "@/types/article";
import FactCheckPanel from "@/components/tasks/FactCheckPanel";

function mapFactCheckStatus(raw: string | undefined | null): "passed" | "needs_review" | "failed" | null {
  if (raw == null || String(raw).trim() === "") return null;
  const s = String(raw).toLowerCase().trim();
  if (s === "pass") return "passed";
  if (s === "warn") return "needs_review";
  if (s === "fail") return "failed";
  return "needs_review";
}

function normalizeIssues(raw: unknown): FactCheckIssue[] {
  if (!raw || !Array.isArray(raw)) return [];
  return raw.map((item) => {
    const o = item as Record<string, unknown>;
    return {
      claim: String(o.claim ?? ""),
      severity: String(o.severity ?? "medium"),
      problem: o.problem != null ? String(o.problem) : undefined,
      suggestion: o.suggestion != null ? String(o.suggestion) : undefined,
      recommendation: o.recommendation != null ? String(o.recommendation) : undefined,
      location: o.location != null ? String(o.location) : undefined,
      confidence: o.confidence != null ? String(o.confidence) : undefined,
      resolved: Boolean(o.resolved),
    };
  });
}

export default function ArticleFactCheck({ articleId }: { articleId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["article", articleId],
    queryFn: async () => {
      const res = await api.get<Article>(`/articles/${articleId}`);
      return res.data;
    },
  });

  const issues = useMemo(() => normalizeIssues(data?.fact_check_issues), [data?.fact_check_issues]);
  const displayStatus = useMemo(() => mapFactCheckStatus(data?.fact_check_status), [data?.fact_check_status]);

  if (isLoading) return <div className="text-slate-500">Loading fact check details...</div>;
  if (!data) return null;

  return (
    <div className="max-w-3xl">
      <h2 className="text-lg font-semibold mb-6 text-slate-800 tracking-tight">Content Fact Checking Results</h2>
      <FactCheckPanel status={displayStatus} issues={issues} articleId={articleId} />
    </div>
  );
}
