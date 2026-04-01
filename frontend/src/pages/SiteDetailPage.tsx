import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import api from "@/api/client";
import { Site } from "@/types/site";
import type { SiteTemplateInput } from "@/types/site";
import { siteTemplatesApi, SiteTemplateListItem } from "@/api/siteTemplates";
import { ArrowLeft, Plus, Pencil, Trash2, Eye, X } from "lucide-react";
import Editor from "@monaco-editor/react";
import toast from "react-hot-toast";

function fillPreview(html: string, siteName: string): string {
  const content =
    "<h1>Preview Content</h1><p>This is a preview of the template layout.</p>";
  return html
    .replace(/\{\{\s*content\s*\}\}/gi, content)
    .replace(/\{\{\s*title\s*\}\}/gi, `Template Preview — ${siteName}`)
    .replace(/\{\{\s*description\s*\}\}/gi, "Preview meta description");
}

export default function SiteDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: sites, isLoading } = useQuery({
    queryKey: ["sites"],
    queryFn: async () => {
      const res = await api.get<Site[]>("/sites");
      return res.data;
    },
  });

  const site = sites?.find((s) => s.id === id);

  const { data: templates, isLoading: loadingTemplates } = useQuery({
    queryKey: ["site-templates", id],
    queryFn: () => (id ? siteTemplatesApi.getAll(id) : Promise.resolve([])),
    enabled: !!id,
  });

  const [modalMode, setModalMode] = useState<"create" | "edit" | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewHtml, setPreviewHtml] = useState("");

  const [form, setForm] = useState<SiteTemplateInput>({
    template_name: "",
    html_template: "",
    pages_config: {},
    is_active: true,
  });
  const [pagesJson, setPagesJson] = useState("{}");

  const openCreate = () => {
    setEditingId(null);
    setForm({
      template_name: "",
      html_template: "<!DOCTYPE html>\n<html><body>{{content}}</body></html>",
      pages_config: {},
      is_active: true,
    });
    setPagesJson("{}");
    setModalMode("create");
  };

  const openEdit = async (templateId: string) => {
    if (!id) return;
    try {
      const full = await siteTemplatesApi.getOne(id, templateId);
      setEditingId(templateId);
      setForm({
        template_name: full.template_name,
        html_template: full.html_template,
        pages_config: (full.pages_config as Record<string, unknown>) || {},
        is_active: full.is_active,
      });
      setPagesJson(JSON.stringify(full.pages_config || {}, null, 2));
      setModalMode("edit");
    } catch {
      toast.error("Failed to load template");
    }
  };

  const createMut = useMutation({
    mutationFn: () => {
      if (!id) throw new Error("no site");
      let pages: Record<string, unknown> | undefined;
      try {
        pages = pagesJson.trim() ? (JSON.parse(pagesJson) as Record<string, unknown>) : {};
      } catch {
        throw new Error("Invalid JSON in pages_config");
      }
      return siteTemplatesApi.create(id, {
        template_name: form.template_name,
        html_template: form.html_template,
        pages_config: pages,
        is_active: form.is_active ?? true,
      });
    },
    onSuccess: () => {
      toast.success("Template created");
      queryClient.invalidateQueries({ queryKey: ["site-templates", id] });
      setModalMode(null);
    },
    onError: (e: Error) => toast.error(e.message || "Create failed"),
  });

  const updateMut = useMutation({
    mutationFn: () => {
      if (!id || !editingId) throw new Error("no template");
      let pages: Record<string, unknown> | undefined;
      try {
        pages = pagesJson.trim() ? (JSON.parse(pagesJson) as Record<string, unknown>) : {};
      } catch {
        throw new Error("Invalid JSON in pages_config");
      }
      return siteTemplatesApi.update(id, editingId, {
        template_name: form.template_name,
        html_template: form.html_template,
        pages_config: pages,
        is_active: form.is_active,
      });
    },
    onSuccess: () => {
      toast.success("Template updated");
      queryClient.invalidateQueries({ queryKey: ["site-templates", id] });
      setModalMode(null);
    },
    onError: (e: Error) => toast.error(e.message || "Update failed"),
  });

  const deleteMut = useMutation({
    mutationFn: (templateId: string) => {
      if (!id) throw new Error("no site");
      return siteTemplatesApi.delete(id, templateId);
    },
    onSuccess: () => {
      toast.success("Template deleted");
      queryClient.invalidateQueries({ queryKey: ["site-templates", id] });
    },
    onError: () => toast.error("Delete failed"),
  });

  const toggleMut = useMutation({
    mutationFn: ({ templateId, is_active }: { templateId: string; is_active: boolean }) => {
      if (!id) throw new Error("no site");
      return siteTemplatesApi.update(id, templateId, { is_active });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["site-templates", id] }),
  });

  const handleSave = () => {
    if (!form.template_name.trim() || !form.html_template.trim()) {
      toast.error("Name and HTML template are required");
      return;
    }
    if (modalMode === "create") createMut.mutate();
    else updateMut.mutate();
  };

  const showPreview = (html: string) => {
    if (!site) return;
    setPreviewHtml(fillPreview(html, site.name));
    setPreviewOpen(true);
  };

  const tableRows = templates ?? [];

  if (isLoading) return <div className="p-6 text-slate-500">Loading site details...</div>;
  if (!site) return <div className="p-6 text-red-500">Site not found</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center bg-white p-4 rounded-lg shadow-sm border">
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={() => navigate("/sites")}
            className="p-2 hover:bg-slate-100 rounded-md transition-colors text-slate-500"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">Templates: {site.name}</h1>
            <div className="text-sm text-slate-500 mt-1 flex flex-wrap gap-3">
              <span>
                Domain:{" "}
                <a
                  href={`https://${site.domain}`}
                  className="text-blue-600 hover:underline"
                  target="_blank"
                  rel="noreferrer"
                >
                  {site.domain}
                </a>
              </span>
              <span>| Country: {site.country}</span>
              <span>| Lang: {site.language}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b bg-slate-50">
          <h2 className="text-lg font-semibold text-slate-900">HTML Templates</h2>
          <button
            type="button"
            onClick={openCreate}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" /> Add template
          </button>
        </div>

        <div className="p-4 overflow-x-auto">
          {loadingTemplates ? (
            <p className="text-sm text-slate-500">Loading templates...</p>
          ) : tableRows.length === 0 ? (
            <div className="text-center py-12 border-2 border-dashed rounded-lg">
              <p className="text-slate-500">No templates yet.</p>
              <button
                type="button"
                onClick={openCreate}
                className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
              >
                Create first template
              </button>
            </div>
          ) : (
            <table className="w-full text-sm text-left">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-2">Name</th>
                  <th className="px-3 py-2">Active</th>
                  <th className="px-3 py-2">Usage</th>
                  <th className="px-3 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {tableRows.map((t: SiteTemplateListItem) => (
                  <tr key={t.id} className="hover:bg-slate-50/80">
                    <td className="px-3 py-2 font-medium text-slate-800">{t.template_name}</td>
                    <td className="px-3 py-2">
                      <input
                        type="checkbox"
                        checked={t.is_active}
                        onChange={(e) =>
                          toggleMut.mutate({ templateId: t.id, is_active: e.target.checked })
                        }
                        className="rounded border-slate-300"
                      />
                    </td>
                    <td className="px-3 py-2 tabular-nums text-slate-600">{t.usage_count ?? 0}</td>
                    <td className="px-3 py-2 text-right space-x-2">
                      <button
                        type="button"
                        className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
                        onClick={async () => {
                          if (!id) return;
                          const full = await siteTemplatesApi.getOne(id, t.id);
                          showPreview(full.html_template);
                        }}
                      >
                        <Eye className="h-3.5 w-3.5" /> Preview
                      </button>
                      <button
                        type="button"
                        className="inline-flex items-center gap-1 text-xs text-slate-700 hover:underline"
                        onClick={() => openEdit(t.id)}
                      >
                        <Pencil className="h-3.5 w-3.5" /> Edit
                      </button>
                      <button
                        type="button"
                        className="inline-flex items-center gap-1 text-xs text-red-600 hover:underline"
                        onClick={() => {
                          if (window.confirm("Delete this template?")) deleteMut.mutate(t.id);
                        }}
                      >
                        <Trash2 className="h-3.5 w-3.5" /> Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {modalMode && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-4xl max-h-[95vh] flex flex-col border">
            <div className="flex items-center justify-between px-4 py-3 border-b">
              <h3 className="text-lg font-semibold">
                {modalMode === "create" ? "New template" : "Edit template"}
              </h3>
              <button type="button" onClick={() => setModalMode(null)} className="p-1 text-slate-500 hover:bg-slate-100 rounded">
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="p-4 space-y-3 overflow-y-auto flex-1 min-h-0">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Name *</label>
                <input
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.template_name}
                  onChange={(e) => setForm((f) => ({ ...f, template_name: e.target.value }))}
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  id="tpl-active"
                  type="checkbox"
                  checked={!!form.is_active}
                  onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
                />
                <label htmlFor="tpl-active" className="text-sm text-slate-700">
                  Active
                </label>
              </div>
              <p className="text-xs text-slate-500">
                Placeholders: <code className="bg-slate-100 px-1 rounded">{"{{content}}"}</code>,{" "}
                <code className="bg-slate-100 px-1 rounded">{"{{title}}"}</code>,{" "}
                <code className="bg-slate-100 px-1 rounded">{"{{description}}"}</code>
              </p>
              <div className="border rounded-lg overflow-hidden min-h-[280px]">
                <Editor
                  height="320px"
                  defaultLanguage="html"
                  theme="vs"
                  value={form.html_template}
                  onChange={(v) => setForm((f) => ({ ...f, html_template: v ?? "" }))}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">pages_config (JSON)</label>
                <textarea
                  className="w-full border rounded-lg px-3 py-2 text-xs font-mono min-h-[80px]"
                  value={pagesJson}
                  onChange={(e) => setPagesJson(e.target.value)}
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 px-4 py-3 border-t bg-slate-50">
              <button type="button" className="px-4 py-2 text-sm text-slate-700 hover:bg-slate-100 rounded-lg" onClick={() => setModalMode(null)}>
                Cancel
              </button>
              <button
                type="button"
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                onClick={handleSave}
                disabled={createMut.isPending || updateMut.isPending}
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {previewOpen && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-900/60 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-4xl h-[80vh] flex flex-col">
            <div className="flex justify-between items-center px-4 py-2 border-b">
              <span className="font-medium text-slate-800">Preview</span>
              <button type="button" onClick={() => setPreviewOpen(false)} className="p-1 text-slate-500">
                <X className="h-5 w-5" />
              </button>
            </div>
            <iframe title="preview" className="flex-1 w-full border-0" sandbox="" srcDoc={previewHtml} />
          </div>
        </div>
      )}
    </div>
  );
}
