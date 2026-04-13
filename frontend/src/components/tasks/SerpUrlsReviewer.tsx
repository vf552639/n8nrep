import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { tasksApi } from "@/api/tasks";
import { Trash2, Plus } from "lucide-react";

export type SerpUrlRow = {
  url: string;
  title: string;
  description: string;
  position: number;
  domain: string;
  manually_added: boolean;
};

type Props = {
  taskId: string;
  onApproved?: () => void;
};

function isValidHttpUrl(s: string): boolean {
  const t = s.trim();
  return t.startsWith("http://") || t.startsWith("https://");
}

export default function SerpUrlsReviewer({ taskId, onApproved }: Props) {
  const queryClient = useQueryClient();
  const [rows, setRows] = useState<SerpUrlRow[]>([]);
  const [newUrl, setNewUrl] = useState("");

  const { data, isLoading, isError } = useQuery({
    queryKey: ["task-serp-urls", taskId],
    queryFn: () => tasksApi.getSerpUrls(taskId),
    enabled: !!taskId,
  });

  useEffect(() => {
    if (data?.urls?.length) {
      setRows(data.urls as SerpUrlRow[]);
    } else if (data && Array.isArray(data.urls)) {
      setRows([]);
    }
  }, [data]);

  const approveMutation = useMutation({
    mutationFn: (urls: string[]) => tasksApi.approveSerpUrls(taskId, urls),
    onSuccess: (res) => {
      toast.success(res?.msg || "Pipeline resumed");
      queryClient.invalidateQueries({ queryKey: ["task", taskId] });
      queryClient.invalidateQueries({ queryKey: ["task-steps", taskId] });
      queryClient.invalidateQueries({ queryKey: ["task-serp-urls", taskId] });
      onApproved?.();
    },
    onError: (e: unknown) => {
      const ax = e as { response?: { data?: { detail?: string } } };
      toast.error(ax.response?.data?.detail || "Failed to approve URLs");
    },
  });

  const urlStrings = useMemo(() => rows.map((r) => r.url), [rows]);

  const handleAdd = () => {
    const u = newUrl.trim();
    if (!u) return;
    if (!isValidHttpUrl(u)) {
      toast.error("URL must start with http:// or https://");
      return;
    }
    if (rows.some((r) => r.url === u)) {
      toast.error("This URL is already in the list");
      return;
    }
    let domain = "";
    try {
      domain = new URL(u).hostname;
    } catch {
      domain = u;
    }
    setRows((prev) => [
      ...prev,
      {
        url: u,
        title: "",
        description: "",
        position: prev.length + 1,
        domain,
        manually_added: true,
      },
    ]);
    setNewUrl("");
  };

  const handleRemove = (url: string) => {
    setRows((prev) => prev.filter((r) => r.url !== url));
  };

  if (isLoading) {
    return (
      <div className="rounded-xl border border-sky-200 bg-sky-50 p-4 text-sm text-sky-800">Loading SERP URLs…</div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
        Could not load SERP URLs.
      </div>
    );
  }

  if (!data?.paused) {
    return null;
  }

  return (
    <div className="rounded-xl border border-sky-300 bg-sky-50 p-5 shadow-sm">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-sky-900">SERP URLs review</h2>
          <p className="mt-1 text-sm text-sky-800">
            Remove unwanted competitors or add URLs manually, then continue. Keyword:{" "}
            <span className="font-medium">{data.keyword}</span>
          </p>
        </div>
      </div>

      <p className="mb-3 text-sm font-medium text-sky-900">
        {rows.length} site{rows.length === 1 ? "" : "s"} will be analyzed
      </p>

      {rows.length === 0 && (
        <p className="mb-3 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          No URLs yet. Add at least one URL to continue (e.g. from Ahrefs).
        </p>
      )}

      <div className="max-h-[360px] overflow-auto rounded-lg border border-sky-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="sticky top-0 bg-slate-100 text-xs uppercase text-slate-600">
            <tr>
              <th className="px-3 py-2">#</th>
              <th className="px-3 py-2">Domain</th>
              <th className="px-3 py-2">Title</th>
              <th className="px-3 py-2">URL</th>
              <th className="w-12 px-2 py-2" />
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr key={row.url + idx} className="border-t border-slate-100">
                <td className="px-3 py-2 align-top text-slate-600">{row.position ?? idx + 1}</td>
                <td className="px-3 py-2 align-top text-slate-800">
                  <span className="inline-flex flex-wrap items-center gap-1">
                    {row.domain || "—"}
                    {row.manually_added ? (
                      <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-amber-900">
                        Manual
                      </span>
                    ) : null}
                  </span>
                </td>
                <td className="max-w-[200px] px-3 py-2 align-top text-slate-700">
                  <span className="line-clamp-2">{row.title || "—"}</span>
                </td>
                <td className="max-w-[280px] break-all px-3 py-2 align-top font-mono text-xs text-slate-600">
                  {row.url}
                </td>
                <td className="px-2 py-2 align-top">
                  <button
                    type="button"
                    onClick={() => handleRemove(row.url)}
                    className="rounded p-1.5 text-slate-500 hover:bg-red-50 hover:text-red-700"
                    title="Remove"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4 flex flex-wrap items-end gap-2">
        <div className="min-w-[200px] flex-1">
          <label className="mb-1 block text-xs font-medium text-sky-900">Add URL</label>
          <input
            type="url"
            value={newUrl}
            onChange={(e) => setNewUrl(e.target.value)}
            placeholder="https://example.com/page"
            className="w-full rounded-md border border-sky-200 px-3 py-2 text-sm shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
          />
        </div>
        <button
          type="button"
          onClick={handleAdd}
          className="inline-flex items-center gap-1 rounded-md bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700"
        >
          <Plus className="h-4 w-4" />
          Add
        </button>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button
          type="button"
          disabled={rows.length === 0 || approveMutation.isPending}
          onClick={() => approveMutation.mutate(urlStrings)}
          className="rounded-lg bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white shadow hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {approveMutation.isPending ? "Submitting…" : "Continue generation"}
        </button>
      </div>
    </div>
  );
}
