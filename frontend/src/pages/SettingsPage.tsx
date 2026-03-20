import { useState } from "react";
import { Save } from "lucide-react";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("general");
  const [globalExcludeWords, setGlobalExcludeWords] = useState("gambling, casino, porn");
  const [excludedDomains, setExcludedDomains] = useState("example.com, spam.org");

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex justify-between items-center">
        <div>
           <h1 className="text-3xl font-bold tracking-tight text-slate-900">Settings</h1>
           <p className="text-sm text-slate-500 mt-1">Configure global application behavior and defaults.</p>
        </div>
        <button className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-lg transition-colors text-sm font-medium shadow-sm">
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
                     <input type="number" defaultValue={5} className="w-full border p-2.5 rounded-md text-sm outline-none focus:ring-2 focus:ring-blue-500" />
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
              value={globalExcludeWords}
              onChange={(e) => setGlobalExcludeWords(e.target.value)}
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
              value={excludedDomains}
              onChange={(e) => setExcludedDomains(e.target.value)}
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
