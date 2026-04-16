import { useParams, Link, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect, useMemo } from "react";
import toast from "react-hot-toast";
import api from "@/api/client";
import { projectsApi } from "@/api/projects";
import { legalPagesApi } from "@/api/legalPages";
import { LEGAL_PAGE_TYPE_LABELS } from "@/types/template";
import { tasksApi } from "@/api/tasks";
import { formatApiErrorDetail } from "@/lib/apiErrorMessage";
import { Project } from "@/types/project";
import StatusBadge from "@/components/common/StatusBadge";
import StepMonitor from "@/components/tasks/StepMonitor";
import { sitesApi } from "@/api/sites";
import { authorsApi } from "@/api/authors";
import type { Site } from "@/types/site";
import type { Author } from "@/types/author";
import {
  Download,
  Pause,
  Play,
  CheckCircle2,
  CircleDashed,
  FileText,
  ChevronRight,
  ChevronDown,
  Trash2,
  RefreshCw,
  Copy,
  Clock,
  DollarSign,
  PlayCircle,
  FileSpreadsheet,
} from "lucide-react";

function formatProjectErrorLog(raw: string | null | undefined): string {
  if (!raw) return "";
  try {
    const j = JSON.parse(raw) as unknown;
    return JSON.stringify(j, null, 2);
  } catch {
    return raw;
  }
}

function fmtMoney(n: number | undefined) {
  if (n == null || Number.isNaN(n)) return "—";
  return `$${n.toFixed(4)}`;
}

function fmtHumanSecs(s: number | null | undefined) {
  if (s == null || Number.isNaN(s)) return "—";
  const sec = Math.floor(s);
  const m = Math.floor(sec / 60);
  const h = Math.floor(m / 60);
  const remM = m % 60;
  const remS = sec % 60;
  if (h > 0) return `${h}h ${remM}m ${remS}s`;
  if (m > 0) return `${m}m ${remS}s`;
  return `${remS}s`;
}

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [expandedTask, setExpandedTask] = useState<string | null>(null);
  const [cloneOpen, setCloneOpen] = useState(false);
  const [nowTick, setNowTick] = useState(() => Date.now());

  const { data: project, isLoading } = useQuery({
    queryKey: ["project", id],
    queryFn: async () => {
      const res = await api.get<Project>(`/projects/${id}`);
      return res.data;
    },
    refetchInterval: (query) => {
      const p = query.state.data;
      if (p?.status === "generating" || p?.status === "pending") return 3000;
      return false;
    }
  });

  useEffect(() => {
    const p = project;
    if (!p || (p.status !== "generating" && p.status !== "pending" && p.status !== "awaiting_page_approval")) return;
    const t = setInterval(() => setNowTick(Date.now()), 1000);
    return () => clearInterval(t);
  }, [project?.status, project?.started_at, project?.generation_started_at]);

  const actionMutation = useMutation({
    mutationFn: (action: "stop" | "resume") => api.post(`/projects/${id}/${action}`),
    onSuccess: (_, action) => {
      toast.success(`Project ${action === "stop" ? "stopped (waiting for current task)" : "resumed"}`);
      queryClient.invalidateQueries({ queryKey: ["project", id] });
    },
    onError: () => toast.error("Action failed"),
  });

  const retryFailedMutation = useMutation({
    mutationFn: () => projectsApi.retryFailedPages(id!),
    onSuccess: (data) => {
      toast.success(`Queued retry for ${data.retried_count} failed page(s)`);
      queryClient.invalidateQueries({ queryKey: ["project", id] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
    onError: () => toast.error("Retry failed"),
  });

  const retryOneTaskMutation = useMutation({
    mutationFn: (taskId: string) => tasksApi.retry(taskId),
    onSuccess: () => {
      toast.success("Task queued for retry");
      queryClient.invalidateQueries({ queryKey: ["project", id] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
    onError: () => toast.error("Could not retry task"),
  });

  const deleteMutation = useMutation({
    mutationFn: () => projectsApi.deleteProject(id!),
    onSuccess: () => {
      toast.success("Project deleted");
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      navigate("/projects");
    },
    onError: () => toast.error("Delete failed"),
  });

  const startMutation = useMutation({
    mutationFn: () => projectsApi.startProject(id!),
    onSuccess: () => {
      toast.success("Project queued");
      queryClient.invalidateQueries({ queryKey: ["project", id] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
    onError: (e: unknown) => {
      const ax = e as { response?: { data?: { detail?: unknown } }; message?: string };
      toast.error(
        formatApiErrorDetail(ax.response?.data?.detail) || ax.message || "Start failed"
      );
    },
  });

  const approvePageMutation = useMutation({
    mutationFn: () => projectsApi.approvePage(id!),
    onSuccess: () => {
      toast.success("Page approved, generation resumed");
      queryClient.invalidateQueries({ queryKey: ["project", id] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
    onError: () => toast.error("Approval failed"),
  });

  const rebuildZipMutation = useMutation({
    mutationFn: () => projectsApi.rebuildZip(id!),
    onSuccess: () => {
      toast.success("ZIP rebuilt successfully");
      queryClient.invalidateQueries({ queryKey: ["project", id] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
    onError: (e: unknown) => {
      const ax = e as { response?: { data?: { detail?: unknown } }; message?: string };
      toast.error(
        formatApiErrorDetail(ax.response?.data?.detail) || ax.message || "ZIP rebuild failed"
      );
    },
  });

  const etaEstimate = useMemo(() => {
    const p = project;
    if (!p || p.status !== "generating") return null;
    const completed = p.completed_tasks ?? 0;
    const rem = p.remaining_pages ?? 0;
    const startTs = p.generation_started_at ?? p.started_at;
    if (startTs == null || completed <= 0 || rem <= 0) return null;
    const elapsed = (nowTick - new Date(startTs).getTime()) / 1000;
    return (elapsed / completed) * rem;
  }, [project, nowTick]);

  const ltm = project?.legal_template_map;
  const ltmEntries =
    ltm && typeof ltm === "object"
      ? (Object.entries(ltm) as [string, string][]).filter(([, tid]) => tid && String(tid).trim())
      : [];

  const { data: legalTemplateLabels } = useQuery({
    queryKey: ["project-legal-template-labels", id, ltmEntries.map((e) => e[1]).join("|")],
    queryFn: async () => {
      const out: { page_type: string; name: string }[] = [];
      for (const [page_type, templateId] of ltmEntries) {
        try {
          const t = await legalPagesApi.getOne(String(templateId));
          out.push({ page_type, name: t.name });
        } catch {
          out.push({ page_type, name: String(templateId) });
        }
      }
      return out;
    },
    enabled: Boolean(id) && ltmEntries.length > 0,
  });

  if (isLoading) return <div className="p-6 text-slate-500">Loading project...</div>;
  if (!project) return <div className="p-6 text-red-500">Project not found</div>;

  const elapsedSec =
    (project.generation_started_at ?? project.started_at) != null
      ? (nowTick - new Date(project.generation_started_at ?? project.started_at!).getTime()) / 1000
      : null;

  const failedCount = project.failed_count ?? 0;
  const canRetryFailed =
    failedCount > 0 && project.status !== "generating" && project.status !== "pending";
  const canDelete = project.status !== "generating" && project.status !== "pending";
  const canStart = project.status === "pending";
  const logs = project.logs ?? [];
  const sc = project.serp_config as Record<string, unknown> | undefined;
  const serpBadgeItems: { label: string; value: string }[] = [];
  if (sc) {
    const eng = sc.search_engine;
    if (eng && eng !== "google") {
      serpBadgeItems.push({
        label: "Engine",
        value: String(eng),
      });
    }
    if (sc.depth != null && Number(sc.depth) !== 10) {
      serpBadgeItems.push({ label: "Depth", value: String(sc.depth) });
    }
    if (sc.device && sc.device !== "mobile") {
      serpBadgeItems.push({ label: "Device", value: String(sc.device) });
    }
  }
  const taskCount = project.total_tasks ?? project.tasks?.length ?? 0;
  const canExportCsv = taskCount > 0 && project.status !== "pending";
  const canExportDocx = (project.completed_tasks ?? 0) > 0;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">{project.name}</h1>
          <div className="text-sm text-slate-500 mt-2 flex flex-wrap gap-x-4 gap-y-1">
            <span className="flex items-center gap-1">
              Blueprint:{" "}
              <span className="font-semibold text-slate-700">{project.blueprint_id}</span>
            </span>
            <span className="flex items-center gap-1">
              Seed:{" "}
              <span className="font-semibold text-slate-700 bg-slate-100 px-2 rounded">
                {project.seed_keyword}
              </span>
            </span>
            <span className="flex items-center gap-1">
              Site: <span className="font-medium">{project.site_id}</span>
            </span>
            <span className="flex items-center gap-1">
              GEO:{" "}
              <span className="font-medium text-slate-700">
                {project.country} / {project.language}
              </span>
            </span>
            {failedCount > 0 && (
              <span className="text-red-600 font-semibold">Failed pages: {failedCount}</span>
            )}
            {serpBadgeItems.length > 0 && (
              <span className="flex flex-wrap gap-1.5 items-center">
                {serpBadgeItems.map((b) => (
                  <span
                    key={b.label}
                    className="text-xs font-medium bg-indigo-50 text-indigo-800 border border-indigo-200 px-2 py-0.5 rounded"
                  >
                    {b.label}: {b.value}
                  </span>
                ))}
              </span>
            )}
            {legalTemplateLabels && legalTemplateLabels.length > 0 && (
              <span className="block w-full text-slate-600 text-sm">
                Legal templates:{" "}
                {legalTemplateLabels.map((row, i) => (
                  <span key={row.page_type}>
                    {i > 0 ? " · " : ""}
                    {LEGAL_PAGE_TYPE_LABELS[row.page_type] || row.page_type} → {row.name}
                  </span>
                ))}
              </span>
            )}
          </div>
        </div>
        <div className="flex flex-wrap gap-2 justify-end">
          <button
            type="button"
            onClick={() => setCloneOpen(true)}
            className="flex items-center gap-2 bg-slate-50 text-slate-800 border border-slate-200 hover:bg-slate-100 px-3 py-1.5 rounded-md text-sm font-medium"
            title="Clone project"
          >
            <Copy className="w-4 h-4" /> Clone
          </button>
          {canStart && (
            <button
              type="button"
              onClick={() => startMutation.mutate()}
              disabled={startMutation.isPending}
              className="flex items-center gap-2 bg-emerald-50 text-emerald-800 border border-emerald-200 hover:bg-emerald-100 px-3 py-1.5 rounded-md text-sm font-medium disabled:opacity-60"
            >
              <PlayCircle className="w-4 h-4" /> Start
            </button>
          )}
          {canRetryFailed && (
            <button
              type="button"
              onClick={() => retryFailedMutation.mutate()}
              disabled={retryFailedMutation.isPending}
              className="flex items-center gap-2 bg-violet-50 text-violet-800 border border-violet-200 hover:bg-violet-100 px-3 py-1.5 rounded-md text-sm font-medium disabled:opacity-60"
            >
              <RefreshCw className="w-4 h-4" /> Retry Failed Pages
            </button>
          )}
          {canDelete && (
            <button
              type="button"
              onClick={() => {
                if (
                  window.confirm(
                    "Delete this project and all its tasks? This cannot be undone."
                  )
                ) {
                  deleteMutation.mutate();
                }
              }}
              disabled={deleteMutation.isPending}
              className="flex items-center gap-2 bg-red-50 text-red-700 border border-red-200 hover:bg-red-100 px-3 py-1.5 rounded-md text-sm font-medium disabled:opacity-60"
            >
              <Trash2 className="w-4 h-4" /> Delete
            </button>
          )}
          {project.status === "generating" && (
            <button 
              onClick={() => actionMutation.mutate("stop")}
              disabled={actionMutation.isPending}
              className="flex items-center gap-2 bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100 px-3 py-1.5 rounded-md text-sm font-medium transition-colors shadow-sm disabled:opacity-70"
            >
              <Pause className="w-4 h-4" /> Stop Project
            </button>
          )}
          {project.status === "stopped" && (
            <button 
              onClick={() => actionMutation.mutate("resume")}
              disabled={actionMutation.isPending}
              className="flex items-center gap-2 bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 px-3 py-1.5 rounded-md text-sm font-medium transition-colors shadow-sm disabled:opacity-70"
            >
              <Play className="w-4 h-4" /> Resume
            </button>
          )}
          {canExportCsv && (
            <button
              type="button"
              onClick={async () => {
                try {
                  await projectsApi.exportCsv(project.id);
                  toast.success("CSV download started");
                } catch {
                  toast.error("CSV export failed");
                }
              }}
              className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-md text-sm font-medium shadow-sm transition-colors"
            >
              <FileSpreadsheet className="w-4 h-4" /> Export Summary (CSV)
            </button>
          )}
          {canExportDocx && (
            <button
              type="button"
              onClick={async () => {
                try {
                  await projectsApi.exportDocx(project.id);
                  toast.success("DOCX download started");
                } catch {
                  toast.error("DOCX export failed");
                }
              }}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium shadow-sm transition-colors"
            >
              <FileText className="w-4 h-4" /> Export DOCX
            </button>
          )}
          {project.status === "completed" && (
            <>
              <button
                type="button"
                onClick={() => rebuildZipMutation.mutate()}
                disabled={rebuildZipMutation.isPending}
                className="flex items-center gap-2 bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-300 px-4 py-2 rounded-md text-sm font-medium shadow-sm transition-colors disabled:opacity-60"
              >
                <RefreshCw className="w-4 h-4" /> Rebuild ZIP
              </button>
              <a
                href={`${import.meta.env.VITE_API_URL || "http://localhost:8000/api"}/projects/${id}/download`}
                download
                className="flex items-center gap-2 bg-emerald-700 hover:bg-emerald-800 text-white px-4 py-2 rounded-md text-sm font-medium shadow-sm transition-colors"
              >
                <Download className="w-4 h-4" /> Download ZIP
              </a>
            </>
          )}
        </div>
      </div>

      {project.status === "awaiting_page_approval" && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-center justify-between gap-4">
          <div>
            <p className="font-semibold text-amber-900">Page completed - waiting for approval</p>
            <p className="text-sm text-amber-700 mt-1">
              Review the generated page, then approve to continue.
            </p>
          </div>
          <button
            type="button"
            onClick={() => approvePageMutation.mutate()}
            disabled={approvePageMutation.isPending}
            className="px-4 py-2 bg-emerald-600 text-white rounded-lg font-medium hover:bg-emerald-700 disabled:opacity-60"
          >
            Approve & Continue
          </button>
        </div>
      )}

      {project.status === "failed" && project.error_log && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <span className="text-red-500 text-lg" aria-hidden>
              ❌
            </span>
            <div>
              <p className="font-semibold text-red-800">Project Failed</p>
              <p className="text-sm text-red-700 mt-1 font-mono whitespace-pre-wrap break-words">
                {formatProjectErrorLog(project.error_log)}
              </p>
            </div>
          </div>
        </div>
      )}

      {project.status === "completed" && project.error_log && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <span className="text-amber-600 text-lg" aria-hidden>
              ⚠
            </span>
            <div>
              <p className="font-semibold text-amber-900">Completed with page errors</p>
              <p className="text-sm text-amber-900/90 mt-1 font-mono whitespace-pre-wrap break-words">
                {formatProjectErrorLog(project.error_log)}
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="bg-white border rounded-xl p-4 shadow-sm flex gap-3">
          <div className="p-2 rounded-lg bg-emerald-50 text-emerald-700">
            <DollarSign className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">Total cost</div>
            <div className="text-lg font-semibold text-slate-900 tabular-nums">
              {fmtMoney(project.total_cost)}
            </div>
            <div className="text-xs text-slate-500 mt-0.5">
              Avg / page: {fmtMoney(project.avg_cost_per_page)}
            </div>
          </div>
        </div>
        <div className="bg-white border rounded-xl p-4 shadow-sm flex gap-3">
          <div className="p-2 rounded-lg bg-sky-50 text-sky-700">
            <Clock className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">Time</div>
            {(project.status === "completed" ||
              project.status === "stopped" ||
              project.status === "failed") &&
            project.duration_seconds != null ? (
              <>
                <div className="text-lg font-semibold text-slate-900">
                  {fmtHumanSecs(project.duration_seconds)}
                </div>
                <div className="text-xs text-slate-500 mt-0.5">
                  Avg / page: {fmtHumanSecs(project.avg_seconds_per_page ?? undefined)}
                </div>
              </>
            ) : project.status === "generating" && project.started_at ? (
              <>
                <div className="text-lg font-semibold text-slate-900">
                  Elapsed {fmtHumanSecs(elapsedSec ?? undefined)}
                </div>
                <div className="text-xs text-slate-500 mt-0.5">
                  ETA ~{" "}
                  {etaEstimate != null ? fmtHumanSecs(etaEstimate) : "—"}
                </div>
              </>
            ) : (
              <div className="text-sm text-slate-500">—</div>
            )}
          </div>
        </div>
      </div>

      <div className="bg-white border p-6 rounded-xl shadow-sm">
        <div className="flex justify-between items-center mb-4">
           <h2 className="text-lg font-semibold text-slate-800">Overall Progress</h2>
           <StatusBadge status={project.status} />
        </div>
        <div className="w-full bg-slate-100 rounded-full h-4 relative overflow-hidden my-4 border shadow-inner">
          <div 
            className={`h-4 rounded-full transition-all duration-500 border-r border-black/10 ${project.progress === 100 ? 'bg-emerald-500' : 'bg-blue-500'}`} 
            style={{ width: `${project.progress || 0}%` }}
          />
        </div>
        <div className="text-right text-sm font-bold text-slate-600">{Math.round(project.progress || 0)}% Complete</div>
      </div>

      {logs.length > 0 && (
        <div className="bg-white border rounded-xl shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b bg-slate-50 flex justify-between items-center">
            <h2 className="text-lg font-semibold text-slate-800">Project log</h2>
            <span className="text-xs text-slate-500">{logs.length} events</span>
          </div>
          <div className="overflow-x-auto max-h-[320px] overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-slate-600 sticky top-0">
                <tr>
                  <th className="px-4 py-2 font-medium whitespace-nowrap w-44">Time</th>
                  <th className="px-4 py-2 font-medium w-24">Level</th>
                  <th className="px-4 py-2 font-medium">Message</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {logs.map((row, idx) => (
                  <tr key={`${row.ts}-${idx}`} className="hover:bg-slate-50/80">
                    <td className="px-4 py-2 text-slate-500 font-mono text-xs whitespace-nowrap">
                      {row.ts}
                    </td>
                    <td className="px-4 py-2">
                      <span
                        className={`text-xs font-medium px-2 py-0.5 rounded ${
                          row.level === "error"
                            ? "bg-red-100 text-red-800"
                            : row.level === "warning"
                              ? "bg-amber-100 text-amber-900"
                              : "bg-slate-100 text-slate-700"
                        }`}
                      >
                        {row.level || "info"}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-slate-800 whitespace-pre-wrap break-words">
                      {row.msg}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="bg-white border rounded-xl shadow-sm overflow-hidden min-h-[400px]">
        <div className="p-6 pb-4 border-b">
          <h2 className="text-lg font-semibold text-slate-800">Project Tasks Execution</h2>
        </div>
        
        {project.tasks && project.tasks.length > 0 ? (
          <div className="divide-y">
            {project.tasks.map((task, i) => {
              const isExpanded = expandedTask === task.id;
              return (
                <div key={task.id} className="flex flex-col">
                  <div 
                    className="p-4 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer"
                    onClick={() => setExpandedTask(isExpanded ? null : task.id)}
                  >
                    <div className="flex items-center gap-4">
                      <div className="flex-shrink-0 font-mono text-slate-400 text-sm w-6">#{i + 1}</div>
                      <div className="flex items-center gap-2">
                         {task.status === 'completed' && <CheckCircle2 className="w-5 h-5 text-emerald-500" />}
                         {task.status === 'running' && <CircleDashed className="w-5 h-5 text-blue-500 animate-[spin_3s_linear_infinite]" />}
                         {task.status === 'pending' && <CircleDashed className="w-5 h-5 text-slate-300" />}
                         {task.status === 'failed' && <CircleDashed className="w-5 h-5 text-red-500" />}
                      </div>
                      <div>
                        <div className="font-medium text-slate-800 break-all">{task.main_keyword}</div>
                        <div className="text-xs text-slate-500 mt-0.5 flex gap-2">
                           <span className="bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200 uppercase tracking-tighter">{task.page_type}</span>
                           {task.current_step && <span className="bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded text-xs">{task.current_step.replace(/_/g, " ")}</span>}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-6">
                      <div className="text-sm font-medium text-slate-500">{Math.round(task.progress)}%</div>
                      {task.status === "failed" && (
                        <button
                          type="button"
                          className="rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-900 hover:bg-amber-100 disabled:opacity-50"
                          disabled={retryOneTaskMutation.isPending}
                          onClick={(e) => {
                            e.stopPropagation();
                            retryOneTaskMutation.mutate(task.id);
                          }}
                        >
                          Retry page
                        </button>
                      )}
                      <Link 
                        to={`/tasks/${task.id}`}
                        className="flex items-center justify-center p-2 text-blue-600 hover:bg-blue-50 border border-transparent hover:border-blue-200 rounded-md transition-all text-xs font-semibold"
                        title="Open Task Detail Page"
                        onClick={(e) => e.stopPropagation()}
                      >
                        Open Detailed View
                      </Link>
                      <button className="text-slate-400 hover:text-slate-700 p-1">
                        {isExpanded ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
                      </button>
                    </div>
                  </div>
                  {isExpanded && (
                    <div className="bg-slate-50/50 p-6 border-t border-slate-100 shadow-inner">
                      <StepMonitor
                        taskId={task.id}
                        isActive={["processing", "pending"].includes(task.status)}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center text-slate-500 mt-16 bg-slate-50 border border-dashed rounded-lg p-10 max-w-lg mx-auto">
              <FileText className="w-10 h-10 mx-auto text-slate-300 mb-4" />
              <div className="font-medium text-slate-700">No tasks generated yet</div>
              <p className="text-sm mt-1 text-slate-500">Once the blueprint is parsed, tasks will populate here.</p>
          </div>
        )}
      </div>

      {cloneOpen && (
        <CloneProjectModal
          project={project}
          onClose={() => setCloneOpen(false)}
          onCloned={(newId) => {
            setCloneOpen(false);
            navigate(`/projects/${newId}`);
          }}
        />
      )}
    </div>
  );
}

function CloneProjectModal({
  project,
  onClose,
  onCloned,
}: {
  project: Project;
  onClose: () => void;
  onCloned: (id: string) => void;
}) {
  const [form, setForm] = useState({
    name: `${project.name} (copy)`,
    seed_keyword: project.seed_keyword,
    seed_is_brand: Boolean(project.seed_is_brand),
    site_id: project.site_id,
    country: project.country,
    language: project.language,
    author_id: "" as string,
  });

  const { data: sites } = useQuery({
    queryKey: ["sites"],
    queryFn: () => sitesApi.getAll(),
  });
  const { data: authors } = useQuery({
    queryKey: ["authors"],
    queryFn: () => authorsApi.getAll(),
  });

  const filteredAuthors = (authors || []).filter(
    (a: Author) => a.country === form.country && a.language === form.language
  );

  const mutation = useMutation({
    mutationFn: () => {
      const authorId =
        form.author_id && form.author_id.trim() !== ""
          ? Number(form.author_id)
          : undefined;
      return projectsApi.cloneProject(project.id, {
        name: form.name,
        seed_keyword: form.seed_keyword,
        seed_is_brand: form.seed_is_brand,
        target_site: form.site_id,
        country: form.country,
        language: form.language,
        ...(authorId != null && !Number.isNaN(authorId) ? { author_id: authorId } : {}),
      });
    },
    onSuccess: (data) => {
      toast.success("Project cloned — use Start to queue generation");
      onCloned(data.id);
    },
    onError: (e: unknown) => {
      const ax = e as { response?: { data?: { detail?: unknown } }; message?: string };
      toast.error(
        formatApiErrorDetail(ax.response?.data?.detail) || ax.message || "Clone failed"
      );
    },
  });

  const onSiteChange = (siteId: string) => {
    const site = (sites || []).find((s: Site) => s.id === siteId);
    setForm((prev) => ({
      ...prev,
      site_id: siteId,
      country: site ? site.country : prev.country,
      language: site ? site.language : prev.language,
      author_id: "",
    }));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg overflow-hidden flex flex-col max-h-[90vh]">
        <div className="px-6 py-4 border-b bg-slate-50 flex justify-between items-center shrink-0">
          <h2 className="text-lg font-bold text-slate-900">Clone project</h2>
          <button type="button" onClick={onClose} className="p-1 hover:bg-slate-200 rounded text-slate-500">
            ×
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Name</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full border rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Seed keyword</label>
            <input
              type="text"
              value={form.seed_keyword}
              onChange={(e) => setForm({ ...form, seed_keyword: e.target.value })}
              className="w-full border rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={form.seed_is_brand}
              onChange={(e) => setForm({ ...form, seed_is_brand: e.target.checked })}
            />
            Brand seed
          </label>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Target site</label>
            <select
              value={form.site_id}
              onChange={(e) => onSiteChange(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm bg-white"
            >
              {(sites || []).map((s: Site) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.domain})
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Country</label>
              <input
                type="text"
                value={form.country}
                onChange={(e) => setForm({ ...form, country: e.target.value, author_id: "" })}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Language</label>
              <input
                type="text"
                value={form.language}
                onChange={(e) => setForm({ ...form, language: e.target.value, author_id: "" })}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Author</label>
            <select
              value={form.author_id}
              onChange={(e) => setForm({ ...form, author_id: e.target.value })}
              className="w-full border rounded-lg px-3 py-2 text-sm bg-white"
            >
              <option value="">Auto (by country/language)</option>
              {filteredAuthors.map((a: Author) => (
                <option key={a.id} value={a.id}>
                  {a.author || a.id}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="flex justify-end gap-3 px-6 py-4 border-t bg-slate-50 shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-slate-600 hover:bg-slate-200 rounded-lg text-sm font-medium"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={mutation.isPending}
            onClick={() => mutation.mutate()}
            className="px-4 py-2 bg-slate-900 text-white rounded-lg text-sm font-medium disabled:opacity-50"
          >
            {mutation.isPending ? "Cloning…" : "Clone"}
          </button>
        </div>
      </div>
    </div>
  );
}
