import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import toast from "react-hot-toast";
import Editor from "@monaco-editor/react";
import { templatesApi } from "@/api/templates";
import type { HtmlTemplate, HtmlTemplateInput } from "@/types/template";
import { ReactTable } from "@/components/common/ReactTable";
import { Plus, Pencil, Trash2, Eye, X, FileCode } from "lucide-react";

function fillPreview(html: string, name: string): string {
  const content = "<h1>Preview</h1><p>Sample content for layout check.</p>";
  return html
    .replace(/\{\{\s*content\s*\}\}/gi, content)
    .replace(/\{\{\s*title\s*\}\}/gi, `Preview — ${name}`)
    .replace(/\{\{\s*description\s*\}\}/gi, "Preview meta description");
}

export default function TemplatesPage() {
  const queryClient = useQueryClient();
  const [modalMode, setModalMode] = useState<"create" | "edit" | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewHtml, setPreviewHtml] = useState("");

  const [form, setForm] = useState<HtmlTemplateInput>({
    name: "",
    html_template: "<!DOCTYPE html>\n<html><body>{{content}}</body></html>",
    description: "",
    is_active: true,
  });

  const { data: rows, isLoading } = useQuery({
    queryKey: ["html-templates"],
    queryFn: () => templatesApi.getAll(),
  });

  const openCreate = () => {
    setEditingId(null);
    setForm({
      name: "",
      html_template: "<!DOCTYPE html>\n<html><body>{{content}}</body></html>",
      description: "",
      is_active: true,
    });
    setModalMode("create");
  };

  const openEdit = async (id: string) => {
    try {
      const full = await templatesApi.getOne(id);
      setEditingId(id);
      setForm({
        name: full.name,
        html_template: full.html_template ?? "",
        description: full.description || "",
        preview_screenshot: full.preview_screenshot || undefined,
        is_active: full.is_active,
      });
      setModalMode("edit");
    } catch {
      toast.error("Failed to load template");
    }
  };

  const createMut = useMutation({
    mutationFn: () => templatesApi.create(form),
    onSuccess: () => {
      toast.success("Template created");
      queryClient.invalidateQueries({ queryKey: ["html-templates"] });
      setModalMode(null);
    },
  });

  const updateMut = useMutation({
    mutationFn: () => {
      if (!editingId) throw new Error("no id");
      return templatesApi.update(editingId, form);
    },
    onSuccess: () => {
      toast.success("Template updated");
      queryClient.invalidateQueries({ queryKey: ["html-templates"] });
      setModalMode(null);
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => templatesApi.delete(id),
    onSuccess: () => {
      toast.success("Template deleted");
      queryClient.invalidateQueries({ queryKey: ["html-templates"] });
    },
  });

  const handleSave = () => {
    if (!form.name.trim() || !form.html_template.trim()) {
      toast.error("Name and HTML are required");
      return;
    }
    if (modalMode === "create") createMut.mutate();
    else updateMut.mutate();
  };

  const showPreview = async (row: { id: string; name: string }) => {
    const full = await templatesApi.getOne(row.id);
    setPreviewHtml(fillPreview(full.html_template ?? "", full.name ?? ""));
    setPreviewOpen(true);
  };

  const columns = [
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }: { row: { original: HtmlTemplate } }) => (
        <div className="flex items-center gap-2 font-medium text-slate-800">
          <FileCode className="h-4 w-4 text-slate-400" />
          {row.original.name}
        </div>
      ),
    },
    {
      accessorKey: "sites_count",
      header: "Sites using",
      cell: ({ row }: { row: { original: HtmlTemplate } }) => (
        <span className="tabular-nums text-slate-700">{row.original.sites_count ?? 0}</span>
      ),
    },
    {
      accessorKey: "is_active",
      header: "Active",
      cell: ({ row }: { row: { original: HtmlTemplate } }) => (
        <span
          className={`rounded px-2 py-0.5 text-xs font-medium ${
            row.original.is_active ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-600"
          }`}
        >
          {row.original.is_active ? "Yes" : "No"}
        </span>
      ),
    },
    {
      id: "actions",
      header: "Actions",
      enableSorting: false,
      meta: { tdClassName: "text-right" },
      cell: ({ row }: { row: { original: HtmlTemplate } }) => (
        <div className="flex justify-end gap-2">
          <button
            type="button"
            className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
            onClick={(e) => {
              e.stopPropagation();
              showPreview(row.original);
            }}
          >
            <Eye className="h-3.5 w-3.5" /> Preview
          </button>
          <button
            type="button"
            className="inline-flex items-center gap-1 text-xs text-slate-700 hover:underline"
            onClick={(e) => {
              e.stopPropagation();
              openEdit(row.original.id);
            }}
          >
            <Pencil className="h-3.5 w-3.5" /> Edit
          </button>
          <button
            type="button"
            className="inline-flex items-center gap-1 text-xs text-red-600 hover:underline"
            onClick={(e) => {
              e.stopPropagation();
              if (window.confirm("Delete this template?")) deleteMut.mutate(row.original.id);
            }}
          >
            <Trash2 className="h-3.5 w-3.5" /> Delete
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 rounded-xl border bg-white p-5 shadow-sm sm:flex-row sm:items-center">
        <div>
          <h1 className="border-l-4 border-blue-500 pl-3 text-2xl font-bold tracking-tight text-slate-900">
            HTML Templates
          </h1>
          <p className="mt-1 pl-4 text-sm text-slate-500">
            Reusable page shells. Assign a template to each site under Sites.
          </p>
        </div>
        <button
          type="button"
          onClick={openCreate}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700"
        >
          <Plus className="h-4 w-4" /> Add template
        </button>
      </div>

      <ReactTable columns={columns as never} data={rows || []} isLoading={isLoading} />

      {modalMode && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
          <div className="flex max-h-[95vh] w-full max-w-4xl flex-col overflow-hidden rounded-xl border bg-white shadow-xl">
            <div className="flex items-center justify-between border-b px-4 py-3">
              <h3 className="text-lg font-semibold">
                {modalMode === "create" ? "Add New Template" : "Edit Template"}
              </h3>
              <button
                type="button"
                onClick={() => setModalMode(null)}
                className="rounded p-1 text-slate-500 hover:bg-slate-100"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Template Name *</label>
                <input
                  className="w-full rounded-lg border px-3 py-2 text-sm"
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Description</label>
                <textarea
                  className="min-h-[72px] w-full rounded-lg border px-3 py-2 text-sm"
                  value={form.description || ""}
                  onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                  placeholder="Optional notes"
                />
              </div>
              <p className="text-xs text-slate-500">
                Placeholders: <code className="rounded bg-slate-100 px-1">{"{{content}}"}</code>,{" "}
                <code className="rounded bg-slate-100 px-1">{"{{title}}"}</code>,{" "}
                <code className="rounded bg-slate-100 px-1">{"{{description}}"}</code>
              </p>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">HTML Template *</label>
                <div className="overflow-hidden rounded-lg border">
                  <Editor
                    height="320px"
                    defaultLanguage="html"
                    theme="vs"
                    value={form.html_template}
                    onChange={(v) => setForm((f) => ({ ...f, html_template: v ?? "" }))}
                  />
                </div>
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={!!form.is_active}
                  onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
                />
                Active
              </label>
            </div>
            <div className="flex justify-end gap-2 border-t bg-slate-50 px-4 py-3">
              <button
                type="button"
                className="rounded-lg px-4 py-2 text-sm text-slate-700 hover:bg-slate-100"
                onClick={() => setModalMode(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
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
          <div className="flex h-[80vh] w-full max-w-4xl flex-col rounded-xl bg-white shadow-xl">
            <div className="flex items-center justify-between border-b px-4 py-2">
              <span className="font-medium text-slate-800">Preview</span>
              <button type="button" onClick={() => setPreviewOpen(false)} className="p-1 text-slate-500">
                <X className="h-5 w-5" />
              </button>
            </div>
            <iframe title="preview" className="min-h-0 flex-1 w-full border-0" sandbox="" srcDoc={previewHtml} />
          </div>
        </div>
      )}
    </div>
  );
}
