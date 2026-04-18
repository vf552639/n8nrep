import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import toast from "react-hot-toast";
import Editor from "@monaco-editor/react";
import { legalPagesApi } from "@/api/legalPages";
import type { LegalPageTemplateRow, LegalPageType } from "@/types/template";
import { LEGAL_PAGE_TYPE_LABELS } from "@/types/template";
import { ReactTable } from "@/components/common/ReactTable";
import { Plus, Pencil, Trash2, X } from "lucide-react";

const FALLBACK_PAGE_TYPES = Object.keys(LEGAL_PAGE_TYPE_LABELS);

export default function LegalPagesPage() {
  const queryClient = useQueryClient();
  const [pageTypeFilter, setPageTypeFilter] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  const [form, setForm] = useState({
    name: "",
    page_type: "privacy_policy" as LegalPageType | string,
    content: "",
    content_format: "text" as "text" | "html",
    variablesJson: "{}",
    notes: "",
    is_active: true,
  });

  const { data: pageTypes } = useQuery({
    queryKey: ["legal-page-types"],
    queryFn: () => legalPagesApi.getPageTypes(),
  });

  const { data: rows, isLoading } = useQuery({
    queryKey: ["legal-pages", pageTypeFilter],
    queryFn: () => legalPagesApi.getAll(pageTypeFilter || undefined),
  });

  const openCreate = () => {
    setEditingId(null);
    setForm({
      name: "",
      page_type: "privacy_policy",
      content: "",
      content_format: "text",
      variablesJson: "{}",
      notes: "",
      is_active: true,
    });
    setModalOpen(true);
  };

  const openEdit = async (id: string) => {
    try {
      const full = await legalPagesApi.getOne(id);
      setEditingId(id);
      setForm({
        name: full.name,
        page_type: full.page_type,
        content: full.content,
        content_format: (full.content_format === "html" ? "html" : "text") as "text" | "html",
        variablesJson: JSON.stringify(full.variables || {}, null, 2),
        notes: full.notes || "",
        is_active: full.is_active,
      });
      setModalOpen(true);
    } catch {
      toast.error("Failed to load");
    }
  };

  const saveMut = useMutation({
    mutationFn: async () => {
      let variables: Record<string, unknown> = {};
      try {
        variables = form.variablesJson.trim() ? JSON.parse(form.variablesJson) : {};
      } catch {
        throw new Error("Invalid JSON in Variables");
      }
      if (editingId) {
        return legalPagesApi.update(editingId, {
          name: form.name,
          page_type: form.page_type,
          content: form.content,
          content_format: form.content_format,
          variables,
          notes: form.notes || null,
          is_active: form.is_active,
        });
      }
      return legalPagesApi.create({
        name: form.name,
        page_type: form.page_type,
        content: form.content,
        content_format: form.content_format,
        variables,
        notes: form.notes || null,
        is_active: form.is_active,
      });
    },
    onSuccess: () => {
      toast.success(editingId ? "Updated" : "Created");
      queryClient.invalidateQueries({ queryKey: ["legal-pages"] });
      setModalOpen(false);
    },
    onError: (e: Error) => toast.error(e.message || "Save failed"),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => legalPagesApi.delete(id),
    onSuccess: () => {
      toast.success("Deleted");
      queryClient.invalidateQueries({ queryKey: ["legal-pages"] });
    },
  });

  const columns = [
    { accessorKey: "name", header: "Name" },
    {
      accessorKey: "page_type",
      header: "Page type",
      cell: ({ row }: { row: { original: LegalPageTemplateRow } }) => (
        <span>{LEGAL_PAGE_TYPE_LABELS[row.original.page_type] || row.original.page_type}</span>
      ),
    },
    {
      accessorKey: "content_format",
      header: "Format",
      cell: ({ row }: { row: { original: LegalPageTemplateRow } }) => (
        <span className="text-xs uppercase text-slate-600">{row.original.content_format}</span>
      ),
    },
    {
      accessorKey: "is_active",
      header: "Active",
      cell: ({ row }: { row: { original: LegalPageTemplateRow } }) => (
        <span className={row.original.is_active ? "text-emerald-700" : "text-slate-500"}>
          {row.original.is_active ? "Yes" : "No"}
        </span>
      ),
    },
    {
      id: "actions",
      header: "Actions",
      enableSorting: false,
      meta: { tdClassName: "text-right" },
      cell: ({ row }: { row: { original: LegalPageTemplateRow } }) => (
        <div className="flex justify-end gap-2">
          <button
            type="button"
            className="text-xs text-blue-600 hover:underline"
            onClick={(e) => {
              e.stopPropagation();
              openEdit(row.original.id);
            }}
          >
            <Pencil className="mr-1 inline h-3 w-3" /> Edit
          </button>
          <button
            type="button"
            className="text-xs text-red-600 hover:underline"
            onClick={(e) => {
              e.stopPropagation();
              if (window.confirm("Delete?")) deleteMut.mutate(row.original.id);
            }}
          >
            <Trash2 className="mr-1 inline h-3 w-3" /> Delete
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 rounded-xl border bg-white p-5 shadow-sm lg:flex-row lg:items-center">
        <div>
          <h1 className="border-l-4 border-blue-500 pl-3 text-2xl font-bold tracking-tight text-slate-900">
            Legal Page Templates
          </h1>
          <p className="mt-1 pl-4 text-sm text-slate-500">
            Named reference samples (plain text or HTML) for LLM legal-page generation.
          </p>
        </div>
        <button
          type="button"
          onClick={openCreate}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          <Plus className="h-4 w-4" /> Add
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-3 rounded-lg border bg-white px-4 py-3">
        <label className="text-sm text-slate-600">
          Filter by page type:
          <select
            className="ml-2 rounded border px-2 py-1 text-sm"
            value={pageTypeFilter}
            onChange={(e) => setPageTypeFilter(e.target.value)}
          >
            <option value="">All</option>
            {(pageTypes && pageTypes.length > 0 ? pageTypes : FALLBACK_PAGE_TYPES).map((pt) => (
              <option key={pt} value={pt}>
                {LEGAL_PAGE_TYPE_LABELS[pt] || pt}
              </option>
            ))}
          </select>
        </label>
      </div>

      <ReactTable columns={columns as never} data={rows || []} isLoading={isLoading} />

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
          <div className="flex max-h-[95vh] w-full max-w-4xl flex-col overflow-hidden rounded-xl border bg-white shadow-xl">
            <div className="flex items-center justify-between border-b px-4 py-3">
              <h3 className="text-lg font-semibold">{editingId ? "Edit Legal Template" : "Add Legal Page Template"}</h3>
              <button type="button" onClick={() => setModalOpen(false)} className="rounded p-1 text-slate-500 hover:bg-slate-100">
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-sm font-medium">Name *</label>
                  <input
                    className="w-full rounded border px-3 py-2 text-sm"
                    value={form.name}
                    onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                    placeholder="e.g. Casino Privacy Policy"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium">Page Type *</label>
                  <select
                    className="w-full rounded border px-3 py-2 text-sm"
                    value={form.page_type}
                    onChange={(e) => setForm((f) => ({ ...f, page_type: e.target.value }))}
                  >
                    {(pageTypes && pageTypes.length > 0 ? pageTypes : FALLBACK_PAGE_TYPES).map((pt) => (
                      <option key={pt} value={pt}>
                        {LEGAL_PAGE_TYPE_LABELS[pt] || pt}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <span className="mb-1 block text-sm font-medium">Content format</span>
                <div className="flex gap-4 text-sm">
                  <label className="flex items-center gap-2">
                    <input
                      type="radio"
                      name="content_format"
                      checked={form.content_format === "text"}
                      onChange={() => setForm((f) => ({ ...f, content_format: "text" }))}
                    />
                    Plain text
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="radio"
                      name="content_format"
                      checked={form.content_format === "html"}
                      onChange={() => setForm((f) => ({ ...f, content_format: "html" }))}
                    />
                    HTML
                  </label>
                </div>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">Content *</label>
                <p className="mb-1 text-xs text-slate-500">Reference text for LLM. Can be plain text or HTML.</p>
                <div className="overflow-hidden rounded border">
                  <Editor
                    height="240px"
                    language={form.content_format === "html" ? "html" : "plaintext"}
                    theme="vs"
                    value={form.content}
                    onChange={(v) => setForm((f) => ({ ...f, content: v ?? "" }))}
                  />
                </div>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">Variables (JSON)</label>
                <textarea
                  className="min-h-[100px] w-full rounded border px-3 py-2 font-mono text-xs"
                  value={form.variablesJson}
                  onChange={(e) => setForm((f) => ({ ...f, variablesJson: e.target.value }))}
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">Notes</label>
                <textarea
                  className="w-full rounded border px-3 py-2 text-sm"
                  value={form.notes}
                  onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                />
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
                />
                Active
              </label>
            </div>
            <div className="flex justify-end gap-2 border-t bg-slate-50 px-4 py-3">
              <button type="button" className="rounded-lg px-4 py-2 text-sm text-slate-700 hover:bg-slate-100" onClick={() => setModalOpen(false)}>
                Cancel
              </button>
              <button
                type="button"
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
                onClick={() => saveMut.mutate()}
                disabled={saveMut.isPending || !form.name.trim() || !form.content.trim()}
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
