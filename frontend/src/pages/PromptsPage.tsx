import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Editor from "@monaco-editor/react";
import toast from "react-hot-toast";
import { promptsApi } from "@/api/prompts";
import { Prompt } from "@/types/prompt";
import { Play, Save, Check } from "lucide-react";

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
                className={`w-full text-left px-3 py-2.5 rounded-md text-sm transition-colors ${
                  (activePromptId ? activePromptId === prompt.id : prompts[0].id === prompt.id)
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
        {activePrompt ? (
          <>
            <div className="p-4 border-b flex justify-between items-center bg-slate-50 rounded-t-lg shrink-0">
              <div>
                <h2 className="font-semibold text-slate-800 capitalize text-lg">{activePrompt.agent_name.replace(/_/g, " ")}</h2>
                <div className="text-xs text-slate-500 mt-1 flex gap-4">
                  <span className="flex items-center gap-1">Model: <span className="font-mono text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">{activePrompt.model}</span></span>
                  <span className="flex items-center">v{activePrompt.version}</span>
                  <span className="flex items-center">Tokens: {activePrompt.max_tokens}</span>
                </div>
              </div>
              <div className="flex gap-2">
                <label className="flex items-center gap-2 text-sm text-slate-700 mr-4 cursor-pointer">
                  <input 
                    type="checkbox" 
                    className="rounded border-slate-300"
                    checked={editState?.skip_in_pipeline || false}
                    onChange={(e) => setEditState(prev => prev ? {...prev, skip_in_pipeline: e.target.checked} : null)}
                  />
                  Skip in Pipeline
                </label>
                <button 
                  onClick={() => setIsTestOpen(true)}
                  className="flex items-center gap-2 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 px-3 py-1.5 rounded-md transition-colors text-sm font-medium border border-emerald-200 shadow-sm"
                >
                  <Play className="w-4 h-4" /> Test Prompt
                </button>
                <button 
                  onClick={() => editState && saveMutation.mutate(editState)}
                  disabled={saveMutation.isPending}
                  className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-5 py-1.5 rounded-md transition-colors text-sm font-medium shadow-sm disabled:opacity-70"
                >
                  <Save className="w-4 h-4" /> Save Changes
                </button>
              </div>
            </div>
            
            <div className="p-3 bg-slate-100 border-b text-xs flex gap-4 overflow-x-auto whitespace-nowrap scrollbar-hide">
               <span className="font-semibold text-slate-600">Variables:</span>
               {['{{main_keyword}}', '{{language}}', '{{country}}', '{{competitors_headers}}', '{{avg_word_count}}', '{{merged_markdown}}', '{{related_searches}}'].map(v => (
                 <span key={v} className="font-mono text-blue-700 bg-blue-50 px-1.5 rounded border border-blue-200">{v}</span>
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
                            value={editState?.system_prompt || ""}
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
                            value={editState?.user_prompt || ""}
                            onChange={(val) => setEditState(prev => prev ? {...prev, user_prompt: val || ""} : null)}
                            options={{ minimap: { enabled: false }, wordWrap: "on", padding: { top: 16 } }}
                        />
                    </div>
                </div>
            </div>

            {isTestOpen && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
                <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl p-6">
                  <h2 className="text-xl font-bold mb-4 text-slate-900">Test {activePrompt.agent_name}</h2>
                  <div className="space-y-4">
                     <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">Test Context (JSON)</label>
                        <textarea rows={5} className="w-full border rounded-md px-3 py-2 text-sm font-mono text-slate-700" placeholder='{"main_keyword": "test"}' defaultValue='{"main_keyword": "SEO test"}'></textarea>
                     </div>
                     <div className="bg-slate-50 border rounded p-4 h-48 overflow-auto">
                        <span className="text-slate-400 italic text-sm">Output will appear here...</span>
                     </div>
                  </div>
                  <div className="flex justify-end gap-3 mt-8">
                    <button 
                      onClick={() => setIsTestOpen(false)}
                      className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-md text-sm font-medium"
                    >
                      Close
                    </button>
                    <button 
                      className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-md hover:bg-emerald-700 text-sm font-medium"
                    >
                      <Play className="w-4 h-4" /> Run Test
                    </button>
                  </div>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-slate-500">Select an agent to view and edit prompts</div>
        )}
      </div>
    </div>
  );
}
