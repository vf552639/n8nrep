import { useState, useRef, useEffect } from "react";
import { Search, Terminal } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import api from "@/api/client";

export default function LogsPage() {
  const [level, setLevel] = useState("ALL");
  const [searchTerm, setSearchTerm] = useState("");
  const logsEndRef = useRef<HTMLDivElement>(null);

  const { data: logsData, isLoading } = useQuery({
    queryKey: ["logs", level],
    queryFn: async () => {
      const res = await api.get<{logs: string[]}>(`/logs?lines=200&level=${level}`);
      return res.data.logs;
    },
    refetchInterval: 3000 // Poll every 3 seconds
  });

  const logs = logsData || [];
  
  const filteredLogs = logs.filter(log => 
    searchTerm ? log.toLowerCase().includes(searchTerm.toLowerCase()) : true
  );

  useEffect(() => {
    // Auto scroll to bottom when new logs arrive
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [filteredLogs]);

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      <div className="flex justify-between items-center mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">System Logs</h1>
          <p className="text-sm text-slate-500 mt-1">Real-time view of Celery workers and API logs.</p>
        </div>
      </div>

      <div className="flex-1 bg-slate-950 rounded-xl shadow-sm border border-slate-800 flex flex-col overflow-hidden">
        <div className="bg-slate-900 border-b border-slate-800 p-3 flex justify-between items-center shrink-0">
          <div className="flex items-center gap-2 text-slate-400">
             <Terminal className="w-5 h-5" />
             <span className="font-mono text-sm font-semibold">tail -f /logs/celery.log</span>
          </div>
          <div className="flex gap-3">
             <div className="relative">
                 <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                 <input 
                    type="text" 
                    placeholder="Search logs..." 
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="bg-slate-950 border border-slate-700 rounded-md py-1.5 pl-9 pr-3 text-sm text-slate-300 w-64 focus:outline-none focus:border-slate-500"
                 />
             </div>
             <select 
                className="bg-slate-950 border border-slate-700 rounded-md px-3 py-1.5 text-sm text-slate-300 focus:outline-none"
                value={level}
                onChange={(e) => setLevel(e.target.value)}
             >
                <option value="ALL">All Levels</option>
                <option value="INFO">INFO</option>
                <option value="WARNING">WARNING</option>
                <option value="ERROR">ERROR</option>
             </select>
          </div>
        </div>

        <div className="flex-1 p-4 overflow-auto font-mono text-xs sm:text-sm whitespace-pre-wrap leading-relaxed">
            {isLoading && <div className="text-slate-500 mb-4 animate-pulse">Loading logs...</div>}
            
            {filteredLogs.map((log, i) => (
                <div key={i} className={`py-0.5 ${
                    log.includes('ERROR') ? 'text-red-400 font-medium' : 
                    log.includes('WARNING') ? 'text-amber-400' : 'text-slate-300'
                }`}>
                    {log}
                </div>
            ))}
            
            {filteredLogs.length === 0 && !isLoading && (
              <div className="text-slate-500 italic mt-2">No logs found matching criteria.</div>
            )}
            
            <div ref={logsEndRef} className="h-1 mt-2"></div>
        </div>
      </div>
    </div>
  );
}
