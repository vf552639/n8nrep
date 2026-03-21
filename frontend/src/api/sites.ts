import api from "./client";
import { Site, SiteTemplate } from "@/types/site";

export const sitesApi = {
  getAll: (params?: { skip?: number; limit?: number }) => 
    api.get<Site[]>("/sites", { params }).then(res => res.data),
    
  getOne: (id: string) => 
    api.get<Site>(`/sites/${id}`).then(res => res.data),
    
  create: (data: Partial<Site>) => 
    api.post<Site>("/sites", data).then(res => res.data),

  delete: (id: string) =>
    api.delete(`/sites/${id}`).then((res) => res.data),
    
  getTemplates: (id: string) => 
    api.get<SiteTemplate[]>(`/sites/${id}/templates`).then(res => res.data),
    
  createTemplate: (id: string, data: Partial<SiteTemplate>) => 
    api.post<SiteTemplate>(`/sites/${id}/templates`, data).then(res => res.data),
};
