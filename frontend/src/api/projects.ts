import api from "./client";
import {
  Project,
  ProjectClonePayload,
  ProjectPreview,
  ProjectTaskExpanded as ProjectTask,
} from "@/types/project";

/** Matches backend `SiteProjectCreate` — use `target_site` (site UUID or domain/name). */
export interface SiteProjectCreatePayload {
  name: string;
  blueprint_id: string;
  target_site: string;
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

  deleteProject: (id: string) =>
    api.delete<{ msg: string; project_id: string }>(`/projects/${id}`).then((res) => res.data),

  retryFailedPages: (id: string) =>
    api.post<{ msg: string; project_id: string; retried_count: number }>(`/projects/${id}/retry-failed`).then((res) => res.data),
  approvePage: (id: string) =>
    api.post<{ msg: string; project_id: string }>(`/projects/${id}/approve-page`).then((res) => res.data),

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
};
