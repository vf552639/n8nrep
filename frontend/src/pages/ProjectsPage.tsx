import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect, useMemo, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import type { RowSelectionState } from "@tanstack/react-table";
import toast from "react-hot-toast";
import {
  projectsApi,
  type ClusterKeywordsResult,
  type SiteProjectCreatePayload,
} from "@/api/projects";
import { formatApiErrorDetail } from "@/lib/apiErrorMessage";
import { languageEquals, normalizeLanguageDisplay } from "@/lib/languageDisplay";
import { sitesApi } from "@/api/sites";
import { blueprintsApi } from "@/api/blueprints";
import { Author } from "@/types/author";
import { Site } from "@/types/site";
import { ReactTable } from "@/components/common/ReactTable";
import StatusBadge from "@/components/common/StatusBadge";
import {
  Plus,
  FolderGit2,
  X,
  Archive,
  ArchiveRestore,
  Trash2,
  Search,
  Eye,
  ChevronDown,
  ChevronUp,
  Shuffle,
} from "lucide-react";
import type { Project, ProjectPreview } from "@/types/project";
import { LEGAL_PAGE_TYPE_LABELS } from "@/types/template";
import { COUNTRY_CODES, countryLabel } from "@/constants/countries";
import { legalPagesApi } from "@/api/legalPages";

function isProjectDeleteBlockedByActiveStatus(status: number | undefined, detail: unknown): boolean {
  if (status !== 400) return false;
  const s = formatApiErrorDetail(detail);
  return /pending or generating/i.test(s);
}

function parseKeywords(raw: string): string[] {
  if (!raw.trim()) return [];
  return raw
    .split(/[\n,]/)
    .map((kw) => kw.trim())
    .filter((kw) => kw.length > 0)
    .slice(0, 100);
}

function parseUrls(raw: string): string[] {
  if (!raw.trim()) return [];
  return raw
    .split(/[\n,]/)
    .map((u) => u.trim())
    .filter((u) => u.length > 0)
    .slice(0, 50);
}

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "pending", label: "Pending" },
  { value: "generating", label: "Generating" },
  { value: "completed", label: "Completed" },
  { value: "failed", label: "Failed" },
  { value: "stopped", label: "Stopped" },
];

export default function ProjectsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [viewArchived, setViewArchived] = useState(false);
  const [statusFilter, setStatusFilter] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [forceDeleteModal, setForceDeleteModal] = useState<{
    id: string;
    name: string;
    status: string;
  } | null>(null);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(searchInput.trim()), 400);
    return () => clearTimeout(t);
  }, [searchInput]);

  const listParams = useMemo(
    () => ({
      limit: 100,
      archived: viewArchived,
      ...(statusFilter ? { status: statusFilter } : {}),
      ...(debouncedSearch ? { search: debouncedSearch } : {}),
    }),
    [viewArchived, statusFilter, debouncedSearch]
  );

  const { data: projects, isLoading } = useQuery({
    queryKey: ["projects", listParams],
    queryFn: async () => projectsApi.getAll(listParams),
  });

  const selectedIds = useMemo(
    () => Object.keys(rowSelection).filter((id) => rowSelection[id]),
    [rowSelection]
  );
  const selectedCount = selectedIds.length;

  const archiveMutation = useMutation({
    mutationFn: ({ id, archive }: { id: string; archive: boolean }) =>
      archive ? projectsApi.archiveProject(id) : projectsApi.unarchiveProject(id),
    onSuccess: (_, { archive }) => {
      toast.success(archive ? "Project archived" : "Project restored");
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
    onError: (e: unknown) => {
      const ax = e as { response?: { data?: { detail?: unknown } }; message?: string };
      toast.error(formatApiErrorDetail(ax.response?.data?.detail) || ax.message || "Request failed");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (vars: { id: string; name: string; status: string; force?: boolean }) =>
      projectsApi.deleteProject(vars.id, { force: Boolean(vars.force) }),
    onSuccess: () => {
      toast.success("Project deleted");
      setForceDeleteModal(null);
      setRowSelection({});
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
    onError: (e: unknown, variables) => {
      const ax = e as {
        response?: { status?: number; data?: { detail?: unknown } };
        message?: string;
      };
      if (
        !variables.force &&
        isProjectDeleteBlockedByActiveStatus(ax.response?.status, ax.response?.data?.detail)
      ) {
        setForceDeleteModal({
          id: variables.id,
          name: variables.name,
          status: variables.status,
        });
        return;
      }
      toast.error(formatApiErrorDetail(ax.response?.data?.detail) || ax.message || "Delete failed");
    },
  });

  const deleteSelectedMutation = useMutation({
    mutationFn: (vars: { ids: string[]; force?: boolean }) =>
      projectsApi.deleteSelected(vars.ids, { force: Boolean(vars.force) }),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      toast.success(
        `Deleted ${data.deleted} project(s)${data.skipped ? `, skipped ${data.skipped} active` : ""}`
      );
      if (data.skipped > 0 && !variables.force) {
        if (
          window.confirm(
            `${data.skipped} project(s) are still pending or generating and were skipped. Force delete them? Celery tasks will be revoked. This cannot be undone.`
          )
        ) {
          deleteSelectedMutation.mutate({ ids: variables.ids, force: true });
          return;
        }
      }
      setRowSelection({});
    },
    onError: () => toast.error("Failed to delete projects"),
  });

  const handleDeleteSelected = useCallback(() => {
    if (selectedIds.length === 0) return;
    if (
      !window.confirm(
        `Delete ${selectedIds.length} project(s) and all their tasks? This cannot be undone.`
      )
    ) {
      return;
    }
    deleteSelectedMutation.mutate({ ids: selectedIds });
  }, [selectedIds, deleteSelectedMutation]);

  const columns = useMemo(
    () => [
      {
        id: "select",
        size: 40,
        enableSorting: false,
        meta: { tdClassName: "w-10 min-w-[2.5rem] align-middle" },
        header: ({ table }: { table: any }) => (
          <input
            type="checkbox"
            className="rounded border-slate-300 text-blue-600"
            checked={table.getIsAllPageRowsSelected()}
            ref={(el) => {
              if (el) {
                el.indeterminate =
                  table.getIsSomePageRowsSelected() && !table.getIsAllPageRowsSelected();
              }
            }}
            onChange={table.getToggleAllPageRowsSelectedHandler()}
            aria-label="Select all on page"
          />
        ),
        cell: ({ row }: { row: any }) => (
          <input
            type="checkbox"
            className="rounded border-slate-300 text-blue-600"
            checked={row.getIsSelected()}
            onChange={row.getToggleSelectedHandler()}
            onClick={(e) => e.stopPropagation()}
            aria-label="Select row"
          />
        ),
      },
      {
        accessorKey: "name",
        header: "Project Name",
        cell: ({ row }: { row: { original: Project } }) => (
          <div className="font-semibold text-slate-800 flex items-center gap-2">
            <FolderGit2 className="w-4 h-4 text-slate-400" />
            {row.original.name}
          </div>
        ),
      },
      {
        accessorKey: "seed_keyword",
        header: "Seed Keyword",
        cell: ({ row }: { row: { original: Project } }) => (
          <span className="text-slate-600 bg-slate-50 px-2 py-0.5 rounded border leading-tight">
            {row.original.seed_keyword}
          </span>
        ),
      },
      {
        id: "geo",
        header: "Country / Lang",
        cell: ({ row }: { row: { original: Project } }) => (
          <span className="text-slate-600 text-xs">
            {[row.original.country, row.original.language].filter(Boolean).join(" / ") || "—"}
          </span>
        ),
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }: { row: { original: Project } }) => (
          <StatusBadge status={row.original.status} />
        ),
      },
      {
        id: "pages",
        header: "Pages",
        cell: ({ row }: { row: { original: Project } }) => {
          const p = row.original;
          const t = p.total_tasks ?? 0;
          const c = p.completed_tasks ?? 0;
          return (
            <span className="text-slate-700 text-sm tabular-nums">
              {t > 0 ? `${c}/${t}` : "—"}
            </span>
          );
        },
      },
      {
        id: "total_cost",
        header: "Cost",
        cell: ({ row }: { row: { original: Project } }) => (
          <span className="text-slate-700 text-sm tabular-nums">
            {row.original.total_cost != null ? `$${Number(row.original.total_cost).toFixed(4)}` : "—"}
          </span>
        ),
      },
      {
        id: "failed_tasks",
        header: "Failed",
        cell: ({ row }: { row: { original: Project } }) => {
          const n = row.original.failed_tasks ?? 0;
          return (
            <span
              className={`text-sm font-medium tabular-nums ${n > 0 ? "text-red-600" : "text-slate-400"}`}
            >
              {n}
            </span>
          );
        },
      },
      {
        accessorKey: "progress",
        header: "Progress",
        cell: ({ row }: { row: { original: Project } }) => {
          const p = row.original;
          return (
            <div className="flex items-center gap-3 w-full max-w-[180px]">
              <div className="w-full bg-slate-200 rounded-full h-2.5 overflow-hidden">
                <div
                  className={`h-2.5 rounded-full border-r border-black/10 ${
                    p.progress === 100 ? "bg-emerald-500" : "bg-blue-500"
                  }`}
                  style={{ width: `${p.progress || 0}%` }}
                />
              </div>
              <span className="text-xs font-semibold text-slate-600 w-8 text-right">
                {Math.round(p.progress || 0)}%
              </span>
            </div>
          );
        },
      },
      {
        accessorKey: "created_at",
        header: "Date",
        cell: ({ row }: { row: { original: Project } }) => (
          <span className="text-slate-500 text-sm whitespace-nowrap">
            {new Date(row.original.created_at).toLocaleDateString()}
          </span>
        ),
      },
      {
        id: "actions",
        header: "",
        meta: { tdClassName: "w-12" },
        cell: ({ row }: { row: { original: Project } }) => (
          <div
            className="flex justify-end items-center gap-0.5"
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => e.stopPropagation()}
            role="presentation"
          >
            {viewArchived ? (
              <>
                <button
                  type="button"
                  title="Restore from archive"
                  className="p-2 rounded-lg text-slate-500 hover:bg-emerald-50 hover:text-emerald-700"
                  onClick={() => archiveMutation.mutate({ id: row.original.id, archive: false })}
                  disabled={
                    archiveMutation.isPending ||
                    deleteMutation.isPending ||
                    deleteSelectedMutation.isPending
                  }
                >
                  <ArchiveRestore className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  title="Delete permanently"
                  className="p-2 rounded-lg text-slate-500 hover:bg-red-50 hover:text-red-700"
                  onClick={() => {
                    if (
                      window.confirm(
                        `Delete project "${row.original.name}" and all its tasks? This cannot be undone.`
                      )
                    ) {
                      deleteMutation.mutate({
                        id: row.original.id,
                        name: row.original.name,
                        status: row.original.status,
                      });
                    }
                  }}
                  disabled={deleteMutation.isPending || deleteSelectedMutation.isPending}
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </>
            ) : (
              <button
                type="button"
                title="Archive"
                className="p-2 rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-800"
                onClick={() => archiveMutation.mutate({ id: row.original.id, archive: true })}
                disabled={archiveMutation.isPending || deleteSelectedMutation.isPending}
              >
                <Archive className="w-4 h-4" />
              </button>
            )}
          </div>
        ),
      },
    ],
    [
      viewArchived,
      archiveMutation.isPending,
      deleteMutation.isPending,
      deleteSelectedMutation.isPending,
    ]
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 bg-white p-5 rounded-xl border shadow-sm">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 border-l-4 border-slate-700 pl-3">
              Generative Projects
            </h1>
            <p className="text-sm text-slate-500 mt-1 pl-4">
              Manage bulk generation of entire sites from blueprints.
            </p>
          </div>
          <button
            onClick={() => setIsCreateOpen(true)}
            className="flex items-center justify-center gap-2 bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 rounded-lg transition-colors text-sm font-medium shadow-sm w-full sm:w-auto"
          >
            <Plus className="w-4 h-4" /> New Project
          </button>
        </div>

        <div className="flex flex-col lg:flex-row flex-wrap gap-3 items-stretch lg:items-center border-t border-slate-100 pt-4">
          <div className="inline-flex rounded-lg border border-slate-200 p-0.5 bg-slate-50">
            <button
              type="button"
              onClick={() => {
                setViewArchived(false);
                setRowSelection({});
              }}
              className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${
                !viewArchived ? "bg-white shadow text-slate-900" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Active
            </button>
            <button
              type="button"
              onClick={() => {
                setViewArchived(true);
                setRowSelection({});
              }}
              className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${
                viewArchived ? "bg-white shadow text-slate-900" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Archived
            </button>
          </div>

          <div className="flex flex-wrap gap-2 items-center flex-1 min-w-[200px]">
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setRowSelection({});
              }}
              className="border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white text-slate-800 max-w-[200px]"
            >
              {STATUS_OPTIONS.map((o) => (
                <option key={o.value || "all"} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
            <div className="relative flex-1 min-w-[160px] max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="search"
                placeholder="Search by name..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                className="w-full border border-slate-200 rounded-lg pl-9 pr-3 py-2 text-sm"
              />
            </div>
          </div>
        </div>
      </div>

      {selectedCount > 0 && (
        <div className="flex flex-wrap items-center gap-3 rounded-lg border border-blue-200 bg-blue-50 p-3">
          <span className="text-sm font-medium text-slate-800">Выбрано: {selectedCount}</span>
          <button
            type="button"
            disabled={deleteSelectedMutation.isPending}
            onClick={handleDeleteSelected}
            className="inline-flex items-center gap-1.5 rounded-md bg-white px-3 py-1.5 text-sm font-medium text-red-800 shadow-sm ring-1 ring-red-200 hover:bg-red-50 disabled:opacity-50"
          >
            <Trash2 className="h-4 w-4" /> Удалить выбранные
          </button>
          <button
            type="button"
            onClick={() => setRowSelection({})}
            className="ml-auto text-sm text-slate-600 hover:text-slate-900"
          >
            Снять выделение
          </button>
        </div>
      )}

      <ReactTable
        columns={columns as any}
        data={projects || []}
        isLoading={isLoading}
        enableRowSelection
        rowSelection={rowSelection}
        onRowSelectionChange={setRowSelection}
        getRowId={(row) => row.id}
        onRowClick={(p: Project) => navigate(`/projects/${p.id}`)}
      />

      {forceDeleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4 border">
            <h2 className="text-lg font-semibold text-slate-900">Cannot delete normally</h2>
            <p className="text-sm text-slate-600">
              Проект завис в статусе <span className="font-semibold">{forceDeleteModal.status}</span>.
              Celery-задача, вероятно, не выполняется. Принудительно удалить?
            </p>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                className="px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 rounded-lg"
                onClick={() => setForceDeleteModal(null)}
              >
                Отмена
              </button>
              <button
                type="button"
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg disabled:opacity-50"
                disabled={deleteMutation.isPending}
                onClick={() =>
                  deleteMutation.mutate({
                    id: forceDeleteModal.id,
                    name: forceDeleteModal.name,
                    status: forceDeleteModal.status,
                    force: true,
                  })
                }
              >
                {deleteMutation.isPending ? "…" : "Force Delete"}
              </button>
            </div>
          </div>
        </div>
      )}

      {isCreateOpen && <CreateProjectModal onClose={() => setIsCreateOpen(false)} />}
    </div>
  );
}

function CreateProjectModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState({
    name: "",
    blueprint_id: "",
    site_id: "",
    seed_keyword: "",
    seed_is_brand: false,
    country: "",
    language: "",
    author_id: "" as string,
    serp_engine: "google" as "google" | "bing" | "google+bing",
    serp_depth: 10 as number,
    serp_device: "mobile" as "mobile" | "desktop",
    serp_os: "android" as "android" | "ios" | "windows" | "macos",
    additional_keywords_raw: "",
    competitor_urls_raw: "",
    legal_template_map: {} as Record<string, string>,
    use_site_template: true,
    markup_only: false,
  });
  const [serpAdvancedOpen, setSerpAdvancedOpen] = useState(false);
  const [preview, setPreview] = useState<ProjectPreview | null>(null);
  const [clusterResult, setClusterResult] = useState<ClusterKeywordsResult | null>(null);

  const parsedKeywords = useMemo(
    () => parseKeywords(formData.additional_keywords_raw),
    [formData.additional_keywords_raw]
  );

  const parsedCompetitorUrls = useMemo(
    () => parseUrls(formData.competitor_urls_raw),
    [formData.competitor_urls_raw]
  );

  useEffect(() => {
    setClusterResult(null);
  }, [formData.additional_keywords_raw, formData.blueprint_id]);

  const { data: authors } = useQuery({
    queryKey: ["authors"],
    queryFn: () => import("@/api/authors").then((m) => m.authorsApi.getAll()),
  });

  const { data: sites } = useQuery({
    queryKey: ["sites"],
    queryFn: async () => sitesApi.getAll(),
    refetchOnMount: "always",
  });

  const { data: selectedSiteDetail } = useQuery({
    queryKey: ["sites", formData.site_id],
    queryFn: () => sitesApi.getOne(formData.site_id!),
    enabled: Boolean(formData.site_id),
  });

  const selectedSite =
    selectedSiteDetail ?? (sites || []).find((s: Site) => s.id === formData.site_id);
  const siteHasTemplate =
    selectedSite?.has_template ?? Boolean(selectedSite?.template_id);

  useEffect(() => {
    setPreview(null);
  }, [formData.use_site_template, formData.markup_only]);

  useEffect(() => {
    if (!formData.site_id || siteHasTemplate) return;
    setFormData((prev) => {
      if (!prev.use_site_template) return prev;
      return { ...prev, use_site_template: false };
    });
  }, [formData.site_id, siteHasTemplate]);

  const countries = Array.from(
    new Set(
      [
        ...COUNTRY_CODES,
        ...(authors || []).map((a: Author) => String(a.country || "").toUpperCase().trim()),
        ...(selectedSite?.country ? [String(selectedSite.country).toUpperCase().trim()] : []),
        ...(formData.country ? [formData.country.toUpperCase().trim()] : []),
      ].filter(Boolean)
    )
  ).sort();
  const languages = Array.from(
    new Set(
      [
        ...(authors || []).map((a: Author) => normalizeLanguageDisplay(String(a.language || ""))),
        ...(selectedSite?.language ? [normalizeLanguageDisplay(selectedSite.language)] : []),
        ...(formData.language ? [normalizeLanguageDisplay(formData.language)] : []),
      ].filter(Boolean)
    )
  ).sort();

  const filteredAuthors = (authors || []).filter(
    (a: Author) =>
      String(a.country || "")
        .toUpperCase()
        .trim() === String(formData.country || "").toUpperCase().trim() &&
      languageEquals(a.language, formData.language)
  );

  const { data: blueprints } = useQuery({
    queryKey: ["blueprints"],
    queryFn: async () => blueprintsApi.getAll({ limit: 100 }),
  });

  const { data: legalForBp } = useQuery({
    queryKey: ["legal-for-blueprint", formData.blueprint_id],
    queryFn: () => legalPagesApi.getForBlueprint(formData.blueprint_id),
    enabled: Boolean(formData.blueprint_id),
  });

  useEffect(() => {
    if (!legalForBp || legalForBp.legal_page_types.length === 0) return;

    setFormData((prev) => {
      const hasUserSelection = Object.values(prev.legal_template_map).some(
        (v) => v && String(v).trim()
      );
      if (hasUserSelection) return prev;

      const defaults: Record<string, string> = {};
      for (const group of legalForBp.legal_page_types) {
        if (group.default_template_id) {
          defaults[group.page_type] = group.default_template_id;
        }
      }
      if (Object.keys(defaults).length === 0) return prev;

      return { ...prev, legal_template_map: { ...prev.legal_template_map, ...defaults } };
    });
  }, [legalForBp]);

  const buildSerpConfig = () => {
    if (
      formData.serp_engine === "google" &&
      formData.serp_depth === 10 &&
      formData.serp_device === "mobile" &&
      formData.serp_os === "android"
    ) {
      return undefined;
    }
    return {
      search_engine: formData.serp_engine,
      depth: formData.serp_depth,
      device: formData.serp_device,
      os: formData.serp_os,
    };
  };

  const previewMutation = useMutation({
    mutationFn: () => {
      const authorId =
        formData.author_id && formData.author_id.trim() !== ""
          ? Number(formData.author_id)
          : undefined;
      return projectsApi.preview({
        blueprint_id: formData.blueprint_id,
        ...(formData.markup_only ? {} : { target_site: formData.site_id }),
        seed_keyword: formData.seed_keyword,
        seed_is_brand: formData.seed_is_brand,
        country: formData.country,
        language: formData.language,
        ...(authorId != null && !Number.isNaN(authorId) ? { author_id: authorId } : {}),
        serp_config: buildSerpConfig(),
        use_site_template: formData.markup_only ? false : formData.use_site_template,
      });
    },
    onSuccess: (data) => {
      setPreview(data);
      toast.success("Preview loaded");
    },
    onError: (error: unknown) => {
      const ax = error as {
        response?: { data?: { detail?: unknown } };
        message?: string;
      };
      toast.error(
        formatApiErrorDetail(ax.response?.data?.detail) ||
          ax.message ||
          "Preview failed"
      );
    },
  });

  const clusterMutation = useMutation({
    mutationFn: (kw: string[]) =>
      projectsApi.clusterKeywords({
        keywords: kw,
        blueprint_id: formData.blueprint_id,
      }),
    onSuccess: (data) => {
      setClusterResult(data);
      toast.success("Keywords clustered");
    },
    onError: (error: unknown) => {
      const ax = error as {
        response?: { data?: { detail?: unknown } };
        message?: string;
      };
      toast.error(
        formatApiErrorDetail(ax.response?.data?.detail) ||
          ax.message ||
          "Clustering failed"
      );
    },
  });

  const canPreview =
    Boolean(formData.blueprint_id) &&
    Boolean(formData.seed_keyword) &&
    Boolean(formData.country) &&
    Boolean(formData.language) &&
    (formData.markup_only || Boolean(formData.site_id));

  const mutation = useMutation({
    mutationFn: projectsApi.create,
    onSuccess: (data) => {
      toast.success("Project started successfully");
      if (data?.serp_warning) {
        toast(data.serp_warning, { icon: "⚠️", duration: 8000 });
      }
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      onClose();
    },
    onError: (error: unknown) => {
      const ax = error as {
        response?: { data?: { detail?: unknown } };
        message?: string;
      };
      const msg =
        formatApiErrorDetail(ax.response?.data?.detail) ||
        ax.message ||
        "Failed to start project";
      toast.error(msg);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const needSite = !formData.markup_only;
    if (
      !formData.name ||
      !formData.blueprint_id ||
      (needSite && !formData.site_id) ||
      !formData.seed_keyword ||
      !formData.country ||
      !formData.language
    ) {
      toast.error(
        needSite
          ? "Please fill in all required fields (Name, Blueprint, Site, Seed Keyword, Country, Language)"
          : "Please fill in all required fields (Name, Blueprint, Seed Keyword, Country, Language)"
      );
      return;
    }
    const authorId =
      formData.author_id && formData.author_id.trim() !== ""
        ? Number(formData.author_id)
        : undefined;
    const serp = buildSerpConfig();

    let project_keywords: SiteProjectCreatePayload["project_keywords"];
    if (clusterResult && parsedKeywords.length > 0) {
      project_keywords = {
        raw: parsedKeywords,
        clustered: clusterResult.clustered,
        unassigned: clusterResult.unassigned,
        clustering_model: clusterResult.model,
        clustering_cost: clusterResult.cost,
      };
    } else if (parsedKeywords.length > 0) {
      project_keywords = { raw: parsedKeywords };
    } else {
      project_keywords = undefined;
    }

    const ltmRaw = formData.legal_template_map || {};
    const legal_template_map = Object.fromEntries(
      Object.entries(ltmRaw).filter(([, templateId]) => templateId && String(templateId).trim())
    );
    const hasLegal = Object.keys(legal_template_map).length > 0;

    mutation.mutate({
      name: formData.name,
      blueprint_id: formData.blueprint_id,
      ...(formData.markup_only ? {} : { target_site: formData.site_id }),
      seed_keyword: formData.seed_keyword,
      seed_is_brand: formData.seed_is_brand,
      country: formData.country,
      language: formData.language,
      ...(authorId != null && !Number.isNaN(authorId) ? { author_id: authorId } : {}),
      ...(serp ? { serp_config: serp } : {}),
      ...(project_keywords ? { project_keywords } : {}),
      ...(hasLegal ? { legal_template_map } : {}),
      use_site_template: formData.markup_only ? false : formData.use_site_template,
      ...(parsedCompetitorUrls.length > 0 ? { competitor_urls: parsedCompetitorUrls } : {}),
    });
  };

  const onSiteChange = (siteId: string) => {
    const site = (sites || []).find((s: Site) => s.id === siteId);
    const newHasTemplate = site
      ? (site.has_template ?? Boolean(site.template_id))
      : false;
    setFormData((prev) => ({
      ...prev,
      site_id: siteId,
      country: site ? site.country : prev.country,
      language: site ? site.language : prev.language,
      author_id: "",
      use_site_template: newHasTemplate,
    }));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
        <div className="px-6 py-4 border-b bg-slate-50 flex justify-between items-center shrink-0">
          <h2 className="text-lg font-bold text-slate-900">Create Generative Project</h2>
          <button onClick={onClose} className="p-1 hover:bg-slate-200 rounded text-slate-500">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-6">
          <form id="create-project-form" onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Project Name *</label>
              <input
                required
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm"
                placeholder="e.g. Finance Hub"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Blueprint *</label>
              <select
                required
                value={formData.blueprint_id}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    blueprint_id: e.target.value,
                    legal_template_map: {},
                  })
                }
                className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm bg-white"
              >
                <option value="" disabled>
                  Select blueprint...
                </option>
                {blueprints?.map((bp) => (
                  <option key={bp.id} value={bp.id}>
                    {bp.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-3">
              <label className="flex items-start gap-2 text-sm text-slate-800 cursor-pointer">
                <input
                  type="checkbox"
                  className="mt-0.5 shrink-0"
                  checked={formData.markup_only}
                  onChange={(e) => {
                    const on = e.target.checked;
                    setFormData((prev) => ({
                      ...prev,
                      markup_only: on,
                      ...(on ? { site_id: "", use_site_template: false } : {}),
                    }));
                  }}
                />
                <span>
                  <span className="font-medium">
                    Markup only (skip target site — output without site HTML wrapper)
                  </span>
                  <span className="block text-xs text-slate-500 font-normal mt-1">
                    Uses a reserved placeholder site; set Country and Language below. No site head,
                    header, or footer wrapper.
                  </span>
                </span>
              </label>
            </div>
            {!formData.markup_only && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Target Site *</label>
              <select
                required
                value={formData.site_id}
                onChange={(e) => onSiteChange(e.target.value)}
                className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm bg-white"
              >
                <option value="" disabled>
                  Select target site...
                </option>
                {sites?.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.domain})
                  </option>
                ))}
              </select>
            </div>
            )}
            {!formData.markup_only && formData.site_id && (
              <div className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-3 space-y-1">
                <label
                  className={`flex items-start gap-2 text-sm text-slate-800 ${
                    siteHasTemplate ? "cursor-pointer" : "cursor-not-allowed"
                  }`}
                >
                  <input
                    type="checkbox"
                    className="mt-0.5 shrink-0"
                    disabled={!siteHasTemplate}
                    checked={formData.use_site_template}
                    onChange={(e) =>
                      setFormData({ ...formData, use_site_template: e.target.checked })
                    }
                  />
                  <span>
                    <span className="font-medium">Use site HTML template</span>
                    <span className="block text-xs text-slate-500 font-normal mt-1">
                      {siteHasTemplate
                        ? "When disabled, articles are generated as clean HTML without site wrapper (no head, css, header/footer)."
                        : "No HTML template assigned to this site. Articles are generated as clean HTML."}
                    </span>
                  </span>
                </label>
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Seed Keyword *</label>
              <input
                required
                type="text"
                value={formData.seed_keyword}
                onChange={(e) => setFormData({ ...formData, seed_keyword: e.target.value })}
                className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm"
                placeholder="e.g. Best Credit Cards"
              />
              <label className="mt-2 flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={formData.seed_is_brand}
                  onChange={(e) => setFormData({ ...formData, seed_is_brand: e.target.checked })}
                />
                Brand seed
              </label>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Additional Keywords (optional, max 100)
              </label>
              <textarea
                rows={4}
                placeholder={
                  "One per line or comma-separated\ncasino bonus codes\nfree spins no deposit"
                }
                value={formData.additional_keywords_raw}
                onChange={(e) =>
                  setFormData({ ...formData, additional_keywords_raw: e.target.value })
                }
                className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
              <div className="flex flex-wrap items-center justify-between gap-2 mt-1">
                <p className="text-xs text-slate-400">{parsedKeywords.length} / 100 keywords</p>
                {parsedKeywords.length > 0 && formData.blueprint_id && (
                  <button
                    type="button"
                    onClick={() => clusterMutation.mutate(parsedKeywords)}
                    disabled={clusterMutation.isPending}
                    className="flex items-center gap-2 px-3 py-1.5 border border-slate-300 bg-white text-slate-800 rounded-lg text-xs font-medium hover:bg-slate-50 disabled:opacity-50"
                  >
                    <Shuffle className="w-3.5 h-3.5" />
                    {clusterMutation.isPending ? "Clustering..." : "Cluster Keywords"}
                  </button>
                )}
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Competitor URLs (optional, max 50)
              </label>
              <textarea
                rows={4}
                placeholder={
                  "One per line or comma-separated — merged with SERP results; duplicates by domain are dropped.\nhttps://competitor.example/article\nother-site.org/page"
                }
                value={formData.competitor_urls_raw}
                onChange={(e) =>
                  setFormData({ ...formData, competitor_urls_raw: e.target.value })
                }
                className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 font-mono text-xs"
              />
              <p className="text-xs text-slate-400 mt-1">
                {parsedCompetitorUrls.length} / 50 URLs (normalized on save)
              </p>
            </div>
            {clusterResult && clusterResult.total_assigned === 0 && clusterResult.total_keywords > 0 && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                Keywords don&apos;t match any page well — all keywords were left unassigned. Try
                editing the list or blueprint.
              </div>
            )}
            {clusterResult && (
              <div className="border rounded-lg p-4 bg-slate-50 space-y-3">
                <div className="flex justify-between items-center gap-2 flex-wrap">
                  <h4 className="font-semibold text-sm text-slate-800">Keyword Distribution Preview</h4>
                  <span className="text-xs text-slate-500">
                    {clusterResult.total_assigned}/{clusterResult.total_keywords} assigned
                    {clusterResult.cost != null && ` · Cost: $${clusterResult.cost.toFixed(4)}`}
                  </span>
                </div>
                {Object.entries(clusterResult.clustered).map(([slug, data]) => (
                  <div key={slug} className="bg-white rounded border p-3">
                    <div className="flex justify-between gap-2">
                      <span className="font-medium text-sm">{data.page_title}</span>
                      <span className="text-xs text-slate-400">{data.assigned_keywords.length} kw</span>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">Main: {data.keyword}</p>
                    {data.assigned_keywords.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {data.assigned_keywords.map((kw, i) => (
                          <span
                            key={i}
                            className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs"
                          >
                            {kw}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
                {clusterResult.unassigned.length > 0 && (
                  <div className="bg-amber-50 rounded border border-amber-200 p-3">
                    <span className="font-medium text-sm text-amber-800">
                      Unassigned ({clusterResult.unassigned.length})
                    </span>
                    <div className="flex flex-wrap gap-1 mt-2">
                      {clusterResult.unassigned.map((kw, i) => (
                        <span
                          key={i}
                          className="px-2 py-0.5 bg-amber-100 text-amber-800 rounded text-xs"
                        >
                          {kw}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Country *</label>
                <select
                  required
                  className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm bg-white"
                  value={formData.country}
                  onChange={(e) => setFormData({ ...formData, country: e.target.value, author_id: "" })}
                >
                  <option value="" disabled>
                    Select country...
                  </option>
                  {(countries as string[]).map((c) => (
                    <option key={c} value={c}>
                      {countryLabel(c)} ({c})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Language *</label>
                <select
                  required
                  className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm bg-white"
                  value={formData.language}
                  onChange={(e) => setFormData({ ...formData, language: e.target.value, author_id: "" })}
                >
                  <option value="" disabled>
                    Select language...
                  </option>
                  {(languages as string[]).map((l) => (
                    <option key={l} value={l}>
                      {l}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Author</label>
              <select
                className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm bg-white disabled:bg-slate-50 disabled:text-slate-400"
                value={formData.author_id}
                onChange={(e) => setFormData({ ...formData, author_id: e.target.value })}
                disabled={!formData.country || !formData.language}
              >
                {!formData.country || !formData.language ? (
                  <option value="">Auto</option>
                ) : (
                  <>
                    <option value="">Auto (by country/language)</option>
                    {filteredAuthors.map((a: Author) => (
                      <option key={a.id} value={a.id}>
                        {a.author || a.id}
                      </option>
                    ))}
                  </>
                )}
              </select>
              {(!formData.country || !formData.language) && (
                <p className="mt-1 text-xs text-slate-500">
                  {formData.markup_only
                    ? "Select Country and Language first."
                    : "Select Country and Language first (or use Target Site to prefill)."}
                </p>
              )}
            </div>

            {legalForBp && legalForBp.legal_page_types.length > 0 && (
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 space-y-3">
                <h3 className="text-sm font-semibold text-slate-800">Legal Page Templates (optional)</h3>
                <p className="text-xs text-slate-600">
                  Select reference templates for legal pages in this blueprint. LLM will adapt them to your
                  site&apos;s country, language, and domain.
                </p>
                {legalForBp.legal_page_types.map((group) => (
                  <div key={group.page_type}>
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      {LEGAL_PAGE_TYPE_LABELS[group.page_type] || group.page_title}
                    </label>
                    <select
                      className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm bg-white"
                      value={formData.legal_template_map[group.page_type] || ""}
                      onChange={(e) => {
                        const v = e.target.value;
                        setFormData((prev) => {
                          const next = { ...prev.legal_template_map };
                          if (!v) delete next[group.page_type];
                          else next[group.page_type] = v;
                          return { ...prev, legal_template_map: next };
                        });
                      }}
                    >
                      <option value="">— None (generate from scratch) —</option>
                      {group.templates.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name}
                        </option>
                      ))}
                    </select>
                    {group.default_template_id && (
                      <p className="mt-1 text-xs text-blue-600">
                        Blueprint default pre-selected. You can override it.
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}

            <div className="border border-slate-200 rounded-lg overflow-hidden">
              <button
                type="button"
                onClick={() => setSerpAdvancedOpen(!serpAdvancedOpen)}
                className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-slate-800 bg-slate-50 hover:bg-slate-100"
              >
                <span>Advanced SERP Settings</span>
                {serpAdvancedOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>
              {serpAdvancedOpen && (
                <div className="p-4 space-y-3 bg-white border-t border-slate-100">
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">Search Engine</label>
                    <select
                      className="w-full border rounded-lg px-3 py-2 text-sm bg-white"
                      value={formData.serp_engine}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          serp_engine: e.target.value as "google" | "bing" | "google+bing",
                        })
                      }
                    >
                      <option value="google">Google (DataForSEO → SerpAPI fallback)</option>
                      <option value="bing">Bing (DataForSEO)</option>
                      <option value="google+bing">Google + Bing (merged)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">Depth</label>
                    <select
                      className="w-full border rounded-lg px-3 py-2 text-sm bg-white"
                      value={formData.serp_depth}
                      onChange={(e) =>
                        setFormData({ ...formData, serp_depth: Number(e.target.value) })
                      }
                    >
                      {[10, 20, 30, 50, 100].map((d) => (
                        <option key={d} value={d}>
                          {d}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">Device</label>
                    <select
                      className="w-full border rounded-lg px-3 py-2 text-sm bg-white"
                      value={formData.serp_device}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          serp_device: e.target.value as "mobile" | "desktop",
                        })
                      }
                    >
                      <option value="mobile">Mobile</option>
                      <option value="desktop">Desktop</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">OS</label>
                    <select
                      className="w-full border rounded-lg px-3 py-2 text-sm bg-white"
                      value={formData.serp_os}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          serp_os: e.target.value as "android" | "ios" | "windows" | "macos",
                        })
                      }
                    >
                      <option value="android">Android</option>
                      <option value="ios">iOS</option>
                      <option value="windows">Windows</option>
                      <option value="macos">macOS</option>
                    </select>
                  </div>
                </div>
              )}
            </div>
          </form>

          {preview && (
            <div className="mt-6 space-y-4 border-t border-slate-200 pt-4">
              <h3 className="text-sm font-semibold text-slate-800">Preview</h3>
              {preview.warnings?.length > 0 && (
                <div className="space-y-2">
                  {preview.warnings.map((w, i) => (
                    <div
                      key={i}
                      className="text-sm text-amber-900 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2"
                    >
                      {w}
                    </div>
                  ))}
                </div>
              )}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                <div className="border rounded-lg p-3 bg-slate-50">
                  <div className="text-xs text-slate-500 uppercase">Site</div>
                  <div className="font-medium text-slate-900 flex flex-wrap items-center gap-2">
                    <span>
                      {preview.site.name}
                      {preview.site.will_be_created && (
                        <span className="text-amber-700 text-xs ml-1">(will be created)</span>
                      )}
                    </span>
                    {preview.site.use_site_template === false && (
                      <span className="text-xs font-medium px-2 py-0.5 rounded bg-slate-200 text-slate-700">
                        Template: OFF
                      </span>
                    )}
                  </div>
                  <div className="text-slate-600 text-xs">{preview.site.domain}</div>
                </div>
                <div className="border rounded-lg p-3 bg-slate-50">
                  <div className="text-xs text-slate-500 uppercase">Author</div>
                  <div className="font-medium text-slate-900">
                    {preview.author.name ?? "Not assigned"}
                  </div>
                </div>
                <div className="border rounded-lg p-3 bg-slate-50">
                  <div className="text-xs text-slate-500 uppercase">HTML template</div>
                  <div className="font-medium text-slate-900">
                    {preview.site.has_template ? "Yes" : "No"}
                  </div>
                </div>
                <div className="border rounded-lg p-3 bg-slate-50">
                  <div className="text-xs text-slate-500 uppercase">Estimated cost</div>
                  <div className="font-medium text-slate-900">
                    {preview.estimated_cost != null
                      ? `$${preview.estimated_cost.toFixed(4)}`
                      : "—"}
                  </div>
                  {preview.avg_cost_per_page != null && (
                    <div className="text-xs text-slate-500">
                      Avg / task: ${preview.avg_cost_per_page.toFixed(4)}
                    </div>
                  )}
                </div>
              </div>
              {Object.keys(preview.serp_config || {}).length > 0 && (
                <p className="text-xs text-slate-600">
                  SERP config: {JSON.stringify(preview.serp_config)}
                </p>
              )}
              <div className="overflow-x-auto border rounded-lg max-h-64 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="bg-slate-100 sticky top-0 text-left">
                    <tr>
                      <th className="px-2 py-1.5">Order</th>
                      <th className="px-2 py-1.5">Slug</th>
                      <th className="px-2 py-1.5">Keyword</th>
                      <th className="px-2 py-1.5">Type</th>
                      <th className="px-2 py-1.5">Pipeline</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.pages.map((pg) => (
                      <tr key={`${pg.sort_order}-${pg.page_slug}`} className="border-t border-slate-100">
                        <td className="px-2 py-1.5 tabular-nums">{pg.sort_order}</td>
                        <td className="px-2 py-1.5 font-mono text-xs">{pg.page_slug}</td>
                        <td className="px-2 py-1.5 font-semibold text-slate-900">{pg.keyword}</td>
                        <td className="px-2 py-1.5">{pg.page_type}</td>
                        <td className="px-2 py-1.5 text-xs">
                          <span className="font-medium capitalize">{pg.pipeline_preset || "full"}</span>
                          <span className="text-slate-500"> · {pg.use_serp ? "SERP" : "no SERP"}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
        <div className="flex flex-wrap justify-end gap-3 px-6 py-4 border-t bg-slate-50 shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-slate-600 hover:bg-slate-200 rounded-lg text-sm font-medium transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={!canPreview || previewMutation.isPending}
            onClick={() => previewMutation.mutate()}
            className="flex items-center gap-2 px-4 py-2 border border-slate-300 bg-white text-slate-800 rounded-lg text-sm font-medium hover:bg-slate-50 disabled:opacity-50"
          >
            <Eye className="w-4 h-4" />
            {previewMutation.isPending ? "Loading…" : "Preview"}
          </button>
          <button
            type="submit"
            form="create-project-form"
            disabled={mutation.isPending}
            className="px-4 py-2 bg-slate-900 text-white rounded-lg hover:bg-slate-800 text-sm font-medium transition-colors shadow-sm disabled:opacity-50"
          >
            {mutation.isPending ? "Starting..." : "Start Project"}
          </button>
        </div>
      </div>
    </div>
  );
}
