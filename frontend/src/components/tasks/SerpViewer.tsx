import { useQuery } from "@tanstack/react-query";
import api from "@/api/client";
import { Download, Search } from "lucide-react";

export default function SerpViewer({ taskId }: { taskId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["task-serp", taskId],
    queryFn: async () => {
      const res = await api.get(`/tasks/${taskId}/serp-data`);
      return res.data;
    },
  });

  if (isLoading) return <div className="text-slate-500 text-sm p-4 text-center">Loading SERP data...</div>;
  if (!data) return <div className="text-slate-500 text-sm p-4 text-center border rounded-md">No SERP data available yet.</div>;

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center bg-slate-50 p-3 rounded-md border text-slate-700 shadow-sm">
        <div className="flex items-center gap-2">
            <Search className="w-4 h-4 text-slate-400" />
            <span className="text-sm font-medium">Export Full SERP Data (includes Raw DataForSEO)</span>
        </div>
        <a 
          href={`${import.meta.env.VITE_API_URL || "http://localhost:8000/api"}/tasks/${taskId}/serp-export`} 
          download 
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded text-sm font-medium transition-colors shadow-sm"
        >
          <Download className="w-4 h-4" /> Download ZIP
        </a>
      </div>
      
      <div className="bg-slate-900 rounded-md p-4 overflow-auto max-h-96 text-xs font-mono text-slate-300 shadow-inner">
        <pre>{JSON.stringify(data, null, 2)}</pre>
      </div>
    </div>
  );
}
