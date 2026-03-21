import { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { tasksApi } from "@/api/tasks";
import StatusBadge from "@/components/common/StatusBadge";
import StepMonitor from "@/components/tasks/StepMonitor";
import SerpViewer from "@/components/tasks/SerpViewer";

export default function TaskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState("pipeline");

  // Fetch task details
  const { data: task, isLoading } = useQuery({
    queryKey: ["task", id],
    queryFn: () => tasksApi.getOne(id!),
    enabled: !!id,
    refetchInterval: (query) => query.state.data?.status === "processing" ? 5000 : false,
  });

  const handleForceAction = async (action: "complete" | "fail") => {
    try {
      if (!id) return;
      await tasksApi.forceStatus(id, action);
      toast.success(`Task forced to ${action === 'complete' ? 'Completed' : 'Failed'}`);
      queryClient.invalidateQueries({ queryKey: ["task", id] });
    } catch {
      toast.error("Failed to force action. Check console.");
    }
  };

  if (isLoading) return <div className="p-6 text-slate-500 flex items-center justify-center h-64">Loading task details...</div>;
  if (!task) return <div className="p-6 text-red-500">Task not found</div>;

  const tabs = [
    { id: "pipeline", label: "Pipeline Execution" },
    { id: "serp", label: "SERP Data" },
    { id: "prompts", label: "Prompts Debug" },
    { id: "logs", label: "Execution Logs" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Task: {task.main_keyword}</h1>
          <div className="text-sm text-slate-500 mt-1 font-mono">ID: {task.id}</div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex gap-2 bg-slate-50 px-3 py-1.5 rounded-md border text-sm">
             <button 
               onClick={() => handleForceAction("complete")}
               className="text-emerald-700 hover:text-emerald-800 font-medium hover:underline flex items-center gap-1"
             >
               Force Complete
             </button>
             <span className="text-slate-300">|</span>
             <button 
               onClick={() => handleForceAction("fail")}
               className="text-red-700 hover:text-red-800 font-medium hover:underline flex items-center gap-1"
             >
               Force Fail
             </button>
          </div>
          <StatusBadge status={task.status} />
        </div>
      </div>

      <div className="flex gap-2 border-b mt-4 overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`pb-3 px-4 text-sm font-medium transition-colors border-b-2 whitespace-nowrap ${
              activeTab === tab.id 
                ? "border-blue-600 text-blue-600" 
                : "border-transparent text-slate-500 hover:text-slate-800 hover:bg-slate-50 rounded-t-lg"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 space-y-6">
          {activeTab === "pipeline" && (
            <div className="bg-white border rounded-xl shadow-sm p-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
              <StepMonitor taskId={task.id} isActive={task.status === "processing"} />
            </div>
          )}
          
          {activeTab === "serp" && (
            <div className="bg-white border rounded-xl shadow-sm p-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
              <SerpViewer taskId={task.id} />
            </div>
          )}

          {activeTab === "prompts" && (
            <div className="bg-white border rounded-xl shadow-sm p-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
              <h2 className="text-lg font-semibold mb-4 text-slate-800">Prompts Debugging</h2>
              <div className="text-sm text-slate-500 bg-slate-50 p-4 rounded-lg border mb-4">
                This tab shows the resolved prompt templates and agent trajectories for the task.
              </div>
              
              <div className="space-y-4">
                {[
                  { id: "serp_research", label: "SERP Research" },
                  { id: "competitor_scraping", label: "Competitor Scraping" },
                  { id: "ai_structure_analysis", label: "AI Structure Analysis" },
                  { id: "chunk_cluster_analysis", label: "Chunk Cluster Analysis" },
                  { id: "competitor_structure_analysis", label: "Competitor Structure Analysis" },
                  { id: "final_structure_analysis", label: "Final Structure Analysis" },
                  { id: "structure_fact_checking", label: "Structure Fact-Checking" },
                  { id: "primary_generation", label: "Primary Generation" },
                  { id: "competitor_comparison", label: "Competitor Comparison" },
                  { id: "reader_opinion", label: "Reader Opinion" },
                  { id: "interlinking_citations", label: "Interlinking & Citations" },
                  { id: "improver", label: "Improver" },
                  { id: "final_editing", label: "Final Editing" },
                  { id: "content_fact_checking", label: "Content Fact-Checking" },
                  { id: "html_structure", label: "HTML Structure" },
                  { id: "meta_generation", label: "Meta Generation" }
                ].map(step => {
                  const stepData = task.step_results?.[step.id];
                  const resolvedPrompts = stepData?.resolved_prompts;
                  
                  return (
                    <details key={step.id} className="group border rounded-lg bg-white overflow-hidden">
                      <summary className="flex items-center justify-between p-4 cursor-pointer bg-slate-50 hover:bg-slate-100 transition-colors select-none font-medium text-slate-800">
                        <div className="flex items-center gap-3">
                           <span>{step.label}</span>
                           {!resolvedPrompts && (
                             <span className="px-2 py-0.5 rounded text-xs bg-slate-200 text-slate-500 font-normal">
                               Промпты не сохранены
                             </span>
                           )}
                           {resolvedPrompts && (
                             <span className="px-2 py-0.5 rounded text-xs bg-emerald-100 text-emerald-700 font-normal">
                               {stepData?.model || "Resolved"}
                             </span>
                           )}
                        </div>
                        <div className="text-slate-400 group-open:rotate-180 transition-transform">▼</div>
                      </summary>
                      
                      {resolvedPrompts && (
                        <div className="p-4 border-t border-slate-100 space-y-6 bg-[#fffffe]">
                          <div>
                            <div className="flex justify-between items-center mb-2">
                               <h4 className="text-sm font-bold text-slate-700 uppercase tracking-wider">System Prompt</h4>
                               <button 
                                 onClick={(e) => {
                                   e.preventDefault();
                                   navigator.clipboard.writeText(resolvedPrompts.system_prompt || "");
                                   toast.success("System prompt copied");
                                 }}
                                 className="text-xs px-2 py-1 bg-blue-50 text-blue-600 rounded hover:bg-blue-100 transition-colors"
                               >
                                 Copy
                               </button>
                            </div>
                            <pre className="bg-slate-50 p-4 rounded-lg text-sm text-slate-800 font-mono whitespace-pre-wrap border overflow-x-auto max-h-[300px] overflow-y-auto">
                              {resolvedPrompts.system_prompt || "Empty"}
                            </pre>
                          </div>
                          
                          <div>
                            <div className="flex justify-between items-center mb-2">
                               <h4 className="text-sm font-bold text-slate-700 uppercase tracking-wider">User Prompt</h4>
                               <button 
                                 onClick={(e) => {
                                   e.preventDefault();
                                   navigator.clipboard.writeText(resolvedPrompts.user_prompt || "");
                                   toast.success("User prompt copied");
                                 }}
                                 className="text-xs px-2 py-1 bg-blue-50 text-blue-600 rounded hover:bg-blue-100 transition-colors"
                               >
                                 Copy
                               </button>
                            </div>
                            <pre className="bg-slate-50 p-4 rounded-lg text-sm text-slate-800 font-mono whitespace-pre-wrap border overflow-x-auto max-h-[300px] overflow-y-auto">
                              {resolvedPrompts.user_prompt || "Empty"}
                            </pre>
                          </div>
                        </div>
                      )}
                      
                      {!resolvedPrompts && (
                        <div className="p-4 border-t border-slate-100 text-sm text-slate-500 italic bg-[#fafafa]">
                          Нет данных о промптах для этого шага. Возможно, шаг был пропущен или выполнялся старой версией системы.
                        </div>
                      )}
                    </details>
                  );
                })}
              </div>
            </div>
          )}

          {activeTab === "logs" && (
            <div className="bg-white border rounded-xl shadow-sm p-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
              <h2 className="text-lg font-semibold mb-4 text-slate-800">Task Execution Logs</h2>
              <div className="bg-[#1e1e1e] rounded-lg p-4 font-mono text-sm h-[500px] overflow-auto text-green-400">
                 {task.logs ? (
                    task.logs.map((log: any, i: number) => (
                        <div key={i} className="mb-1 leading-relaxed">
                          <span className="text-slate-500 mr-2">[{new Date(log.timestamp || Date.now()).toISOString()}]</span> 
                          <span className={log.level === 'error' ? 'text-red-400' : 'text-slate-300'}>{log.message}</span>
                        </div>
                    ))
                 ) : (
                    <div className="text-slate-500 italic">No logs associated with this task. Use the global logs tab to search by Task ID.</div>
                 )}
              </div>
            </div>
          )}
        </div>

        <div className="space-y-6">
          <div className="bg-white border rounded-xl shadow-sm p-6">
            <h2 className="text-lg font-semibold border-b pb-4 mb-4 text-slate-800">Task Details</h2>
            <ul className="space-y-4 text-sm">
              <li className="flex justify-between items-center">
                <span className="text-slate-500">Country:</span>
                <span className="font-medium bg-slate-100 px-2 py-1 rounded">{task.country}</span>
              </li>
              <li className="flex justify-between items-center">
                <span className="text-slate-500">Language:</span>
                <span className="font-medium bg-slate-100 px-2 py-1 rounded">{task.language}</span>
              </li>
              <li className="flex justify-between items-center">
                <span className="text-slate-500">Cost:</span>
                <span className="font-medium text-emerald-600 font-mono">${task.total_cost?.toFixed(4) || "0.0000"}</span>
              </li>
              <li className="flex justify-between items-center">
                <span className="text-slate-500">Created At:</span>
                <span className="font-medium text-slate-700">{new Date(task.created_at).toLocaleString()}</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
