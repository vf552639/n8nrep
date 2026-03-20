import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { Save } from "lucide-react";
import api from "@/api/client";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("general");
  const [settings, setSettings] = useState<Record<string, string>>({});

  const { data, isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: async () => {
      const res = await api.get<Record<string, string>>("/settings");
      return res.data;
    }
  });

  useEffect(() => {
    if (data) {
      setSettings(data);
    }
  }, [data]);

  const saveMutation = useMutation({
    mutationFn: (newSettings: Record<string, string>) => api.put("/settings", newSettings),
    onSuccess: () => toast.success("Settings saved! Restart backend to apply API keys change."),
    onError: () => toast.error("Failed to save settings.")
  });

  if (isLoading) return <div className="p-6 text-slate-500">Loading settings...</div>;

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex justify-between items-center">
        <div>
           <h1 className="text-3xl font-bold tracking-tight text-slate-900">Settings</h1>
           <p className="text-sm text-slate-500 mt-1">Configure global application behavior and defaults.</p>
        </div>
        <button 
          onClick={() => saveMutation.mutate(settings)}
          disabled={saveMutation.isPending}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-lg transition-colors text-sm font-medium shadow-sm disabled:opacity-70"
        >
          <Save className="w-4 h-4" /> Save Settings
        </button>
      </div>

      <div className="flex gap-2 border-b">
        {["general", "exclude_words", "excluded_domains", "api_keys"].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`pb-3 px-4 text-sm font-medium capitalize transition-colors border-b-2 ${
              activeTab === tab 
                ? "border-blue-600 text-blue-600" 
                : "border-transparent text-slate-500 hover:text-slate-800 hover:bg-slate-50 rounded-t-lg"
            }`}
          >
            {tab.replace("_", " ")}
          </button>
        ))}
      </div>

      <div className="bg-white border rounded-xl shadow-sm p-6">
        {activeTab === "general" && (
          <div className="space-y-6 max-w-2xl">
             <h2 className="text-lg font-semibold text-slate-800 border-b pb-2">General Settings</h2>
             <div className="space-y-4">
                 <div>
                     <label className="block text-sm font-medium text-slate-700 mb-1">Default Model</label>
                     <select className="w-full border p-2.5 rounded-md text-sm outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50">
                         <option>anthropic/claude-3.5-sonnet:beta</option>
                         <option>openai/gpt-4o</option>
                     </select>
                 </div>
                 <div>
                     <label className="block text-sm font-medium text-slate-700 mb-1">Max Concurrent Celery Workers</label>
                     <input 
                       type="number" 
                       value={settings.CELERY_CONCURRENCY || ""} 
                       onChange={(e) => setSettings({...settings, CELERY_CONCURRENCY: e.target.value})}
                       className="w-full border p-2.5 rounded-md text-sm outline-none focus:ring-2 focus:ring-blue-500" 
                     />
                 </div>
             </div>
          </div>
        )}

        {activeTab === "exclude_words" && (
          <div className="space-y-4 max-w-2xl">
            <h2 className="text-lg font-semibold text-slate-800 border-b pb-2">Global Exclude Words Editor</h2>
            <p className="text-sm text-slate-500">These words will be checked against all generated texts across all authors. Separate by comma.</p>
            <textarea
              className="w-full p-4 border rounded-lg text-sm font-mono outline-none focus:ring-2 focus:ring-blue-500 min-h-[200px]"
              value={settings.EXCLUDE_WORDS || ""}
              onChange={(e) => setSettings({...settings, EXCLUDE_WORDS: e.target.value})}
              placeholder="e.g. gambling, violence..."
            />
          </div>
        )}

        {activeTab === "excluded_domains" && (
          <div className="space-y-4 max-w-2xl">
            <h2 className="text-lg font-semibold text-slate-800 border-b pb-2">Excluded Domains Editor</h2>
            <p className="text-sm text-slate-500">Domains listed here will be filtered out from SERP results automatically.</p>
            <textarea
              className="w-full p-4 border rounded-lg text-sm font-mono outline-none focus:ring-2 focus:ring-blue-500 min-h-[200px]"
              value={settings.EXCLUDED_DOMAINS || ""}
              onChange={(e) => setSettings({...settings, EXCLUDED_DOMAINS: e.target.value})}
              placeholder="e.g. reddit.com, quora.com..."
            />
          </div>
        )}

        {activeTab === "api_keys" && (
          <div className="space-y-4 text-center py-10">
              <p className="text-slate-500">API keys are managed via backend `.env` variables.</p>
          </div>
        )}
      </div>
    </div>
  );
}
