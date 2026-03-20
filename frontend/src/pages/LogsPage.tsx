import { useState } from "react";
import { Search, Terminal } from "lucide-react";

export default function LogsPage() {
  const [level, setLevel] = useState("ALL");

  // In a real implementation this would fetch from a websockets /celery-logs endpoint or similar
  const dummyLogs = [
    "[2026-03-20 12:00:01] INFO [pipeline.py:45] Task 1st started for keyword 'example'",
    "[2026-03-20 12:00:05] WARNING [utils.py:12] Retrying OpenRouter API request",
    "[2026-03-20 12:01:00] INFO [step_monitor.py:8] Step 1 completed successfully",
    "[2026-03-20 12:05:00] ERROR [celery_app.py:59] Worker timeout on task 1st",
  ];

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
            {dummyLogs.map((log, i) => (
                <div key={i} className={`py-0.5 ${
                    log.includes('ERROR') ? 'text-red-400 font-medium' : 
                    log.includes('WARNING') ? 'text-amber-400' : 'text-slate-300'
                }`}>
                    {log}
                </div>
            ))}
            <div className="animate-pulse text-slate-600 mt-2">Waiting for new logs...</div>
        </div>
      </div>
    </div>
  );
}
