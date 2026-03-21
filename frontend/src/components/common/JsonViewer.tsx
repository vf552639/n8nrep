import { useMemo } from "react";
import { cn } from "@/lib/utils";
import CopyButton from "./CopyButton";

interface Props {
  data: any;
  className?: string;
  expanded?: boolean;
}

export default function JsonViewer({ data, className, expanded = true }: Props) {
  const jsonString = useMemo(() => {
    try {
      return typeof data === "string" ? 
        JSON.stringify(JSON.parse(data), null, 2) : 
        JSON.stringify(data, null, 2);
    } catch {
      return String(data);
    }
  }, [data]);

  return (
    <div className={cn("relative group bg-slate-950 rounded-lg overflow-hidden border border-slate-800", className)}>
      <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <CopyButton 
          text={jsonString} 
          className="bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white border-slate-700"
        />
      </div>
      <pre className={cn(
        "p-4 text-xs font-mono text-slate-300 overflow-auto",
        !expanded && "max-h-60"
      )}>
        {jsonString}
      </pre>
    </div>
  );
}
