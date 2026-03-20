import api from "./client";
import { Project, ProjectTask } from "@/types/project";

export const projectsApi = {
  getAll: (params?: { skip?: number; limit?: number }) => 
    api.get<Project[]>("/projects", { params }).then(res => res.data),
    
  getOne: (id: string) => 
    api.get<Project>(`/projects/${id}`).then(res => res.data),
    
  create: (data: Partial<Project>) => 
    api.post<Project>("/projects", data).then(res => res.data),
    
  stopProject: (id: string) => 
    api.post(`/projects/${id}/stop`).then(res => res.data),
    
  resumeProject: (id: string) => 
    api.post(`/projects/${id}/resume`).then(res => res.data),
    
  getTasks: (id: string) => 
    api.get<ProjectTask[]>(`/projects/${id}/tasks`).then(res => res.data),
};
