import { useState } from "react";
import { Download, ExternalLink } from "lucide-react";

const apiBase = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

type EngineData = {
  urls?: string[];
  organic_results?: any[];
  paa?: string[];
  related_searches?: string[];
  serp_features?: string[];
  ads_count?: number;
  people_also_search?: string[];
};

type SerpSummary = {
  source?: string;
  organic_count?: number;
  paa_count?: number;
  related_count?: number;
  has_featured_snippet?: boolean;
  ads_count?: number;
  people_also_search_count?: number;
  people_also_search?: string[];
  serp_features?: string[];
  urls?: string[];
  google_data?: EngineData;
  bing_data?: EngineData;
};

function Metric({ label, value, variant }: { label: string; value: string | number; variant?: "red" }) {
  return (
    <div
      className={`rounded-lg border px-3 py-2 text-center min-w-[100px] ${
        variant === "red"
          ? "border-red-200 bg-red-50"
          : "border-slate-200 bg-slate-50"
      }`}
    >
      <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`text-sm font-semibold ${variant === "red" ? "text-red-700" : "text-slate-800"}`}>
        {value}
      </div>
    </div>
  );
}

function UrlTable({ urls }: { urls: string[] }) {
  if (!urls.length) return null;
  return (
    <div>
      <div className="text-xs font-semibold text-slate-600 mb-2">URLs</div>
      <div className="max-h-64 overflow-auto rounded-lg border border-slate-200">
        <table className="w-full text-xs">
          <thead className="bg-slate-50 sticky top-0">
            <tr>
              <th className="px-3 py-2 text-left font-semibold text-slate-600">#</th>
              <th className="px-3 py-2 text-left font-semibold text-slate-600">URL</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {urls.map((u, i) => (
              <tr key={`${u}-${i}`} className="hover:bg-slate-50/80">
                <td className="px-3 py-1.5 text-slate-500 font-mono">{i + 1}</td>
                <td className="px-3 py-1.5">
                  <a
                    href={u}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-blue-600 hover:underline break-all"
                  >
                    {u}
                    <ExternalLink className="h-3 w-3 shrink-0 opacity-60" />
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function SerpStepView({ data, taskId }: { data: SerpSummary; taskId: string }) {
  const isGoogleBing = data.source === "google+bing";
  const [tab, setTab] = useState<"all" | "google" | "bing">("all");

  const getViewData = () => {
    if (!isGoogleBing || tab === "all") {
      return {
        urls: Array.isArray(data.urls) ? data.urls : [],
        organic: data.organic_count ?? 0,
        paa: data.paa_count ?? 0,
        related: data.related_count ?? 0,
        ads: data.ads_count ?? 0,
        pas: data.people_also_search_count ?? 0,
        pasItems: data.people_also_search ?? [],
        source: data.source ?? "—",
        features: data.serp_features ?? [],
      };
    }
    const ed = tab === "google" ? data.google_data : data.bing_data;
    if (!ed) return null;
    return {
      urls: ed.urls ?? [],
      organic: ed.organic_results?.length ?? 0,
      paa: ed.paa?.length ?? 0,
      related: ed.related_searches?.length ?? 0,
      ads: ed.ads_count ?? 0,
      pas: ed.people_also_search?.length ?? 0,
      pasItems: ed.people_also_search ?? [],
      source: tab,
      features: ed.serp_features ?? [],
    };
  };

  const v = getViewData();
  if (!v) return <div className="text-sm text-slate-400 italic">No data for this engine</div>;

  return (
    <div className="space-y-4">
      {/* Engine tabs (only for google+bing) */}
      {isGoogleBing && (
        <div className="flex gap-1">
          {(["all", "google", "bing"] as const).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTab(t)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors capitalize ${
                tab === t
                  ? "bg-blue-600 text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {t === "all" ? "All (Merged)" : t === "google" ? "🔍 Google" : "🅱 Bing"}
            </button>
          ))}
        </div>
      )}

      {/* Metrics */}
      <div className="flex flex-wrap gap-2">
        <Metric label="Source" value={v.source} />
        <Metric label="Organic" value={v.organic} />
        <Metric label="PAA" value={v.paa} />
        <Metric label="Related" value={v.related} />
        <Metric label="Featured Snippet" value={data.has_featured_snippet ? "Yes" : "No"} />
        <Metric label="Ads" value={v.ads} variant={v.ads > 0 ? "red" : undefined} />
        {v.pas > 0 && <Metric label="PAS" value={v.pas} />}
      </div>

      {/* SERP features */}
      {v.features.length > 0 && (
        <div>
          <div className="text-xs font-semibold text-slate-600 mb-1.5">SERP features</div>
          <div className="flex flex-wrap gap-1.5">
            {v.features.map((f) => (
              <span
                key={f}
                className={`rounded-full px-2 py-0.5 text-xs font-medium border ${
                  f === "paid"
                    ? "bg-red-50 text-red-800 border-red-100"
                    : "bg-blue-50 text-blue-800 border-blue-100"
                }`}
              >
                {f}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* URLs table */}
      <UrlTable urls={v.urls} />

      {/* People Also Search */}
      {v.pasItems.length > 0 && (
        <div>
          <div className="text-xs font-semibold text-slate-600 mb-1.5">People also search</div>
          <div className="flex flex-wrap gap-1.5">
            {v.pasItems.map((q, i) => (
              <span
                key={i}
                className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-700 border border-slate-200"
              >
                {q}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Download */}
      <div className="flex justify-end">
        <a
          href={`${apiBase}/tasks/${taskId}/serp-export`}
          className="inline-flex items-center gap-2 rounded-md border border-blue-200 bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-800 hover:bg-blue-100"
        >
          <Download className="h-4 w-4" />
          Download SERP ZIP
        </a>
      </div>
    </div>
  );
}
