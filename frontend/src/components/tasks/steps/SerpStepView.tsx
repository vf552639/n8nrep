import { Download, ExternalLink } from "lucide-react";

const apiBase = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

type SerpSummary = {
  source?: string;
  organic_count?: number;
  paa_count?: number;
  related_count?: number;
  has_featured_snippet?: boolean;
  serp_features?: string[];
  urls?: string[];
};

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-center min-w-[100px]">
      <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="text-sm font-semibold text-slate-800">{value}</div>
    </div>
  );
}

export default function SerpStepView({ data, taskId }: { data: SerpSummary; taskId: string }) {
  const organic = data.organic_count ?? 0;
  const paa = data.paa_count ?? 0;
  const related = data.related_count ?? 0;
  const source = data.source ?? "—";
  const urls = Array.isArray(data.urls) ? data.urls : [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <Metric label="Source" value={source} />
        <Metric label="Organic" value={organic} />
        <Metric label="PAA" value={paa} />
        <Metric label="Related" value={related} />
        <Metric label="Featured Snippet" value={data.has_featured_snippet ? "Yes" : "No"} />
      </div>

      {Array.isArray(data.serp_features) && data.serp_features.length > 0 && (
        <div>
          <div className="text-xs font-semibold text-slate-600 mb-1.5">SERP features</div>
          <div className="flex flex-wrap gap-1.5">
            {data.serp_features.map((f) => (
              <span key={f} className="rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-800 border border-blue-100">
                {f}
              </span>
            ))}
          </div>
        </div>
      )}

      {urls.length > 0 && (
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
      )}

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
