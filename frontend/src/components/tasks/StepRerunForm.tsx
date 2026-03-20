import { useState } from "react";
import api from "@/api/client";
import { RefreshCw } from "lucide-react";
import toast from "react-hot-toast";
import { useQueryClient } from "@tanstack/react-query";

interface Props {
  taskId: string;
  stepName: string;
}

export default function StepRerunForm({ taskId, stepName }: Props) {
  const [feedback, setFeedback] = useState("");
  const [cascade, setCascade] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const queryClient = useQueryClient();

  const handleRerun = async () => {
    setIsSubmitting(true);
    try {
      await api.post(`/tasks/${taskId}/rerun-step`, {
        step_name: stepName,
        feedback,
        cascade
      });
      toast.success("Step rerun initiated");
      queryClient.invalidateQueries({ queryKey: ["task-steps", taskId] });
      queryClient.invalidateQueries({ queryKey: ["task", taskId] });
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-slate-50 border rounded-md p-3 w-full space-y-3">
      <div className="text-sm font-medium text-slate-700">Rerun this step</div>
      <textarea
        className="w-full text-sm p-2 border rounded resize-y outline-none focus:ring-2 focus:ring-blue-500"
        placeholder="What should the AI fix? (Feedback)"
        rows={2}
        value={feedback}
        onChange={(e) => setFeedback(e.target.value)}
      />
      <div className="flex items-center justify-between">
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input 
            type="checkbox" 
            checked={cascade} 
            onChange={(e) => setCascade(e.target.checked)}
            className="rounded text-blue-600 focus:ring-blue-500"
          />
          Cascade (rerun subsequent steps)
        </label>
        <button
          onClick={handleRerun}
          disabled={isSubmitting}
          className="flex items-center gap-2 text-sm bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded disabled:opacity-50 transition-colors shadow-sm font-medium"
        >
          <RefreshCw className={cn("w-4 h-4", isSubmitting && "animate-spin")} />
          Rerun Step
        </button>
      </div>
    </div>
  );
}

// Simple internal cn for use inside this file to avoid cyclic dependencies occasionally
function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}
