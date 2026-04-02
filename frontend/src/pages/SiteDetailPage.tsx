import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { sitesApi } from "@/api/sites";
import { templatesApi } from "@/api/templates";
import type { HtmlTemplate } from "@/types/template";
import { ArrowLeft, Save } from "lucide-react";
import toast from "react-hot-toast";

export default function SiteDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: site, isLoading } = useQuery({
    queryKey: ["site", id],
    queryFn: () => (id ? sitesApi.getOne(id) : Promise.reject()),
    enabled: !!id,
  });

  const { data: templateList } = useQuery({
    queryKey: ["html-templates"],
    queryFn: () => templatesApi.getAll(),
  });

  const [templateId, setTemplateId] = useState<string | "">("");
  const [legalJson, setLegalJson] = useState("{}");

  useEffect(() => {
    if (!site) return;
    setTemplateId(site.template_id || "");
    setLegalJson(JSON.stringify(site.legal_info && Object.keys(site.legal_info).length ? site.legal_info : {}, null, 2));
  }, [site]);

  const saveMut = useMutation({
    mutationFn: async () => {
      if (!id) throw new Error("no id");
      let legal_info: Record<string, string> | undefined;
      try {
        const parsed = JSON.parse(legalJson || "{}");
        if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
          legal_info = parsed as Record<string, string>;
        } else {
          throw new Error("Legal info must be a JSON object");
        }
      } catch (e) {
        throw new Error(e instanceof Error ? e.message : "Invalid JSON");
      }
      return sitesApi.update(id, {
        template_id: templateId || null,
        legal_info,
      });
    },
    onSuccess: () => {
      toast.success("Site updated");
      queryClient.invalidateQueries({ queryKey: ["site", id] });
      queryClient.invalidateQueries({ queryKey: ["sites"] });
      queryClient.invalidateQueries({ queryKey: ["html-templates"] });
    },
    onError: (e: Error) => toast.error(e.message || "Save failed"),
  });

  if (isLoading) return <div className="p-6 text-slate-500">Loading site...</div>;
  if (!site) return <div className="p-6 text-red-500">Site not found</div>;

  const templates = (templateList || []) as HtmlTemplate[];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4 rounded-lg border bg-white p-4 shadow-sm">
        <button
          type="button"
          onClick={() => navigate("/sites")}
          className="rounded-md p-2 text-slate-500 hover:bg-slate-100"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{site.name}</h1>
          <p className="mt-1 text-sm text-slate-500">
            <a href={`https://${site.domain}`} className="text-blue-600 hover:underline" target="_blank" rel="noreferrer">
              {site.domain}
            </a>
            <span className="mx-2">|</span>
            {site.country} / {site.language}
          </p>
        </div>
      </div>

      <div className="rounded-lg border bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold text-slate-900">Site settings</h2>

        <div className="max-w-xl space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">HTML Template</label>
            <select
              className="w-full rounded-lg border px-3 py-2 text-sm"
              value={templateId}
              onChange={(e) => setTemplateId(e.target.value)}
            >
              <option value="">— None —</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                  {typeof t.sites_count === "number" ? ` (${t.sites_count} sites)` : ""}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-slate-500">
              Manage reusable shells under <span className="font-medium">Templates</span> in the sidebar.
            </p>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Legal info (JSON)</label>
            <p className="mb-1 text-xs text-slate-500">
              Used when generating legal pages: company_name, contact_email, address, etc.
            </p>
            <textarea
              className="min-h-[160px] w-full rounded-lg border px-3 py-2 font-mono text-xs"
              value={legalJson}
              onChange={(e) => setLegalJson(e.target.value)}
            />
          </div>

          <button
            type="button"
            onClick={() => saveMut.mutate()}
            disabled={saveMut.isPending}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            Save changes
          </button>
        </div>
      </div>
    </div>
  );
}
