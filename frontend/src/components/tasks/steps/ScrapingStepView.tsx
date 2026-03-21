type FailedRow = { url?: string; domain?: string; error?: string };

type ScrapeSummary = {
  total_from_serp?: number;
  total_attempted?: number;
  successful?: number;
  failed?: number;
  avg_word_count?: number;
  serper_count?: number;
  scraped_domains?: string[];
  failed_results?: FailedRow[];
};

function Metric({
  label,
  value,
  variant,
}: {
  label: string;
  value: string | number;
  variant?: "default" | "danger" | "success";
}) {
  const border =
    variant === "danger"
      ? "border-red-200 bg-red-50"
      : variant === "success"
        ? "border-emerald-200 bg-emerald-50"
        : "border-slate-200 bg-slate-50";
  const text =
    variant === "danger" ? "text-red-800" : variant === "success" ? "text-emerald-800" : "text-slate-800";
  return (
    <div className={`rounded-lg border px-3 py-2 text-center min-w-[96px] ${border}`}>
      <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`text-sm font-semibold ${text}`}>{value}</div>
    </div>
  );
}

export default function ScrapingStepView({ data }: { data: ScrapeSummary }) {
  const fromSerp = data.total_from_serp ?? 0;
  const attempted = data.total_attempted ?? 0;
  const success = data.successful ?? 0;
  const failed = data.failed ?? Math.max(0, attempted - success);
  const avgWords = data.avg_word_count != null ? Number(data.avg_word_count).toFixed(0) : "—";
  const serper = data.serper_count ?? 0;
  const domains = Array.isArray(data.scraped_domains) ? data.scraped_domains : [];
  const failedRows = Array.isArray(data.failed_results) ? data.failed_results : [];
  const pct = attempted > 0 ? Math.round((success / attempted) * 100) : 0;
  const successVariant = attempted > 0 && success === attempted ? "success" : "default";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <Metric label="From SERP" value={fromSerp} />
        <Metric
          label="Scraped"
          value={`${success} / ${attempted}${attempted ? ` (${pct}%)` : ""}`}
          variant={successVariant}
        />
        <Metric label="Errors" value={failed} variant={failed > 0 ? "danger" : "default"} />
        <Metric label="Avg words" value={avgWords} />
        <Metric label="Serper" value={serper} />
      </div>

      {failedRows.length > 0 && (
        <div className="rounded-lg border-2 border-red-200 bg-red-50/40 overflow-hidden">
          <div className="bg-red-100/80 px-3 py-2 text-xs font-semibold text-red-900">Failed results</div>
          <div className="max-h-56 overflow-auto">
            <table className="w-full text-xs">
              <thead className="bg-red-50 sticky top-0">
                <tr>
                  <th className="px-2 py-1.5 text-left text-red-900">URL</th>
                  <th className="px-2 py-1.5 text-left text-red-900">Domain</th>
                  <th className="px-2 py-1.5 text-left text-red-900">Error</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-red-100 bg-white">
                {failedRows.map((row, i) => (
                  <tr key={i}>
                    <td className="px-2 py-1.5 break-all text-slate-800">{row.url ?? "—"}</td>
                    <td className="px-2 py-1.5 text-slate-700">{row.domain ?? "—"}</td>
                    <td className="px-2 py-1.5 text-red-700">{row.error ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {domains.length > 0 && (
        <div>
          <div className="text-xs font-semibold text-slate-600 mb-1.5">Scraped domains</div>
          <div className="flex flex-wrap gap-1.5">
            {domains.map((d) => (
              <span
                key={d}
                className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-mono text-slate-700 border border-slate-200"
              >
                {d}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
