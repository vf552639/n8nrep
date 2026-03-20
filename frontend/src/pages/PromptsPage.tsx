import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Editor from "@monaco-editor/react";
import api from "@/api/client";
import { Prompt } from "@/types/prompt";
import { Play } from "lucide-react";

export default function PromptsPage() {
  const [activePromptId, setActivePromptId] = useState<string | null>(null);

  const { data: prompts, isLoading } = useQuery({
    queryKey: ["prompts"],
    queryFn: async () => {
      const res = await api.get<Prompt[]>("/prompts");
      return res.data;
    },
  });

  const activePrompt = prompts?.find(p => p.id === activePromptId) || prompts?.[0];

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
                <button className="flex items-center gap-2 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 px-3 py-1.5 rounded-md transition-colors text-sm font-medium border border-emerald-200 shadow-sm">
                  <Play className="w-4 h-4" /> Test Prompt
                </button>
                <button className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-1.5 rounded-md transition-colors text-sm font-medium shadow-sm">
                  Save Changes
                </button>
              </div>
            </div>
            
            <div className="flex-1 flex flex-col xl:flex-row divide-y xl:divide-y-0 xl:divide-x overflow-hidden">
                <div className="flex-1 flex flex-col min-w-0">
                    <div className="p-2.5 bg-slate-100 text-xs font-bold text-slate-600 uppercase tracking-wider shrink-0 border-b">System Prompt</div>
                    <div className="flex-1 relative bg-[#fffffe]">
                        <Editor
                            height="100%"
                            language="markdown"
                            theme="vs-light"
                            value={activePrompt.system_prompt}
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
                            value={activePrompt.user_prompt}
                            options={{ minimap: { enabled: false }, wordWrap: "on", padding: { top: 16 } }}
                        />
                    </div>
                </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-slate-500">Select an agent to view and edit prompts</div>
        )}
      </div>
    </div>
  );
}
