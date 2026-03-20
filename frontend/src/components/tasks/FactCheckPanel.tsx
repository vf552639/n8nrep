import { FactCheckIssue } from "@/types/article";
import { AlertCircle, CheckCircle2, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  status: "passed" | "needs_review" | "failed";
  issues: FactCheckIssue[];
}

export default function FactCheckPanel({ status, issues }: Props) {
  const statusConfig = {
    passed: {
      color: "text-emerald-700 bg-emerald-50 border-emerald-200",
      icon: <CheckCircle2 className="w-5 h-5 text-emerald-600" />,
      text: "Fact Check Passed"
    },
    needs_review: {
      color: "text-amber-700 bg-amber-50 border-amber-200",
      icon: <AlertTriangle className="w-5 h-5 text-amber-600" />,
      text: "Needs Review"
    },
    failed: {
      color: "text-red-700 bg-red-50 border-red-200",
      icon: <AlertCircle className="w-5 h-5 text-red-600" />,
      text: "Fact Check Failed"
    }
  };

  const config = statusConfig[status] || statusConfig.needs_review;

  return (
    <div className="space-y-4">
      <div className={cn("flex items-center gap-3 p-3 rounded-md border shadow-sm", config.color)}>
        {config.icon}
        <span className="font-semibold">{config.text}</span>
        <span className="ml-auto text-sm font-medium opacity-80">{issues?.length || 0} issues detected</span>
      </div>

      {issues && issues.length > 0 && (
        <div className="space-y-3">
          {issues.map((issue, idx) => (
            <div key={idx} className="bg-white border p-3 rounded-xl shadow-sm space-y-2">
              <div className="flex items-start gap-2">
                <span className={cn(
                  "px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide shrink-0 mt-0.5",
                  issue.severity === "high" ? "bg-red-100 text-red-700" :
                  issue.severity === "medium" ? "bg-amber-100 text-amber-700" :
                  "bg-blue-100 text-blue-700"
                )}>
                  {issue.severity}
                </span>
                <span className="text-sm font-medium text-slate-800 leading-snug">{issue.claim}</span>
              </div>
              <div className="text-sm text-slate-600 ml-12 border-l-2 pl-3 py-1 my-1">
                <span className="font-semibold text-slate-700 mr-1 block text-xs underline mb-1">Recommendation</span>
                {issue.recommendation}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
