import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import api from "@/api/client";
import { StepResult } from "@/types/task";
import StepCard from "./StepCard";

interface Props {
  taskId: string;
  isActive: boolean;
}

export default function StepMonitor({ taskId, isActive }: Props) {
  const { data: steps, refetch } = useQuery({
    queryKey: ["task-steps", taskId],
    queryFn: async () => {
      const res = await api.get<{ steps: StepResult[] }>(`/tasks/${taskId}/steps`);
      return res.data?.steps || [];
    },
  });

  // Polling implementation for workflow monitoring
  useEffect(() => {
    if (!isActive) return;
    const idx = setInterval(() => refetch(), 8000);
    return () => clearInterval(idx);
  }, [isActive, refetch]);

  if (!steps) return <div className="text-sm text-slate-500 text-center py-4">Loading pipeline steps...</div>;

  return (
    <div className="space-y-3">
      {steps.map((step, i) => (
        <StepCard key={step.step_name + i} step={step} taskId={taskId} index={i} />
      ))}
    </div>
  );
}
