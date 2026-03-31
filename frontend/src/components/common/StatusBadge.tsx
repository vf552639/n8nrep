import { cn } from "@/lib/utils";

export type TaskStatus = "pending" | "processing" | "completed" | "failed" | "stale" | "stopped" | "awaiting_page_approval";

interface Props {
  status: TaskStatus | string;
}

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-gray-200 text-gray-800",
  processing: "bg-blue-200 text-blue-800 animate-pulse",
  completed: "bg-green-200 text-green-800",
  failed: "bg-red-200 text-red-800",
  stale: "bg-yellow-200 text-yellow-800",
  stopped: "bg-orange-200 text-orange-800",
  awaiting_page_approval: "bg-amber-100 text-amber-700",
};

export default function StatusBadge({ status }: Props) {
  const colorClass = STATUS_COLORS[status.toLowerCase()] || "bg-gray-100 text-gray-800";
  
  return (
    <span className={cn("px-2.5 py-0.5 rounded-full text-xs font-medium uppercase tracking-wider", colorClass)}>
      {status.toLowerCase() === "awaiting_page_approval" ? "Awaiting Approval" : status}
    </span>
  );
}
