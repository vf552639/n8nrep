import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Editor from "@monaco-editor/react";
import toast from "react-hot-toast";
import { promptsApi } from "@/api/prompts";
import { Prompt } from "@/types/prompt";
import { Play, Save, Settings2, X, FileJson, Loader2 } from "lucide-react";

export default function PromptsPage() {
  const queryClient = useQueryClient();
  const [activePromptId, setActivePromptId] = useState<string | null>(null);
  const [editState, setEditState] = useState<Partial<Prompt> | null>(null);
  const [isTestOpen, setIsTestOpen] = useState(false);

  const { data: prompts, isLoading } = useQuery({
    queryKey: ["prompts"],
    queryFn: () => promptsApi.getAll(),
  });

  const activePrompt = prompts?.find(p => p.id === activePromptId) || prompts?.[0];

  useEffect(() => {
    if (activePrompt && activePrompt.id !== editState?.id) {
      setEditState(activePrompt);
    }
  }, [activePrompt, editState?.id]);

  const saveMutation = useMutation({
    mutationFn: (data: Partial<Prompt>) => promptsApi.update(data.id!, data),
    onSuccess: () => {
      toast.success("Prompt saved successfully");
      queryClient.invalidateQueries({ queryKey: ["prompts"] });
    },
    onError: () => toast.error("Failed to save prompt"),
  });

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-6">
      <div className="w-1/4 bg-white border rounded-lg shadow-sm flex flex-col shrink-0 min-w-[250px]">
        <div className="p-4 border-b bg-slate-50 font-semibold text-slate-800 rounded-t-lg">Available Agents</div>
        <div className="flex-1 overflow-auto p-2 space-y-1">
          {isLoading ? (
            <div className="p-4 text-center text-sm text-slate-500">Loading prompts...</div>
          ) : (
            prompts?.map((prompt) => (
              <button
                key={prompt.id}
                onClick={() => setActivePromptId(prompt.id)}
                className={`w-full text-left px-3 py-2.5 rounded-md text-sm transition-colors ${(activePromptId ? activePromptId === prompt.id : prompts[0].id === prompt.id)
                    ? "bg-blue-50 text-blue-700 font-medium"
                    : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                }`}
              >
                {prompt.agent_name.replace(/_/g, " ")}
              </button>
            ))
          )}
        </div>
      </div>

      <div className="flex-1 bg-white border rounded-lg shadow-sm flex flex-col min-w-0">
        {activePrompt && editState ? (
          <>
            <div className="p-4 border-b flex flex-wrap justify-between items-center bg-slate-50 rounded-t-lg shrink-0 gap-4">
              <div>
                <h2 className="font-semibold text-slate-800 capitalize text-lg">{activePrompt.agent_name.replace(/_/g, " ")}</h2>
                <div className="text-xs text-slate-500 mt-1 flex gap-4">
                  <span className="flex items-center gap-1">v{activePrompt.version}</span>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-2 mr-2">
                   <label className="text-xs text-slate-500 font-medium">Model</label>
                   <select 
                     value={editState.model || "gpt-4"} 
                     onChange={e => setEditState(prev => prev ? {...prev, model: e.target.value} : null)}
                     className="text-xs border rounded p-1"
                   >
                     <option value="gpt-4o">gpt-4o</option>
                     <option value="gpt-4 Turbo">gpt-4 Turbo</option>
                     <option value="gpt-3.5-turbo">gpt-3.5-turbo</option>
                     <option value="claude-3-5-sonnet-20240620">claude-3.5-sonnet</option>
                   </select>
                </div>
                <div className="flex items-center gap-2 mr-2">
                   <label className="text-xs text-slate-500 font-medium">Temp</label>
                   <input 
                     type="number" step="0.1" min="0" max="2"
                     value={editState.temperature ?? 0.7} 
                     onChange={e => setEditState(prev => prev ? {...prev, temperature: parseFloat(e.target.value)} : null)}
                     className="text-xs border rounded p-1 w-16"
                   />
                </div>
                <div className="flex items-center gap-2 mr-2">
                   <label className="text-xs text-slate-500 font-medium">Tokens</label>
                   <input 
                     type="number" step="100" min="100"
                     value={editState.max_tokens ?? 2000} 
                     onChange={e => setEditState(prev => prev ? {...prev, max_tokens: parseInt(e.target.value)} : null)}
                     className="text-xs border rounded p-1 w-20"
                   />
                </div>

                <label className="flex items-center gap-2 text-sm text-slate-700 mr-2 cursor-pointer">
                  <input 
                    type="checkbox" 
                    className="rounded border-slate-300"
                    checked={editState.skip_in_pipeline || false}
                    onChange={(e) => setEditState(prev => prev ? {...prev, skip_in_pipeline: e.target.checked} : null)}
                  />
                  Skip
                </label>
                <div className="h-6 w-px bg-slate-300 mx-1"></div>
                <button 
                  onClick={() => setIsTestOpen(true)}
                  className="flex items-center gap-2 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 px-3 py-1.5 rounded-md transition-colors text-sm font-medium border border-emerald-200 shadow-sm"
                >
                  <Play className="w-4 h-4" /> Test
                </button>
                <button 
                  onClick={() => saveMutation.mutate(editState)}
                  disabled={saveMutation.isPending}
                  className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-1.5 rounded-md transition-colors text-sm font-medium shadow-sm disabled:opacity-70"
                >
                  <Save className="w-4 h-4" /> Save
                </button>
              </div>
            </div>
            
            <div className="p-3 bg-slate-100 border-b text-xs flex gap-4 overflow-x-auto whitespace-nowrap scrollbar-hide items-center">
               <span className="font-semibold text-slate-600 flex items-center gap-1"><Settings2 className="w-4 h-4"/> Variables:</span>
               {['{{main_keyword}}', '{{language}}', '{{country}}', '{{competitors_headers}}', '{{avg_word_count}}', '{{merged_markdown}}', '{{related_searches}}', '{{intent}}', '{{structura}}'].map(v => (
                 <button 
                   key={v} 
                   onClick={() => { navigator.clipboard.writeText(v); toast.success(`Copied ${v}`); }}
                   className="font-mono text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded border border-blue-200 hover:bg-blue-100 transition-colors cursor-copy"
                   title="Click to copy"
                 >
                   {v}
                 </button>
               ))}
            </div>
            
            <div className="flex-1 flex flex-col xl:flex-row divide-y xl:divide-y-0 xl:divide-x overflow-hidden">
                <div className="flex-1 flex flex-col min-w-0">
                    <div className="p-2.5 bg-slate-100 text-xs font-bold text-slate-600 uppercase tracking-wider shrink-0 border-b">System Prompt</div>
                    <div className="flex-1 relative bg-[#fffffe]">
                        <Editor
                            height="100%"
                            language="markdown"
                            theme="vs-light"
                            value={editState.system_prompt || ""}
                            onChange={(val) => setEditState(prev => prev ? {...prev, system_prompt: val || ""} : null)}
                            options={{ minimap: { enabled: false }, wordWrap: "on", padding: { top: 16 } }}
                        />
                    </div>
                </div>
                <div className="flex-1 flex flex-col min-w-0">
                    <div className="p-2.5 bg-slate-100 text-xs font-bold text-slate-600 uppercase tracking-wider shrink-0 border-b">User Prompt</div>
                    <div className="flex-1 relative bg-[#fffffe]">
                        <Editor
                            height="100%"
                            language="markdown"
                            theme="vs-light"
                            value={editState.user_prompt || ""}
                            onChange={(val) => setEditState(prev => prev ? {...prev, user_prompt: val || ""} : null)}
                            options={{ minimap: { enabled: false }, wordWrap: "on", padding: { top: 16 } }}
                        />
                    </div>
                </div>
            </div>

            {isTestOpen && (
              <PromptTestRunner 
                prompt={editState as Prompt} 
                onClose={() => setIsTestOpen(false)} 
              />
            )}
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-slate-500">Select an agent to view and edit prompts</div>
        )}
      </div>
    </div>
  );
}

function PromptTestRunner({ prompt, onClose }: { prompt: Prompt, onClose: () => void }) {
  const [testContext, setTestContext] = useState<string>('{\n  "main_keyword": "SEO Strategy 2024",\n  "language": "en",\n  "country": "us"\n}');
  const [result, setResult] = useState<any>(null);

  const testMutation = useMutation({
    mutationFn: async () => {
      let parsedContext = {};
      try { parsedContext = JSON.parse(testContext); } 
      catch (e) { throw new Error("Invalid JSON in Test Context"); }
      
      return promptsApi.testPrompt(prompt.id, {
        context: parsedContext,
        model: prompt.model
      });
    },
    onSuccess: (data) => setResult(data),
    onError: (err: any) => {
      setResult({ error: err.message || "Test failed" });
      toast.error(err.message || "Test failed");
    }
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-4xl p-0 flex flex-col min-h-[600px] overflow-hidden">
        <div className="px-6 py-4 border-b bg-slate-50 flex justify-between items-center shrink-0">
           <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">Test Prompt: <span className="text-blue-600 font-mono text-base">{prompt.agent_name}</span></h2>
           <button onClick={onClose} className="p-1 hover:bg-slate-200 rounded text-slate-500 transition-colors"><X className="w-5 h-5"/></button>
        </div>
        
        <div className="flex-1 flex flex-col lg:flex-row divide-y lg:divide-y-0 lg:divide-x overflow-hidden">
           <div className="w-full lg:w-1/3 flex flex-col p-4 bg-slate-50">
              <label className="flex items-center gap-2 text-sm font-semibold text-slate-700 mb-2 mt-1">
                <FileJson className="w-4 h-4 text-slate-400" />
                Test Context (JSON Variables)
              </label>
              <textarea 
                className="flex-1 w-full border border-slate-200 rounded-lg p-3 text-sm font-mono text-slate-700 focus:ring-1 focus:ring-blue-500 outline-none resize-none shadow-inner bg-white" 
                value={testContext}
                onChange={(e) => setTestContext(e.target.value)}
                placeholder='{"main_keyword": "test"}'
              />
              <button 
                onClick={() => testMutation.mutate()}
                disabled={testMutation.isPending}
                className="mt-4 w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors font-medium shadow-sm disabled:opacity-50"
              >
                {testMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-white" />}
                {testMutation.isPending ? "Generating..." : "Run Agent"}
              </button>
           </div>
           
           <div className="flex-1 flex flex-col bg-white">
              <div className="px-5 py-3 border-b text-sm font-semibold text-slate-700 bg-slate-50/50 flex justify-between items-center">
                 Output Result
                 {result?.usage && (
                   <span className="text-xs font-mono text-slate-500 bg-white px-2 py-1 rounded border">
                     Tokens: {result.usage.total_tokens || '?'}
                   </span>
                 )}
              </div>
              <div className="flex-1 p-5 overflow-auto relative">
                 {testMutation.isPending && (
                   <div className="absolute inset-0 bg-white/50 flex flex-col items-center justify-center z-10 backdrop-blur-[1px]">
                     <Loader2 className="w-8 h-8 animate-spin text-blue-600 mb-2" />
                     <span className="text-sm text-slate-500 font-medium animate-pulse">Waiting for LLM response...</span>
                   </div>
                 )}
                 
                 {!result && !testMutation.isPending && (
                   <div className="h-full flex items-center justify-center">
                     <span className="text-slate-400 italic text-sm">Output will strictly appear here...</span>
                   </div>
                 )}
                 
                 {result && (
                   <div className="h-full rounded-lg border bg-slate-50 overflow-hidden font-mono text-sm leading-relaxed text-slate-800 relative">
                     <Editor
                       height="100%"
                       language={typeof result.output === 'object' ? 'json' : 'markdown'}
                       theme="vs-light"
                       value={typeof result.output === 'object' ? JSON.stringify(result.output, null, 2) : (result.output || result.error || JSON.stringify(result, null, 2))}
                       options={{ readOnly: true, minimap: { enabled: false }, wordWrap: "on", padding: { top: 16 } }}
                     />
                   </div>
                 )}
              </div>
           </div>
        </div>
      </div>
    </div>
  );
}
