import { useQuery } from "@tanstack/react-query";
import { tasksApi } from "@/api/tasks";
import { usePolling } from "@/hooks/usePolling";
import StepCard from "./StepCard";

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
  const { data: stepResp, refetch } = useQuery({
    queryKey: ["task-steps", taskId],
    queryFn: () => tasksApi.getSteps(taskId),
  });

  usePolling(refetch, isActive ? 8000 : null);

  if (!stepResp) return <div className="text-sm text-slate-500 text-center py-4">Loading pipeline steps...</div>;

  const results = stepResp.step_results || {};
  const isWaiting = (results as any).waiting_for_approval === true;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between text-sm bg-slate-50 px-4 py-3 rounded border">
         <span className="font-medium text-slate-700">Overall Progress</span>
         <div className="flex items-center gap-3">
           {isWaiting && (
             <span className="text-amber-600 text-xs font-medium">⏸ Paused — see Article Review tab</span>
           )}
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
