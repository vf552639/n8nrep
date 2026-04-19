import api from "./client";
import {
  Project,
  ProjectClonePayload,
  ProjectPreview,
  ProjectTaskExpanded as ProjectTask,
} from "@/types/project";

/** Matches backend `SiteProjectCreate` — use `target_site` (site UUID or domain/name); omit for markup-only. */
export interface SiteProjectCreatePayload {
  name: string;
  blueprint_id: string;
  target_site?: string;
  seed_keyword: string;
  seed_is_brand?: boolean;
  country: string;
  language: string;
  author_id?: number;
  serp_config?: {
    search_engine?: "google" | "bing" | "google+bing";
    depth?: number;
    device?: "mobile" | "desktop";
    os?: string;
  };
  project_keywords?: {
    raw?: string[];
    clustered?: Record<
      string,
      { page_title: string; keyword: string; assigned_keywords: string[] }
    >;
    unassigned?: string[];
    clustering_model?: string;
    clustering_cost?: number;
  };
  legal_template_map?: Record<string, string>;
  use_site_template?: boolean;
}

export interface ClusterKeywordsResult {
  clustered: Record<
    string,
    { page_title: string; keyword: string; assigned_keywords: string[] }
  >;
  unassigned: string[];
  total_keywords: number;
  total_assigned: number;
  cost: number;
  model?: string;
}

export interface ProjectCreateResponse {
  id: string;
  status: string;
  serp_warning?: string | null;
}

export const projectsApi = {
  getAll: (params?: {
    skip?: number;
    limit?: number;
    archived?: boolean;
    status?: string;
    search?: string;
  }) => api.get<Project[]>("/projects", { params }).then((res) => res.data),

  getOne: (id: string) => api.get<Project>(`/projects/${id}`).then((res) => res.data),

  preview: (
    data: Omit<SiteProjectCreatePayload, "name"> & { name?: string }) =>
    api.post<ProjectPreview>("/projects/preview", data).then((res) => res.data),

  create: (data: SiteProjectCreatePayload) =>
    api
      .post<ProjectCreateResponse>("/projects", data, {
        skipErrorToast: true,
      })
      .then((res) => res.data),

  archiveProject: (id: string) =>
    api.post<{ msg: string; project_id: string; is_archived: boolean }>(`/projects/${id}/archive`).then((res) => res.data),

  unarchiveProject: (id: string) =>
    api.post<{ msg: string; project_id: string; is_archived: boolean }>(`/projects/${id}/unarchive`).then((res) => res.data),

  deleteProject: (id: string, opts?: { force?: boolean }) =>
    api
      .delete<{ msg: string; project_id: string }>(`/projects/${id}`, {
        params: opts?.force ? { force: true } : {},
      })
      .then((res) => res.data),

  deleteSelected: (projectIds: string[], opts?: { force?: boolean }) =>
    api
      .post<{ deleted: number; skipped: number }>("/projects/delete-selected", {
        project_ids: projectIds,
        force: Boolean(opts?.force),
      })
      .then((res) => res.data),

  resetProjectStatus: (id: string) =>
    api
      .post<{ msg: string; project_id: string; status: string }>(`/projects/${id}/reset-status`)
      .then((res) => res.data),

  retryFailedPages: (id: string) =>
    api.post<{ msg: string; project_id: string; retried_count: number }>(`/projects/${id}/retry-failed`).then((res) => res.data),
  approvePage: (id: string) =>
    api.post<{ msg: string; project_id: string }>(`/projects/${id}/approve-page`).then((res) => res.data),
  rebuildZip: (id: string) =>
    api
      .post<{ msg: string; zip_path: string }>(`/projects/${id}/rebuild-zip`)
      .then((res) => res.data),

  stopProject: (id: string) => api.post(`/projects/${id}/stop`).then((res) => res.data),

  resumeProject: (id: string) => api.post(`/projects/${id}/resume`).then((res) => res.data),

  startProject: (id: string) =>
    api
      .post<{ msg: string; project_id: string; celery_task_id: string }>(
        `/projects/${id}/start`
      )
      .then((res) => res.data),

  cloneProject: (id: string, body: ProjectClonePayload) =>
    api
      .post<{ id: string; status: string; message: string }>(`/projects/${id}/clone`, body)
      .then((res) => res.data),

  getTasks: (id: string) => api.get<ProjectTask[]>(`/projects/${id}/tasks`).then((res) => res.data),

  exportCsv: async (id: string) => {
    const res = await api.get<Blob>(`/projects/${id}/export-csv`, { responseType: "blob" });
    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = url;
    const disp = res.headers["content-disposition"] as string | undefined;
    const m = disp?.match(/filename="?([^";]+)"?/);
    a.download = m?.[1]?.trim() || `project_${id}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },

  clusterKeywords: (body: { keywords: string[]; blueprint_id: string }) =>
    api.post<ClusterKeywordsResult>("/projects/cluster-keywords", body).then((res) => res.data),

  exportDocx: async (id: string) => {
    const res = await api.get<Blob>(`/projects/${id}/export-docx`, { responseType: "blob" });
    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = url;
    const disp = res.headers["content-disposition"] as string | undefined;
    const m = disp?.match(/filename="?([^";]+)"?/);
    a.download = m?.[1]?.trim() || `project_${id}.docx`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },

  exportHtmlZipUrl: (id: string) =>
    `${import.meta.env.VITE_API_URL || "http://localhost:8000/api"}/projects/${id}/export-html?mode=zip`,

  exportHtmlConcatUrl: (id: string) =>
    `${import.meta.env.VITE_API_URL || "http://localhost:8000/api"}/projects/${id}/export-html?mode=concat`,

  exportHtmlZip: async (id: string) => {
    const res = await api.get<Blob>(`/projects/${id}/export-html`, {
      params: { mode: "zip" },
      responseType: "blob",
    });
    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = url;
    const disp = res.headers["content-disposition"] as string | undefined;
    const m = disp?.match(/filename="?([^";]+)"?/);
    a.download = m?.[1]?.trim() || `project_${id}.html.zip`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },

  exportHtmlConcat: async (id: string) => {
    const res = await api.get<Blob>(`/projects/${id}/export-html`, {
      params: { mode: "concat" },
      responseType: "blob",
    });
    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = url;
    const disp = res.headers["content-disposition"] as string | undefined;
    const m = disp?.match(/filename="?([^";]+)"?/);
    a.download = m?.[1]?.trim() || `project_${id}.html`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },
};
