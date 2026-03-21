import { useState } from "react";
import { StepResult } from "@/types/task";
import { cn } from "@/lib/utils";
import { CheckCircle2, CircleDashed, XCircle, ArrowRightCircle, RefreshCw } from "lucide-react";
import StepRerunForm from "./StepRerunForm";
import ExcludeWordsAlert from "./ExcludeWordsAlert";
import SerpStepView from "./steps/SerpStepView";
import ScrapingStepView from "./steps/ScrapingStepView";
import LlmStepView from "./steps/LlmStepView";
import { parseStepResultJson } from "./steps/parseStepResult";

interface ExtendedStepResult extends StepResult {
  step_name: string;
  result_data?: any;
  resolved_prompts?: { system_prompt?: string; user_prompt?: string } | null;
  variables_snapshot?: Record<string, string> | null;
  exclude_words_violations?: Record<string, number> | string[] | null;
}

interface Props {
  step: ExtendedStepResult;
  taskId: string;
  index: number;
}

function hasExcludeViolations(step: ExtendedStepResult): boolean {
  const ex = step.exclude_words_violations;
  if (!ex) return false;
  if (Array.isArray(ex)) return ex.length > 0;
  if (typeof ex === "object") return Object.keys(ex).length > 0;
  return false;
}

export default function StepCard({ step, taskId, index }: Props) {
  const [expanded, setExpanded] = useState(false);

  const icons = {
    pending: <CircleDashed className="w-5 h-5 text-slate-300" />,
    running: <RefreshCw className="w-5 h-5 text-blue-500 animate-spin" />,
    completed: <CheckCircle2 className="w-5 h-5 text-emerald-500" />,
    failed: <XCircle className="w-5 h-5 text-red-500" />,
    skipped: <ArrowRightCircle className="w-5 h-5 text-slate-400" />,
  };

  const bgStyles = {
    pending: "bg-slate-50/50 border-slate-200",
    running: "bg-blue-50/30 border-blue-200 shadow-sm",
    completed: "bg-white border-slate-200",
    failed: "bg-red-50/50 border-red-200",
    skipped: "bg-slate-50 border-slate-200 opacity-70",
  };

  const showViolations = hasExcludeViolations(step);

  const serpParsed = step.step_name === "serp_research" ? parseStepResultJson(step.result) : null;
  const scrapeParsed = step.step_name === "competitor_scraping" ? parseStepResultJson(step.result) : null;

  return (
    <div className={cn("rounded-lg border p-3.5 transition-all outline-none", bgStyles[step.status])}>
      <div className="flex cursor-pointer select-none items-center gap-3" onClick={() => setExpanded(!expanded)}>
        <div className="shrink-0 rounded-full bg-white">{icons[step.status]}</div>
        <div className="flex flex-1 items-center justify-between">
          <div>
            <div className="text-sm font-semibold tracking-tight text-slate-800">
              {index + 1}. {step.step_name.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
            </div>
            {step.status === "failed" && step.error && (
              <div className="mt-0.5 line-clamp-1 text-xs text-red-600">{step.error}</div>
            )}
          </div>
          {step.status === "completed" && (
            <div className="text-right font-mono text-xs text-slate-400">
              {step.duration_ms ? `${(step.duration_ms / 1000).toFixed(1)}s` : ""}
              {step.cost ? <span className="ml-2 text-emerald-600">${step.cost.toFixed(4)}</span> : null}
            </div>
          )}
        </div>
      </div>

      {expanded && (
        <div className="mt-4 space-y-3 border-t border-slate-100 pt-4">
          {showViolations && step.exclude_words_violations && (
            <ExcludeWordsAlert violations={step.exclude_words_violations as Record<string, number> | string[]} />
          )}

          {step.step_name === "serp_research" && (
            <SerpStepView data={(serpParsed || {}) as any} taskId={taskId} />
          )}

          {step.step_name === "competitor_scraping" && <ScrapingStepView data={(scrapeParsed || {}) as any} />}

          {step.step_name !== "serp_research" && step.step_name !== "competitor_scraping" && (
            <LlmStepView step={step} stepName={step.step_name} />
          )}

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
