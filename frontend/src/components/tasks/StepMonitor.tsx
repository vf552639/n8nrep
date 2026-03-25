import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { tasksApi } from "@/api/tasks";
import { usePolling } from "@/hooks/usePolling";
import StepCard from "./StepCard";
import toast from "react-hot-toast";

interface Props {
  taskId: string;
  isActive: boolean;
}

const ALL_STEPS = [
  "serp_research",
  "competitor_scraping",
  "ai_structure_analysis",
  "chunk_cluster_analysis",
  "competitor_structure_analysis",
  "final_structure_analysis",
  "structure_fact_checking",
  "primary_generation",
  "competitor_comparison",
  "reader_opinion",
  "interlinking_citations",
  "improver",
  "final_editing",
  "content_fact_checking",
  "html_structure",
  "meta_generation"
];

export default function StepMonitor({ taskId, isActive }: Props) {
  const queryClient = useQueryClient();
  const [approving, setApproving] = useState(false);

  const { data: stepResp, refetch } = useQuery({
    queryKey: ["task-steps", taskId],
    queryFn: () => tasksApi.getSteps(taskId),
  });

  usePolling(refetch, isActive ? 8000 : null);

  if (!stepResp) return <div className="text-sm text-slate-500 text-center py-4">Loading pipeline steps...</div>;

  const results = stepResp.step_results || {};
  const waitingForApproval = (results as any).waiting_for_approval === true;
  const primaryResult = (results.primary_generation as any)?.result || "";

  const handleApprove = async () => {
    setApproving(true);
    try {
      await tasksApi.approve(taskId);
      toast.success("Pipeline approved — continuing generation");
      queryClient.invalidateQueries({ queryKey: ["task", taskId] });
      queryClient.invalidateQueries({ queryKey: ["task-steps", taskId] });
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Failed to approve");
    } finally {
      setApproving(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Test Mode Approval Banner */}
      {waitingForApproval && (
        <div className="rounded-lg border-2 border-amber-300 bg-amber-50 overflow-hidden">
          <div className="px-5 py-3 bg-amber-100 border-b border-amber-200 flex items-center gap-2">
            <span className="text-lg">🛑</span>
            <div>
              <p className="font-semibold text-amber-900 text-sm">TEST MODE: Pipeline paused</p>
              <p className="text-amber-700 text-xs">Waiting for manual approval after Primary Generation</p>
            </div>
          </div>

          {primaryResult && (
            <div className="p-4">
              <p className="text-xs font-medium text-slate-500 mb-2 uppercase tracking-wide">Generated Article Preview</p>
              <div
                className="max-h-[500px] overflow-y-auto border border-slate-200 rounded-lg p-4 bg-white text-sm leading-relaxed prose prose-sm max-w-none"
                dangerouslySetInnerHTML={{ __html: primaryResult }}
              />
            </div>
          )}

          <div className="px-5 py-3 border-t border-amber-200 bg-amber-50 flex justify-end">
            <button
              onClick={handleApprove}
              disabled={approving}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-400 text-white font-medium text-sm rounded-lg transition-colors shadow-sm"
            >
              {approving ? (
                <>
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Approving…
                </>
              ) : (
                <>✅ Approve & Continue Pipeline</>
              )}
            </button>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between text-sm bg-slate-50 px-4 py-3 rounded border">
         <span className="font-medium text-slate-700">Overall Progress</span>
         <div className="flex items-center gap-3">
           <span className="text-slate-500">Cost: <span className="font-mono text-emerald-600">${stepResp.total_cost?.toFixed(4) || "0.0000"}</span></span>
           <span className="font-bold text-blue-700">{stepResp.progress || 0}%</span>
         </div>
      </div>
      <div className="space-y-3">
        {ALL_STEPS.map((stepName, i) => {
          const result = results[stepName] || { status: "pending" };
          return (
            <StepCard 
              key={stepName} 
              step={{ step_name: stepName, ...result } as any} 
              taskId={taskId} 
              index={i} 
            />
          );
        })}
      </div>
    </div>
  );
}
