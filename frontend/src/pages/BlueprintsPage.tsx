import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Fragment, useState, type Dispatch, type SetStateAction } from "react";
import toast from "react-hot-toast";
import { blueprintsApi } from "@/api/blueprints";
import { legalPagesApi } from "@/api/legalPages";
import { Blueprint, BlueprintPage, PipelinePreset } from "@/types/blueprint";
import { LEGAL_PAGE_TYPES_SET } from "@/types/template";
import {
  CUSTOM_STEP_OPTIONS,
  DEFAULT_FULL_PIPELINE_STEPS,
  normalizeCustomPipelineSteps,
} from "@/lib/pipelineSteps";
import { ChevronDown, ChevronRight, LayoutTemplate, Pencil, Plus, Trash2, X } from "lucide-react";

const PIPELINE_PRESET_LABEL: Record<PipelinePreset, string> = {
  full: "Full",
  category: "Category",
  about: "About",
  legal: "Legal",
  custom: "Custom",
};

const BLUEPRINT_PAGE_TYPE_OPTIONS: { value: string; label: string }[] = [
  { value: "article", label: "Article" },
  { value: "category", label: "Category" },
  { value: "homepage", label: "Homepage" },
  { value: "about_us", label: "About Us" },
  { value: "privacy_policy", label: "Privacy Policy" },
  { value: "terms_and_conditions", label: "Terms & Conditions" },
  { value: "cookie_policy", label: "Cookie Policy" },
  { value: "responsible_gambling", label: "Responsible Gambling" },
];

export default function BlueprintsPage() {
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [expandedBlueprintId, setExpandedBlueprintId] = useState<string | null>(null);

  const { data: blueprints, isLoading } = useQuery({
    queryKey: ["blueprints"],
    queryFn: async () => {
      return blueprintsApi.getAll({ limit: 1000 });
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-5 rounded-xl border shadow-sm">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 border-l-4 border-purple-500 pl-3">Site Blueprints</h1>
          <p className="text-sm text-slate-500 mt-1 pl-4">Manage architectural structures for generating entire websites.</p>
        </div>
        <button 
          onClick={() => setIsCreateOpen(true)}
          className="flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors text-sm font-medium shadow-sm w-full sm:w-auto"
        >
          <Plus className="w-4 h-4" /> Create Blueprint
        </button>
      </div>

      <div className="overflow-hidden rounded-xl border bg-white shadow-sm">
        <table className="w-full">
          <thead className="bg-slate-50">
            <tr className="text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
              <th className="w-10 px-4 py-3" />
              <th className="px-4 py-3">Blueprint Name</th>
              <th className="px-4 py-3">Description</th>
              <th className="px-4 py-3">Created At</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-sm text-slate-500">
                  Loading blueprints...
                </td>
              </tr>
            )}
            {!isLoading && (blueprints || []).length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-sm text-slate-500">
                  No blueprints found
                </td>
              </tr>
            )}
            {(blueprints || []).map((blueprint) => {
              const expanded = expandedBlueprintId === blueprint.id;
              return (
                <Fragment key={blueprint.id}>
                  <tr
                    className="cursor-pointer border-t hover:bg-slate-50"
                    onClick={() => setExpandedBlueprintId(expanded ? null : blueprint.id)}
                  >
                    <td className="px-4 py-3 text-slate-500">
                      {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2 font-semibold text-slate-800">
                        <LayoutTemplate className="h-4 w-4 text-slate-400" />
                        {blueprint.name}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-500">{blueprint.description || "No description"}</td>
                    <td className="px-4 py-3 text-sm text-slate-500">
                      {new Date(blueprint.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                  {expanded && (
                    <tr className="border-t bg-slate-50/60">
                      <td colSpan={4} className="p-4">
                        <BlueprintPagesPanel blueprintId={blueprint.id} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      {isCreateOpen && (
        <CreateBlueprintModal
          onClose={() => setIsCreateOpen(false)}
          setExpandedBlueprintId={setExpandedBlueprintId}
        />
      )}
    </div>
  );
}

function CreateBlueprintModal({
  onClose,
  setExpandedBlueprintId,
}: {
  onClose: () => void;
  setExpandedBlueprintId: Dispatch<SetStateAction<string | null>>;
}) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState({
    name: "",
    description: "",
  });

  const mutation = useMutation({
    mutationFn: (data: Partial<Blueprint> & { slug: string }) => blueprintsApi.create(data),
    onSuccess: (data: { id: string; name?: string; slug?: string }) => {
      toast.success("Blueprint created successfully");
      queryClient.invalidateQueries({ queryKey: ["blueprints"] });
      if (data?.id) {
        setExpandedBlueprintId(data.id);
      }
      onClose();
    },
    onError: () => toast.error("Failed to create blueprint")
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name) {
      toast.error("Blueprint Name is required");
      return;
    }
    const slug = formData.name
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
    mutation.mutate({ ...formData, slug: slug || `blueprint-${Date.now()}` });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden">
        <div className="px-6 py-4 border-b bg-slate-50 flex justify-between items-center">
            <h2 className="text-lg font-bold text-slate-900">Create New Blueprint</h2>
            <button onClick={onClose} className="p-1 hover:bg-slate-200 rounded text-slate-500"><X className="w-5 h-5"/></button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
           <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Blueprint Name *</label>
              <input 
                required
                type="text" 
                value={formData.name}
                onChange={e => setFormData({...formData, name: e.target.value})}
                className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm" 
                placeholder="e.g. Finance Blog Silo Structure" 
              />
           </div>
           <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
              <textarea 
                rows={3} 
                value={formData.description}
                onChange={e => setFormData({...formData, description: e.target.value})}
                className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm" 
                placeholder="Optional description"
              />
           </div>
           
           <div className="flex justify-end gap-3 mt-8 pt-4 border-t">
             <button 
               type="button"
               onClick={onClose}
               className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg text-sm font-medium transition-colors"
             >
               Cancel
             </button>
             <button 
               type="submit"
               disabled={mutation.isPending}
               className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium transition-colors shadow-sm disabled:opacity-50"
             >
               {mutation.isPending ? "Creating..." : "Create Blueprint"}
             </button>
           </div>
        </form>
      </div>
    </div>
  );
}

function BlueprintPagesPanel({ blueprintId }: { blueprintId: string }) {
  const queryClient = useQueryClient();
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [editingPage, setEditingPage] = useState<BlueprintPage | null>(null);
  const [previewSeed, setPreviewSeed] = useState("casinox");
  const [isBrandSeed, setIsBrandSeed] = useState(false);

  const { data: pages, isLoading } = useQuery({
    queryKey: ["blueprint-pages", blueprintId],
    queryFn: () => blueprintsApi.getPages(blueprintId),
    enabled: !!blueprintId,
  });

  const deleteMutation = useMutation({
    mutationFn: (pageId: string) => blueprintsApi.deletePage(blueprintId, pageId),
    onSuccess: () => {
      toast.success("Page deleted");
      queryClient.invalidateQueries({ queryKey: ["blueprint-pages", blueprintId] });
    },
    onError: () => toast.error("Failed to delete page"),
  });

  const onDelete = (page: BlueprintPage) => {
    if (!window.confirm(`Delete page "${page.page_title}"?`)) return;
    deleteMutation.mutate(page.id);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-800">Pages</h3>
        <button
          type="button"
          onClick={() => setIsAddOpen(true)}
          className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
        >
          <Plus className="h-3.5 w-3.5" />
          Add Page
        </button>
      </div>

      <div className="overflow-x-auto rounded-lg border bg-white">
        <table className="min-w-[980px] w-full">
          <thead className="bg-slate-50 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-600">
            <tr>
              <th className="px-2 py-2">#</th>
              <th className="px-2 py-2">Slug</th>
              <th className="px-2 py-2">Title</th>
              <th className="px-2 py-2">Type</th>
              <th className="px-2 py-2">Keyword Template</th>
              <th className="px-2 py-2">Brand Template</th>
              <th className="px-2 py-2">Filename</th>
              <th className="px-2 py-2 text-center">Pipeline</th>
              <th className="px-2 py-2 text-center">Nav</th>
              <th className="px-2 py-2 text-center">Footer</th>
              <th className="px-2 py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="text-sm">
            {isLoading && (
              <tr>
                <td colSpan={11} className="px-2 py-6 text-center text-slate-500">
                  Loading pages...
                </td>
              </tr>
            )}
            {!isLoading && (pages || []).length === 0 && (
              <tr>
                <td colSpan={11} className="px-2 py-6 text-center text-slate-500">
                  No pages yet
                </td>
              </tr>
            )}
            {(pages || []).map((page) => (
              <tr key={page.id} className="border-t">
                <td className="px-2 py-2 font-mono text-xs">{page.sort_order}</td>
                <td className="px-2 py-2 font-mono text-xs">{page.page_slug}</td>
                <td className="px-2 py-2">{page.page_title}</td>
                <td className="px-2 py-2">{page.page_type}</td>
                <td className="px-2 py-2 font-mono text-xs">{page.keyword_template}</td>
                <td className="px-2 py-2 font-mono text-xs text-slate-600">{page.keyword_template_brand || "-"}</td>
                <td className="px-2 py-2 font-mono text-xs">{page.filename}</td>
                <td className="px-2 py-2 text-center text-xs leading-tight">
                  <div className="font-medium text-slate-800">
                    {PIPELINE_PRESET_LABEL[(page.pipeline_preset || "full") as PipelinePreset]}
                  </div>
                  <div className="text-slate-500">{page.use_serp ? "SERP" : "no SERP"}</div>
                </td>
                <td className="px-2 py-2 text-center">{page.show_in_nav ? "✅" : "❌"}</td>
                <td className="px-2 py-2 text-center">{page.show_in_footer ? "✅" : "❌"}</td>
                <td className="px-2 py-2 text-right">
                  <button
                    type="button"
                    onClick={() => setEditingPage(page)}
                    className="mr-1 inline-flex items-center rounded p-1 text-blue-600 hover:bg-blue-50"
                    title="Edit page"
                  >
                    <Pencil className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => onDelete(page)}
                    className="inline-flex items-center rounded p-1 text-rose-600 hover:bg-rose-50"
                    title="Delete page"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="space-y-2 rounded-lg border bg-white p-3">
        <div className="text-sm font-semibold text-slate-800">Keyword Preview</div>
        <div className="flex flex-wrap items-center gap-3">
          <input
            type="text"
            value={previewSeed}
            onChange={(e) => setPreviewSeed(e.target.value)}
            placeholder="Enter test seed"
            className="w-full max-w-xs rounded-md border px-3 py-1.5 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          />
          <label className="inline-flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={isBrandSeed}
              onChange={(e) => setIsBrandSeed(e.target.checked)}
              className="rounded border-slate-300"
            />
            Brand seed
          </label>
        </div>
        <div className="overflow-x-auto rounded border">
          <table className="min-w-[640px] w-full">
            <thead className="bg-slate-50 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-600">
              <tr>
                <th className="px-2 py-2">#</th>
                <th className="px-2 py-2">Page</th>
                <th className="px-2 py-2">Template Used</th>
                <th className="px-2 py-2">Preview Keyword</th>
              </tr>
            </thead>
            <tbody className="text-sm">
              {(pages || []).map((page) => {
                const selectedTemplate =
                  isBrandSeed && page.keyword_template_brand ? page.keyword_template_brand : page.keyword_template;
                return (
                  <tr key={`preview-${page.id}`} className="border-t">
                    <td className="px-2 py-2 font-mono text-xs">{page.sort_order}</td>
                    <td className="px-2 py-2">{page.page_slug}</td>
                    <td className="px-2 py-2 font-mono text-xs">{selectedTemplate}</td>
                    <td className="px-2 py-2 font-mono text-xs">
                      {selectedTemplate.split("{seed}").join(previewSeed || "{seed}")}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {isAddOpen && (
        <AddBlueprintPageModal
          blueprintId={blueprintId}
          onClose={() => setIsAddOpen(false)}
        />
      )}

      {editingPage && (
        <EditBlueprintPageModal
          blueprintId={blueprintId}
          page={editingPage}
          onClose={() => setEditingPage(null)}
        />
      )}
    </div>
  );
}

function PipelinePresetFields({
  formData,
  setFormData,
}: {
  formData: { pipeline_preset: PipelinePreset; pipeline_steps_custom: string[] };
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  setFormData: React.Dispatch<React.SetStateAction<any>>;
}) {
  return (
    <>
      <Field label="Pipeline preset">
        <select
          className="w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          value={formData.pipeline_preset}
          onChange={(e) => {
            const v = e.target.value as PipelinePreset;
            setFormData((p: any) => ({
              ...p,
              pipeline_preset: v,
              pipeline_steps_custom:
                v === "custom" && !(p.pipeline_steps_custom?.length)
                  ? [...DEFAULT_FULL_PIPELINE_STEPS]
                  : p.pipeline_steps_custom,
            }));
          }}
        >
          <option value="full">Full — SERP + full analysis + generation</option>
          <option value="category">Category — SERP + simplified analysis</option>
          <option value="about">About — author-driven (no SERP)</option>
          <option value="legal">Legal — template-driven (no SERP)</option>
          <option value="custom">Custom — manual steps</option>
        </select>
      </Field>
      <p className="text-xs text-slate-500">
        SERP usage follows the preset. The <code className="rounded bg-slate-100 px-1">use_serp</code> flag is set
        automatically on save.
      </p>
      {formData.pipeline_preset === "custom" && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <div className="mb-2 text-sm font-medium text-slate-800">Custom pipeline steps</div>
          <div className="grid max-h-52 grid-cols-1 gap-2 overflow-y-auto sm:grid-cols-2">
            {CUSTOM_STEP_OPTIONS.map((opt) => (
              <label key={opt.id} className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  className="rounded border-slate-300"
                  checked={formData.pipeline_steps_custom.includes(opt.id)}
                  onChange={(e) => {
                    const checked = e.target.checked;
                    setFormData((p: any) => {
                      const cur = p.pipeline_steps_custom || [];
                      const next = checked
                        ? cur.includes(opt.id)
                          ? cur
                          : [...cur, opt.id]
                        : cur.filter((s: string) => s !== opt.id);
                      return { ...p, pipeline_steps_custom: next };
                    });
                  }}
                />
                {opt.label}
              </label>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

function AddBlueprintPageModal({ blueprintId, onClose }: { blueprintId: string; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState({
    page_slug: "",
    page_title: "",
    page_type: "article",
    keyword_template: "{seed}",
    keyword_template_brand: "{seed}",
    filename: "",
    sort_order: 0,
    nav_label: "",
    show_in_nav: true,
    show_in_footer: true,
    pipeline_preset: "full" as PipelinePreset,
    pipeline_steps_custom: [] as string[],
    default_legal_template_id: "",
  });

  const { data: legalTemplates } = useQuery({
    queryKey: ["legal-templates-by-type", formData.page_type],
    queryFn: () => legalPagesApi.getByPageType(formData.page_type),
    enabled: LEGAL_PAGE_TYPES_SET.has(formData.page_type),
  });

  const mutation = useMutation({
    mutationFn: (data: Partial<BlueprintPage>) => blueprintsApi.createPage(blueprintId, data),
    onSuccess: () => {
      toast.success("Page added");
      queryClient.invalidateQueries({ queryKey: ["blueprint-pages", blueprintId] });
      onClose();
    },
    onError: () => toast.error("Failed to add page"),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.page_slug || !formData.page_title || !formData.keyword_template || !formData.filename) {
      toast.error("Fill required fields");
      return;
    }
    if (
      formData.pipeline_preset === "custom" &&
      normalizeCustomPipelineSteps(formData.pipeline_steps_custom).length === 0
    ) {
      toast.error("Select at least one step for custom pipeline");
      return;
    }
    mutation.mutate({
      ...formData,
      keyword_template_brand: formData.keyword_template_brand || undefined,
      nav_label: formData.nav_label || undefined,
      default_legal_template_id: formData.default_legal_template_id || null,
      pipeline_steps_custom:
        formData.pipeline_preset === "custom"
          ? normalizeCustomPipelineSteps(formData.pipeline_steps_custom || [])
          : null,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm">
      <div className="w-full max-w-2xl overflow-hidden rounded-xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b bg-slate-50 px-6 py-4">
          <h2 className="text-lg font-bold text-slate-900">Add Blueprint Page</h2>
          <button onClick={onClose} className="rounded p-1 text-slate-500 hover:bg-slate-200">
            <X className="h-5 w-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4 p-6">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Field label="Slug *">
              <input
                value={formData.page_slug}
                onChange={(e) => setFormData((p) => ({ ...p, page_slug: e.target.value }))}
                className="w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                placeholder="home"
              />
            </Field>
            <Field label="Title *">
              <input
                value={formData.page_title}
                onChange={(e) => setFormData((p) => ({ ...p, page_title: e.target.value }))}
                className="w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                placeholder="Home Page"
              />
            </Field>
            <Field label="Type">
              <select
                value={formData.page_type}
                onChange={(e) => {
                  const newType = e.target.value;
                  setFormData((prev) => ({
                    ...prev,
                    page_type: newType,
                    default_legal_template_id: LEGAL_PAGE_TYPES_SET.has(newType)
                      ? prev.default_legal_template_id
                      : "",
                  }));
                }}
                className="w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 bg-white"
              >
                {!BLUEPRINT_PAGE_TYPE_OPTIONS.some((o) => o.value === formData.page_type) && (
                  <option value={formData.page_type}>{formData.page_type} (custom)</option>
                )}
                {BLUEPRINT_PAGE_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Filename *">
              <input
                value={formData.filename}
                onChange={(e) => setFormData((p) => ({ ...p, filename: e.target.value }))}
                className="w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                placeholder="index.html"
              />
            </Field>
            <Field label="Sort Order">
              <input
                type="number"
                value={formData.sort_order}
                onChange={(e) => setFormData((p) => ({ ...p, sort_order: Number(e.target.value) || 0 }))}
                className="w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
            </Field>
            <Field label="Nav Label">
              <input
                value={formData.nav_label}
                onChange={(e) => setFormData((p) => ({ ...p, nav_label: e.target.value }))}
                className="w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                placeholder="Home"
              />
            </Field>
          </div>

          {LEGAL_PAGE_TYPES_SET.has(formData.page_type) && (
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                Default Legal Template (optional)
              </label>
              <p className="mb-1 text-xs text-slate-500">
                Fallback template for this page type. Projects can override this per-project.
              </p>
              <select
                className="w-full rounded-lg border px-3 py-2 text-sm"
                value={formData.default_legal_template_id}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    default_legal_template_id: e.target.value,
                  }))
                }
              >
                <option value="">— None (generate from scratch) —</option>
                {(legalTemplates || []).map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          <Field label="Keyword Template *">
            <input
              value={formData.keyword_template}
              onChange={(e) => setFormData((p) => ({ ...p, keyword_template: e.target.value }))}
              className="w-full rounded-lg border px-3 py-2 font-mono text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              placeholder="{seed} online casino"
            />
          </Field>
          <Field label="Brand Template">
            <input
              value={formData.keyword_template_brand}
              onChange={(e) => setFormData((p) => ({ ...p, keyword_template_brand: e.target.value }))}
              className="w-full rounded-lg border px-3 py-2 font-mono text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              placeholder="{seed}"
            />
          </Field>

          <PipelinePresetFields
            formData={{
              pipeline_preset: formData.pipeline_preset,
              pipeline_steps_custom: formData.pipeline_steps_custom,
            }}
            setFormData={setFormData}
          />

          <div className="flex flex-wrap gap-4 text-sm text-slate-700">
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.show_in_nav}
                onChange={(e) => setFormData((p) => ({ ...p, show_in_nav: e.target.checked }))}
                className="rounded border-slate-300"
              />
              Show in Nav
            </label>
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.show_in_footer}
                onChange={(e) => setFormData((p) => ({ ...p, show_in_footer: e.target.checked }))}
                className="rounded border-slate-300"
              />
              Show in Footer
            </label>
          </div>

          <div className="mt-6 flex justify-end gap-3 border-t pt-4">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {mutation.isPending ? "Adding..." : "Add Page"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function EditBlueprintPageModal({
  blueprintId,
  page,
  onClose,
}: {
  blueprintId: string;
  page: BlueprintPage;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState({
    page_slug: page.page_slug,
    page_title: page.page_title,
    page_type: page.page_type,
    keyword_template: page.keyword_template,
    keyword_template_brand: page.keyword_template_brand || "",
    filename: page.filename,
    sort_order: page.sort_order,
    nav_label: page.nav_label || "",
    show_in_nav: page.show_in_nav,
    show_in_footer: page.show_in_footer,
    pipeline_preset: (page.pipeline_preset || "full") as PipelinePreset,
    pipeline_steps_custom: [...(page.pipeline_steps_custom || [])] as string[],
    default_legal_template_id: page.default_legal_template_id || "",
  });

  const { data: legalTemplates } = useQuery({
    queryKey: ["legal-templates-by-type", formData.page_type],
    queryFn: () => legalPagesApi.getByPageType(formData.page_type),
    enabled: LEGAL_PAGE_TYPES_SET.has(formData.page_type),
  });

  const mutation = useMutation({
    mutationFn: (data: Partial<BlueprintPage>) => blueprintsApi.updatePage(blueprintId, page.id, data),
    onSuccess: () => {
      toast.success("Page updated");
      queryClient.invalidateQueries({ queryKey: ["blueprint-pages", blueprintId] });
      onClose();
    },
    onError: () => toast.error("Failed to update page"),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.page_slug || !formData.page_title || !formData.keyword_template || !formData.filename) {
      toast.error("Fill required fields");
      return;
    }
    if (
      formData.pipeline_preset === "custom" &&
      normalizeCustomPipelineSteps(formData.pipeline_steps_custom).length === 0
    ) {
      toast.error("Select at least one step for custom pipeline");
      return;
    }
    mutation.mutate({
      ...formData,
      keyword_template_brand: formData.keyword_template_brand || undefined,
      nav_label: formData.nav_label || undefined,
      default_legal_template_id: formData.default_legal_template_id || null,
      pipeline_steps_custom:
        formData.pipeline_preset === "custom"
          ? normalizeCustomPipelineSteps(formData.pipeline_steps_custom || [])
          : null,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm">
      <div className="w-full max-w-2xl overflow-hidden rounded-xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b bg-slate-50 px-6 py-4">
          <h2 className="text-lg font-bold text-slate-900">Edit Blueprint Page</h2>
          <button onClick={onClose} className="rounded p-1 text-slate-500 hover:bg-slate-200">
            <X className="h-5 w-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4 p-6">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Field label="Slug *">
              <input
                value={formData.page_slug}
                onChange={(e) => setFormData((p) => ({ ...p, page_slug: e.target.value }))}
                className="w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
            </Field>
            <Field label="Title *">
              <input
                value={formData.page_title}
                onChange={(e) => setFormData((p) => ({ ...p, page_title: e.target.value }))}
                className="w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
            </Field>
            <Field label="Type">
              <select
                value={formData.page_type}
                onChange={(e) => {
                  const newType = e.target.value;
                  setFormData((prev) => ({
                    ...prev,
                    page_type: newType,
                    default_legal_template_id: LEGAL_PAGE_TYPES_SET.has(newType)
                      ? prev.default_legal_template_id
                      : "",
                  }));
                }}
                className="w-full rounded-lg border bg-white px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              >
                {!BLUEPRINT_PAGE_TYPE_OPTIONS.some((o) => o.value === formData.page_type) && (
                  <option value={formData.page_type}>{formData.page_type} (custom)</option>
                )}
                {BLUEPRINT_PAGE_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Filename *">
              <input
                value={formData.filename}
                onChange={(e) => setFormData((p) => ({ ...p, filename: e.target.value }))}
                className="w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
            </Field>
            <Field label="Sort Order">
              <input
                type="number"
                value={formData.sort_order}
                onChange={(e) => setFormData((p) => ({ ...p, sort_order: Number(e.target.value) || 0 }))}
                className="w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
            </Field>
            <Field label="Nav Label">
              <input
                value={formData.nav_label}
                onChange={(e) => setFormData((p) => ({ ...p, nav_label: e.target.value }))}
                className="w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
            </Field>
          </div>

          {LEGAL_PAGE_TYPES_SET.has(formData.page_type) && (
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                Default Legal Template (optional)
              </label>
              <p className="mb-1 text-xs text-slate-500">
                Fallback template for this page type. Projects can override this per-project.
              </p>
              <select
                className="w-full rounded-lg border px-3 py-2 text-sm"
                value={formData.default_legal_template_id}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    default_legal_template_id: e.target.value,
                  }))
                }
              >
                <option value="">— None (generate from scratch) —</option>
                {(legalTemplates || []).map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          <Field label="Keyword Template *">
            <input
              value={formData.keyword_template}
              onChange={(e) => setFormData((p) => ({ ...p, keyword_template: e.target.value }))}
              className="w-full rounded-lg border px-3 py-2 font-mono text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            />
          </Field>
          <Field label="Brand Template">
            <input
              value={formData.keyword_template_brand}
              onChange={(e) => setFormData((p) => ({ ...p, keyword_template_brand: e.target.value }))}
              className="w-full rounded-lg border px-3 py-2 font-mono text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            />
          </Field>

          <PipelinePresetFields
            formData={{
              pipeline_preset: formData.pipeline_preset,
              pipeline_steps_custom: formData.pipeline_steps_custom,
            }}
            setFormData={setFormData}
          />

          <div className="flex flex-wrap gap-4 text-sm text-slate-700">
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.show_in_nav}
                onChange={(e) => setFormData((p) => ({ ...p, show_in_nav: e.target.checked }))}
                className="rounded border-slate-300"
              />
              Show in Nav
            </label>
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.show_in_footer}
                onChange={(e) => setFormData((p) => ({ ...p, show_in_footer: e.target.checked }))}
                className="rounded border-slate-300"
              />
              Show in Footer
            </label>
          </div>

          <div className="mt-6 flex justify-end gap-3 border-t pt-4">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {mutation.isPending ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-slate-700">{label}</label>
      {children}
    </div>
  );
}
