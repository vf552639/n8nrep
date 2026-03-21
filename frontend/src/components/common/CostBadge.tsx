import { cn } from "@/lib/utils";
import { Coins } from "lucide-react";

interface Props {
  cost: number | null | undefined;
  className?: string;
  showIcon?: boolean;
}

export default function CostBadge({ cost, className, showIcon = true }: Props) {
  if (cost == null) return null;

  return (
    <div 
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-mono font-medium tracking-tight bg-emerald-50 text-emerald-700 border border-emerald-200/50",
        className
      )}
      title="Computation Cost"
    >
      {showIcon && <Coins className="w-3 h-3 opacity-70" />}
      <span>${cost.toFixed(4)}</span>
    </div>
  );
}
