import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export default function LoadingSpinner({ className, size = 'md' }: Props) {
  const sizeClasses = {
    sm: "w-4 h-4",
    md: "w-6 h-6",
    lg: "w-8 h-8",
  };

  return (
    <Loader2 
      className={cn("animate-spin text-slate-400", sizeClasses[size], className)} 
    />
  );
}
