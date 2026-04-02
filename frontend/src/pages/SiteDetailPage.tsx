import { useParams, useNavigate, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import Editor from "@monaco-editor/react";
import { sitesApi } from "@/api/sites";
import { templatesApi } from "@/api/templates";
import type { HtmlTemplate } from "@/types/template";
import type { HtmlTemplateInput } from "@/types/template";
import { ArrowLeft, Save, Pencil, Trash2, Plus, ExternalLink } from "lucide-react";
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

  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");
  const [country, setCountry] = useState("");
  const [language, setLanguage] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [templateId, setTemplateId] = useState<string | "">("");
  const [legalJson, setLegalJson] = useState("{}");

  const [tplModal, setTplModal] = useState<"add" | "edit" | null>(null);
  const [editingTplId, setEditingTplId] = useState<string | null>(null);
  const [tplForm, setTplForm] = useState<{ name: string; html: string; is_active: boolean; fileName: string }>({
    name: "",
    html: "",
    is_active: true,
    fileName: "",
  });

  useEffect(() => {
    if (!site) return;
    setName(site.name);
    setDomain(site.domain);
    setCountry(site.country);
    setLanguage(site.language);
    setIsActive(site.is_active);
    setTemplateId(site.template_id || "");
    setLegalJson(JSON.stringify(site.legal_info && Object.keys(site.legal_info).length ? site.legal_info : {}, null, 2));
  }, [site]);

  const { data: editingTemplate } = useQuery({
    queryKey: ["html-template", editingTplId],
    queryFn: () => templatesApi.getOne(editingTplId!),
    enabled: tplModal === "edit" && !!editingTplId,
  });

  useEffect(() => {
    if (tplModal === "edit" && editingTemplate) {
      setTplForm({
        name: editingTemplate.name,
        html: editingTemplate.html_template ?? "",
        is_active: editingTemplate.is_active,
        fileName: "",
      });
    }
    if (tplModal === "add") {
      setTplForm({ name: "", html: "<html><body>{{content}}</body></html>", is_active: true, fileName: "" });
    }
  }, [tplModal, editingTemplate]);

  const saveSiteMut = useMutation({
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
        name: name.trim(),
        domain: domain.trim(),
        country: country.trim().toUpperCase(),
        language: language.trim().toLowerCase(),
        is_active: isActive,
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

  const createTplMut = useMutation({
    mutationFn: () => {
      const body: HtmlTemplateInput = {
        name: tplForm.name.trim(),
        html_template: tplForm.html,
        is_active: tplForm.is_active,
      };
      return templatesApi.create(body);
    },
    onSuccess: () => {
      toast.success("Template created");
      queryClient.invalidateQueries({ queryKey: ["html-templates"] });
      setTplModal(null);
      setEditingTplId(null);
    },
    onError: (e: unknown) => {
      const ax = e as { response?: { data?: { detail?: string } } };
      toast.error(ax.response?.data?.detail || "Create failed");
    },
  });

  const updateTplMut = useMutation({
    mutationFn: () => {
      if (!editingTplId) throw new Error("no id");
      return templatesApi.update(editingTplId, {
        name: tplForm.name.trim(),
        html_template: tplForm.html,
        is_active: tplForm.is_active,
      });
    },
    onSuccess: () => {
      toast.success("Template saved");
      queryClient.invalidateQueries({ queryKey: ["html-templates"] });
      queryClient.invalidateQueries({ queryKey: ["html-template", editingTplId] });
      setTplModal(null);
      setEditingTplId(null);
    },
    onError: (e: unknown) => {
      const ax = e as { response?: { data?: { detail?: string } } };
      toast.error(ax.response?.data?.detail || "Update failed");
    },
  });

  const deleteTplMut = useMutation({
    mutationFn: (tplId: string) => templatesApi.delete(tplId),
    onSuccess: () => {
      toast.success("Template deleted");
      queryClient.invalidateQueries({ queryKey: ["html-templates"] });
    },
    onError: (e: unknown) => {
      const ax = e as { response?: { data?: { detail?: string } } };
      toast.error(ax.response?.data?.detail || "Delete failed");
    },
  });

  const openEdit = (tplId: string) => {
    setEditingTplId(tplId);
    setTplModal("edit");
  };

  const handleDeleteTemplate = (tpl: HtmlTemplate) => {
    if (
      !window.confirm(
        `Delete template "${tpl.name}"? Sites using it must be reassigned first (API will block otherwise).`
      )
    ) {
      return;
    }
    deleteTplMut.mutate(tpl.id);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      setTplForm((prev) => ({ ...prev, html: String(reader.result || ""), fileName: file.name }));
    };
    reader.readAsText(file);
  };

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
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Name</label>
              <input
                className="w-full rounded-lg border px-3 py-2 text-sm"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Domain</label>
              <input
                className="w-full rounded-lg border px-3 py-2 text-sm"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Country (ISO)</label>
              <input
                className="w-full rounded-lg border px-3 py-2 text-sm uppercase"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                maxLength={10}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Language</label>
              <input
                className="w-full rounded-lg border px-3 py-2 text-sm lowercase"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                maxLength={10}
              />
            </div>
          </div>

          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
            Active
          </label>

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
              Reusable shells are stored globally. You can add or edit templates in the section below or on the{" "}
              <Link to="/templates" className="text-blue-600 hover:underline">
                Templates
              </Link>{" "}
              page.
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
            onClick={() => saveSiteMut.mutate()}
            disabled={saveSiteMut.isPending}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            Save changes
          </button>
        </div>
      </div>

      <div className="rounded-lg border bg-white p-6 shadow-sm">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-slate-900">Global HTML templates</h2>
          <div className="flex gap-2">
            <Link
              to="/templates"
              className="inline-flex items-center gap-1 rounded-lg border px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
            >
              <ExternalLink className="h-4 w-4" /> Open Templates page
            </Link>
            <button
              type="button"
              onClick={() => {
                setEditingTplId(null);
                setTplModal("add");
              }}
              className="inline-flex items-center gap-1 rounded-lg bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800"
            >
              <Plus className="h-4 w-4" /> Add template
            </button>
          </div>
        </div>
        <p className="mb-4 text-sm text-slate-600">
          Templates are shared across all sites. Editing affects every site that uses this template shell.
        </p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {templates.map((t) => (
            <div key={t.id} className="rounded-lg border border-slate-200 bg-slate-50/50 p-4">
              <div className="font-medium text-slate-900">{t.name}</div>
              <div className="mt-1 text-xs text-slate-500">
                {typeof t.sites_count === "number" ? `${t.sites_count} site(s)` : ""}
                {t.is_active === false ? " · inactive" : ""}
              </div>
              <div className="mt-3 flex gap-2">
                <button
                  type="button"
                  onClick={() => openEdit(t.id)}
                  className="inline-flex flex-1 items-center justify-center gap-1 rounded border bg-white px-2 py-1.5 text-xs font-medium text-slate-800 hover:bg-slate-100"
                >
                  <Pencil className="h-3.5 w-3.5" /> Edit HTML
                </button>
                <button
                  type="button"
                  onClick={() => handleDeleteTemplate(t)}
                  disabled={deleteTplMut.isPending}
                  className="inline-flex items-center justify-center rounded border border-red-200 bg-white px-2 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {tplModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="flex max-h-[90vh] w-full max-w-4xl flex-col rounded-xl border bg-white shadow-xl">
            <div className="border-b px-4 py-3">
              <h3 className="text-lg font-semibold text-slate-900">
                {tplModal === "add" ? "Add template" : "Edit template"}
              </h3>
            </div>
            <div className="min-h-0 flex-1 space-y-3 overflow-auto p-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Template name</label>
                <input
                  className="w-full rounded-lg border px-3 py-2 text-sm"
                  value={tplForm.name}
                  onChange={(e) => setTplForm((p) => ({ ...p, name: e.target.value }))}
                  placeholder="e.g. Main site shell"
                />
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <label className="text-sm text-slate-700">
                  <span className="font-medium">Load from file</span>
                  <input
                    type="file"
                    accept=".html,.htm,text/html"
                    className="ml-2 text-sm"
                    onChange={handleFileUpload}
                  />
                </label>
                {tplForm.fileName && <span className="text-xs text-slate-500">{tplForm.fileName}</span>}
              </div>
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={tplForm.is_active}
                  onChange={(e) => setTplForm((p) => ({ ...p, is_active: e.target.checked }))}
                />
                Active
              </label>
              <div className="h-[min(50vh,420px)] overflow-hidden rounded-lg border">
                <Editor
                  height="100%"
                  defaultLanguage="html"
                  theme="vs"
                  value={tplForm.html}
                  onChange={(v) => setTplForm((p) => ({ ...p, html: v || "" }))}
                  options={{ minimap: { enabled: false }, wordWrap: "on" }}
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 border-t px-4 py-3">
              <button
                type="button"
                onClick={() => {
                  setTplModal(null);
                  setEditingTplId(null);
                }}
                className="rounded-lg border px-4 py-2 text-sm hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={
                  !tplForm.name.trim() ||
                  !tplForm.html.trim() ||
                  createTplMut.isPending ||
                  updateTplMut.isPending
                }
                onClick={() => (tplModal === "add" ? createTplMut.mutate() : updateTplMut.mutate())}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
