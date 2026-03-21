import { useState } from "react";
import { StepResult } from "@/types/task";
import { cn } from "@/lib/utils";
import { CheckCircle2, CircleDashed, XCircle, ArrowRightCircle, RefreshCw } from "lucide-react";
import StepRerunForm from "./StepRerunForm";
import ExcludeWordsAlert from "./ExcludeWordsAlert";
import JsonViewer from "@/components/common/JsonViewer";

interface ExtendedStepResult extends StepResult {
  step_name: string;
  result_data?: any;
}

interface Props {
  step: ExtendedStepResult;
  taskId: string;
  index: number;
}

export default function StepCard({ step, taskId, index }: Props) {
  const [expanded, setExpanded] = useState(false);

  const icons = {
    pending: <CircleDashed className="w-5 h-5 text-slate-300" />,
    running: <RefreshCw className="w-5 h-5 text-blue-500 animate-spin" />,
    completed: <CheckCircle2 className="w-5 h-5 text-emerald-500" />,
    failed: <XCircle className="w-5 h-5 text-red-500" />,
    skipped: <ArrowRightCircle className="w-5 h-5 text-slate-400" />
  };

  const bgStyles = {
    pending: "bg-slate-50/50 border-slate-200",
    running: "bg-blue-50/30 border-blue-200 shadow-sm",
    completed: "bg-white border-slate-200",
    failed: "bg-red-50/50 border-red-200",
    skipped: "bg-slate-50 border-slate-200 opacity-70"
  };

  const hasViolations = step.result?.exclude_words_violations?.length > 0 || step.result_data?.exclude_words_violations?.length > 0;

  return (
    <div className={cn("rounded-lg border p-3.5 transition-all outline-none", bgStyles[step.status])}>
      <div 
        className="flex items-center gap-3 cursor-pointer select-none"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="shrink-0 bg-white rounded-full">
          {icons[step.status]}
        </div>
        <div className="flex-1 flex justify-between items-center">
          <div>
            <div className="font-semibold text-sm text-slate-800 tracking-tight">
              {index + 1}. {step.step_name.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())}
            </div>
            {step.status === "failed" && step.error && (
              <div className="text-xs text-red-600 mt-0.5 line-clamp-1">{step.error}</div>
            )}
          </div>
          {step.status === "completed" && (
            <div className="text-xs text-slate-400 font-mono text-right">
              {step.duration_ms ? `${(step.duration_ms / 1000).toFixed(1)}s` : ""} 
              {step.cost ? <span className="ml-2 text-emerald-600">${step.cost.toFixed(4)}</span> : null}
            </div>
          )}
        </div>
      </div>

      {expanded && (
        <div className="mt-4 pt-4 border-t border-slate-100 space-y-3">
          {hasViolations && (
            <ExcludeWordsAlert violations={step.result_data.exclude_words_violations} />
          )}
          
            <JsonViewer data={step.result || step.result_data || { note: "No result data available" }} />
          
          {step.status === "completed" && (
            <div className="flex justify-end pt-2">
              <StepRerunForm taskId={taskId} stepName={step.step_name} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
