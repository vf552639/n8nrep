import { useMutation, useQueryClient } from "@tanstack/react-query";
import { StopCircle } from "lucide-react";
import toast from "react-hot-toast";
import api from "@/api/client";

export default function QueueControls() {
  const queryClient = useQueryClient();

  // Stop the entire Celery queue
  const stopQueueMutation = useMutation({
    mutationFn: () => api.post("/tasks/queue/stop"), // Example endpoint, adjust base URL if needed
    onSuccess: () => {
      toast.success("Queue stopped successfully");
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: () => toast.error("Failed to stop queue"),
  });

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={() => stopQueueMutation.mutate()}
        disabled={stopQueueMutation.isPending}
        className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-red-700 bg-red-50 hover:bg-red-100 border border-red-200 rounded-md transition-colors disabled:opacity-50"
      >
        <StopCircle className="w-4 h-4" />
        <span>Stop Queue</span>
      </button>
      {/* Additional queue controls could go here, e.g. Resume Queue */}
    </div>
  );
}
