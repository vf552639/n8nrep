import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { Save, Settings2, Webhook, BoxSelect } from "lucide-react";
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
           <h1 className="text-3xl font-bold tracking-tight text-slate-900 border-l-4 border-slate-700 pl-3">Settings</h1>
           <p className="text-sm text-slate-500 mt-1 pl-4">Configure global application behavior and defaults.</p>
        </div>
        <button 
          onClick={() => saveMutation.mutate(settings)}
          disabled={saveMutation.isPending}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-lg transition-colors text-sm font-medium shadow-sm disabled:opacity-70"
        >
          <Save className="w-4 h-4" /> Save Settings
        </button>
      </div>

      <div className="flex gap-4 border-b">
        {[
          { id: "general", label: "General", icon: Settings2 },
          { id: "integrations", label: "Integrations", icon: Webhook },
          { id: "crawling", label: "Crawling", icon: BoxSelect }
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`pb-3 px-4 text-sm font-medium flex items-center gap-2 transition-colors border-b-2 ${
              activeTab === tab.id 
                ? "border-blue-600 text-blue-600" 
                : "border-transparent text-slate-500 hover:text-slate-800 hover:bg-slate-50 rounded-t-lg"
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      <div className="bg-white border rounded-xl shadow-sm p-6">
        {activeTab === "general" && (
          <div className="space-y-6 max-w-2xl">
             <h2 className="text-lg font-semibold text-slate-800 border-b pb-2">General Settings</h2>
             <div className="space-y-4 max-w-md">
                 <div>
                     <label className="block text-sm font-medium text-slate-700 mb-1">Default Global Model</label>
                     <select 
                        value={settings.DEFAULT_MODEL || "gpt-4o"}
                        onChange={(e) => setSettings({...settings, DEFAULT_MODEL: e.target.value})}
                        className="w-full border p-2.5 rounded-md text-sm outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50"
                     >
                         <option value="gpt-4o">gpt-4o</option>
                         <option value="claude-3-5-sonnet-20240620">claude-3.5-sonnet</option>
                         <option value="gpt-4-turbo">gpt-4-turbo</option>
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
                 <label className="flex items-center gap-2 text-sm text-slate-700 mt-4 cursor-pointer">
                    <input 
                      type="checkbox" 
                      className="rounded border-slate-300 w-4 h-4"
                      checked={settings.TEST_MODE === "true"}
                      onChange={(e) => setSettings({...settings, TEST_MODE: e.target.checked ? "true" : "false"})}
                    />
                    Enable Test Mode (Use Mock Responses)
                 </label>
             </div>
          </div>
        )}

        {activeTab === "integrations" && (
          <div className="space-y-6 max-w-2xl">
             <h2 className="text-lg font-semibold text-slate-800 border-b pb-2">Integrations Configuration</h2>
             <div className="space-y-5 max-w-md">
                 <div>
                     <label className="block text-sm font-medium text-slate-700 mb-1">Telegram Bot Token</label>
                     <input 
                       type="password" 
                       value={settings.TELEGRAM_BOT_TOKEN || ""} 
                       onChange={(e) => setSettings({...settings, TELEGRAM_BOT_TOKEN: e.target.value})}
                       className="w-full border p-2.5 rounded-md text-sm outline-none focus:ring-2 focus:ring-blue-500 font-mono" 
                       placeholder="123456789:ABCdefGHIjklMNOpqrSTUvwxYZ"
                     />
                 </div>
                 <div>
                     <label className="block text-sm font-medium text-slate-700 mb-1">DataForSEO API Login</label>
                     <input 
                       type="text" 
                       value={settings.DATAFORSEO_LOGIN || ""} 
                       onChange={(e) => setSettings({...settings, DATAFORSEO_LOGIN: e.target.value})}
                       className="w-full border p-2.5 rounded-md text-sm outline-none focus:ring-2 focus:ring-blue-500" 
                     />
                 </div>
                 <div>
                     <label className="block text-sm font-medium text-slate-700 mb-1">DataForSEO API Password</label>
                     <input 
                       type="password" 
                       value={settings.DATAFORSEO_PASSWORD || ""} 
                       onChange={(e) => setSettings({...settings, DATAFORSEO_PASSWORD: e.target.value})}
                       className="w-full border p-2.5 rounded-md text-sm outline-none focus:ring-2 focus:ring-blue-500 font-mono" 
                     />
                 </div>
                 <div>
                     <label className="block text-sm font-medium text-slate-700 mb-1">OpenAI API Key</label>
                     <input 
                       type="password" 
                       value={settings.OPENAI_API_KEY || ""} 
                       onChange={(e) => setSettings({...settings, OPENAI_API_KEY: e.target.value})}
                       className="w-full border p-2.5 rounded-md text-sm outline-none focus:ring-2 focus:ring-blue-500 font-mono" 
                       placeholder="sk-..."
                     />
                 </div>

                 <div className="pt-2">
                   <h3 className="text-sm font-semibold text-slate-800 mb-2">Image Generation</h3>

                   <label className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer mb-3">
                     <input
                       type="checkbox"
                       className="rounded border-slate-300 w-4 h-4"
                       checked={settings.IMAGE_GEN_ENABLED === "true"}
                       onChange={(e) => setSettings({ ...settings, IMAGE_GEN_ENABLED: e.target.checked ? "true" : "false" })}
                     />
                     Enable Image Generation in Pipeline
                   </label>

                   <div className="space-y-4">
                     <div>
                       <label className="block text-sm font-medium text-slate-700 mb-1">Default Image Model</label>
                       <input
                         type="text"
                         value={settings.IMAGE_MODEL_DEFAULT || ""}
                         onChange={(e) => setSettings({ ...settings, IMAGE_MODEL_DEFAULT: e.target.value })}
                         className="w-full border p-2.5 rounded-md text-sm outline-none focus:ring-2 focus:ring-blue-500 font-mono"
                         placeholder="google/gemini-2.5-flash-image-preview"
                       />
                       <p className="text-xs text-slate-400 mt-1">
                         Used when the Prompts → Image Generation (service) agent has no model set. Examples: google/gemini-2.5-flash-image-preview, black-forest-labs/flux-2-pro, sourceful/riverflow-v2-fast. See OpenRouter models with image output.
                       </p>
                     </div>

                     <div>
                       <label className="block text-sm font-medium text-slate-700 mb-1">ImgBB API Key</label>
                       <input
                         type="password"
                         value={settings.IMGBB_API_KEY || ""}
                         onChange={(e) => setSettings({ ...settings, IMGBB_API_KEY: e.target.value })}
                         className="w-full border p-2.5 rounded-md text-sm outline-none focus:ring-2 focus:ring-blue-500 font-mono"
                         placeholder="imgbb-..."
                       />
                       <p className="text-xs text-slate-400 mt-1">ImgBB is used for permanent image hosting.</p>
                     </div>
                   </div>
                 </div>
             </div>
          </div>
        )}

        {activeTab === "crawling" && (
          <div className="space-y-8 max-w-2xl">
            <div>
                <h2 className="text-lg font-semibold text-slate-800 border-b pb-2 mb-4">Excluded Domains</h2>
                <p className="text-sm text-slate-500 mb-2">Domains listed here will be filtered out from SERP results automatically. Separate by comma.</p>
                <textarea
                  className="w-full p-4 border rounded-lg text-sm font-mono outline-none focus:ring-2 focus:ring-blue-500 min-h-[120px]"
                  value={settings.EXCLUDED_DOMAINS || ""}
                  onChange={(e) => setSettings({...settings, EXCLUDED_DOMAINS: e.target.value})}
                  placeholder="e.g. reddit.com, quora.com..."
                />
            </div>
            
            <div>
                <h2 className="text-lg font-semibold text-slate-800 border-b pb-2 mb-4">Global Exclude Words</h2>
                <p className="text-sm text-slate-500 mb-2">These words will be checked against all generated texts. Separate by comma.</p>
                <textarea
                  className="w-full p-4 border rounded-lg text-sm font-mono outline-none focus:ring-2 focus:ring-blue-500 min-h-[120px]"
                  value={settings.EXCLUDE_WORDS || ""}
                  onChange={(e) => setSettings({...settings, EXCLUDE_WORDS: e.target.value})}
                  placeholder="e.g. gambling, violence..."
                />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
