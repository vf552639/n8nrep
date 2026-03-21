import { useState } from "react";
import { Search, Terminal, AlertTriangle, Info, XCircle } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import api from "@/api/client";
import { ReactTable } from "@/components/common/ReactTable";

interface LogEntry {
  timestamp: string;
  level: string;
  service: string;
  message: string;
}

export default function LogsPage() {
  const [level, setLevel] = useState("ALL");
  const [searchTerm, setSearchTerm] = useState("");
  const [isAutoRefresh, setIsAutoRefresh] = useState(true);

  const { data: logsData, isLoading, refetch } = useQuery({
    queryKey: ["logs", level],
    queryFn: async () => {
      const res = await api.get<{logs: LogEntry[]}>(`/logs?lines=300&level=${level}`);
      return res.data.logs;
    },
    refetchInterval: isAutoRefresh ? 3000 : false // Poll every 3 seconds if enabled
  });

  const logs = logsData || [];
  
  const filteredLogs = logs.filter(log => 
    searchTerm ? (log.message.toLowerCase().includes(searchTerm.toLowerCase()) || log.service.toLowerCase().includes(searchTerm.toLowerCase())) : true
  );

  const columns = [
    { 
      accessorKey: "timestamp", 
      header: "Timestamp", 
      cell: ({ row }: any) => <span className="text-xs text-slate-500 font-mono whitespace-nowrap">{row.original.timestamp}</span> 
    },
    { 
      accessorKey: "level", 
      header: "Level", 
      cell: ({ row }: any) => {
        const lvl = row.original.level;
        if (lvl === "ERROR") return <span className="text-xs font-semibold px-2 py-0.5 rounded border border-red-200 bg-red-50 text-red-700 flex items-center gap-1 w-fit"><XCircle className="w-3 h-3"/> ERROR</span>;
        if (lvl === "WARNING") return <span className="text-xs font-semibold px-2 py-0.5 rounded border border-amber-200 bg-amber-50 text-amber-700 flex items-center gap-1 w-fit"><AlertTriangle className="w-3 h-3"/> WARN</span>;
        return <span className="text-xs font-semibold px-2 py-0.5 rounded border border-slate-200 bg-slate-50 text-slate-700 flex items-center gap-1 w-fit"><Info className="w-3 h-3"/> INFO</span>;
      }
    },
    { 
      accessorKey: "service", 
      header: "Service", 
      cell: ({ row }: any) => <span className="text-xs font-mono text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">{row.original.service}</span> 
    },
    { 
      accessorKey: "message", 
      header: "Message", 
      cell: ({ row }: any) => <span className="text-sm font-mono text-slate-700 break-words">{row.original.message}</span> 
    },
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] space-y-4">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-5 rounded-xl border shadow-sm shrink-0">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 border-l-4 border-slate-700 pl-3">System Logs</h1>
          <p className="text-sm text-slate-500 mt-1 pl-4">Review system activity and background job traces.</p>
        </div>
        <div className="flex items-center gap-3 w-full sm:w-auto self-end">
           <label className="flex items-center gap-2 text-sm text-slate-600 mr-2 cursor-pointer bg-slate-50 px-3 py-1.5 rounded-lg border">
             <input type="checkbox" checked={isAutoRefresh} onChange={(e) => setIsAutoRefresh(e.target.checked)} className="rounded text-blue-600" />
             Live Tail (3s)
           </label>
           <button onClick={() => refetch()} className="text-sm bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-medium px-4 py-1.5 rounded-lg shadow-sm transition-colors">
             Refresh Now
           </button>
        </div>
      </div>

      <div className="bg-white border rounded-xl shadow-sm flex flex-col overflow-hidden flex-1 relative min-h-0">
        <div className="border-b p-3 flex flex-wrap justify-between items-center bg-slate-50 gap-3 shrink-0">
          <div className="flex items-center gap-2 text-slate-600">
             <Terminal className="w-4 h-4" />
             <span className="font-medium text-sm">logs/app.log</span>
          </div>
          <div className="flex flex-wrap gap-3 flex-1 sm:flex-none justify-end">
             <div className="relative w-full sm:w-64">
                 <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                 <input 
                    type="text" 
                    placeholder="Search messages or services..." 
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded-lg py-1.5 pl-9 pr-3 text-sm text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500 shadow-sm"
                 />
             </div>
             <select 
                className="bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500 shadow-sm w-full sm:w-auto"
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

        <div className="flex-1 overflow-auto bg-white p-3">
            <ReactTable 
               columns={columns as any}
               data={filteredLogs}
               isLoading={isLoading}
            />
        </div>
      </div>
    </div>
  );
}
