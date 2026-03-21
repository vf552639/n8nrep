import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FactCheckIssue } from "@/types/article";
import { AlertCircle, CheckCircle2, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import { articlesApi } from "@/api/articles";
import toast from "react-hot-toast";

interface Props {
  status: "passed" | "needs_review" | "failed" | null;
  issues: FactCheckIssue[];
  articleId?: string;
}

function severityStyle(sev: string) {
  const s = (sev || "").toLowerCase();
  if (s === "critical" || s === "high")
    return "bg-red-100 text-red-700";
  if (s === "warning" || s === "medium")
    return "bg-amber-100 text-amber-700";
  if (s === "info" || s === "low")
    return "bg-blue-100 text-blue-700";
  return "bg-slate-100 text-slate-700";
}

export default function FactCheckPanel({ status, issues, articleId }: Props) {
  const queryClient = useQueryClient();

  const resolveMutation = useMutation({
    mutationFn: ({ index }: { index: number }) => {
      if (!articleId) throw new Error("missing article id");
      return articlesApi.resolveIssue(articleId, index);
    },
    onSuccess: () => {
      toast.success("Issue marked as resolved");
      if (articleId) {
        queryClient.invalidateQueries({ queryKey: ["article", articleId] });
      }
    },
    onError: () => toast.error("Could not update issue"),
  });

  const statusConfig = {
    passed: {
      color: "text-emerald-700 bg-emerald-50 border-emerald-200",
      icon: <CheckCircle2 className="w-5 h-5 text-emerald-600" />,
      text: "Fact Check Passed",
    },
    needs_review: {
      color: "text-amber-700 bg-amber-50 border-amber-200",
      icon: <AlertTriangle className="w-5 h-5 text-amber-600" />,
      text: "Needs Review",
    },
    failed: {
      color: "text-red-700 bg-red-50 border-red-200",
      icon: <AlertCircle className="w-5 h-5 text-red-600" />,
      text: "Fact Check Failed",
    },
  };

  const list = issues || [];
  const openCount = list.filter((i) => !i.resolved).length;

  return (
    <div className="space-y-4">
      {status && (
        <div
          className={cn(
            "flex items-center gap-3 p-3 rounded-md border shadow-sm",
            statusConfig[status].color
          )}
        >
          {statusConfig[status].icon}
          <span className="font-semibold">{statusConfig[status].text}</span>
          <span className="ml-auto text-sm font-medium opacity-80">
            {openCount} open / {list.length} total
          </span>
        </div>
      )}

      {!status && list.length === 0 && (
        <p className="text-sm text-slate-500">
          Fact check did not run or returned no status. Enable fact checking in pipeline settings to see
          verification here.
        </p>
      )}

      {list.length > 0 && (
        <div className="space-y-3">
          {list.map((issue, idx) => {
            const rec = issue.suggestion ?? issue.recommendation;
            return (
              <div
                key={idx}
                className="bg-white border p-3 rounded-xl shadow-sm space-y-2"
              >
                <div className="flex items-start gap-2 flex-wrap">
                  <span
                    className={cn(
                      "px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide shrink-0 mt-0.5",
                      severityStyle(String(issue.severity))
                    )}
                  >
                    {issue.severity || "unknown"}
                  </span>
                  {issue.resolved && (
                    <span className="text-[10px] font-semibold uppercase text-emerald-600">Resolved</span>
                  )}
                  <span className="text-sm font-medium text-slate-800 leading-snug flex-1 min-w-0">
                    {issue.claim}
                  </span>
                </div>
                {issue.problem && (
                  <div className="text-sm text-slate-600 ml-1 border-l-2 border-slate-200 pl-3">
                    <span className="font-semibold text-slate-700 text-xs block mb-0.5">Problem</span>
                    {issue.problem}
                  </div>
                )}
                {rec && (
                  <div className="text-sm text-slate-600 ml-1 border-l-2 border-slate-200 pl-3">
                    <span className="font-semibold text-slate-700 text-xs block mb-0.5">Suggestion</span>
                    {rec}
                  </div>
                )}
                <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                  {issue.location && (
                    <span>
                      <span className="font-medium text-slate-600">Location: </span>
                      {issue.location}
                    </span>
                  )}
                  {issue.confidence != null && issue.confidence !== "" && (
                    <span>
                      <span className="font-medium text-slate-600">Confidence: </span>
                      {String(issue.confidence)}
                    </span>
                  )}
                </div>
                {articleId && !issue.resolved && (
                  <button
                    type="button"
                    disabled={resolveMutation.isPending}
                    onClick={() => resolveMutation.mutate({ index: idx })}
                    className="text-xs font-medium text-blue-600 hover:text-blue-800 hover:underline"
                  >
                    Mark as resolved
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
