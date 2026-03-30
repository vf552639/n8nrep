import api from "./client";
import { Project, ProjectTaskExpanded as ProjectTask } from "@/types/project";

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
}

export const projectsApi = {
  getAll: (params?: { skip?: number; limit?: number }) => 
    api.get<Project[]>("/projects", { params }).then(res => res.data),
    
  getOne: (id: string) => 
    api.get<Project>(`/projects/${id}`).then(res => res.data),
    
  create: (data: SiteProjectCreatePayload) =>
    api
      .post<{ id: string; status: string }>("/projects", data, {
        skipErrorToast: true,
      })
      .then((res) => res.data),
    
  stopProject: (id: string) => 
    api.post(`/projects/${id}/stop`).then(res => res.data),
    
  resumeProject: (id: string) => 
    api.post(`/projects/${id}/resume`).then(res => res.data),
    
  getTasks: (id: string) => 
    api.get<ProjectTask[]>(`/projects/${id}/tasks`).then(res => res.data),
};
