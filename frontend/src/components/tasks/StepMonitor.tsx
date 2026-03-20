import { useQuery } from "@tanstack/react-query";
import { tasksApi } from "@/api/tasks";
import { usePolling } from "@/hooks/usePolling";
import StepCard from "./StepCard";

interface Props {
  taskId: string;
  isActive: boolean;
}

export default function StepMonitor({ taskId, isActive }: Props) {
  const { data: stepResp, refetch } = useQuery({
    queryKey: ["task-steps", taskId],
    queryFn: () => tasksApi.getSteps(taskId),
  });

  usePolling(refetch, isActive ? 8000 : null);

  if (!stepResp) return <div className="text-sm text-slate-500 text-center py-4">Loading pipeline steps...</div>;

  const stepsList = Object.entries(stepResp.step_results || {}).map(([name, result]) => ({
    step_name: name,
    ...result,
  }));

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between text-sm bg-slate-50 px-4 py-3 rounded border">
         <span className="font-medium text-slate-700">Overall Progress</span>
         <div className="flex items-center gap-3">
           <span className="text-slate-500">Cost: <span className="font-mono text-emerald-600">${stepResp.total_cost?.toFixed(4) || "0.0000"}</span></span>
           <span className="font-bold text-blue-700">{stepResp.progress || 0}%</span>
         </div>
      </div>
      <div className="space-y-3">
        {stepsList.map((step, i) => (
          <StepCard key={step.step_name + i} step={step as any} taskId={taskId} index={i} />
        ))}
      </div>
    </div>
  );
}
