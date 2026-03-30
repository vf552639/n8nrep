import api from "./client";
import { Blueprint, BlueprintPage } from "@/types/blueprint";

export const blueprintsApi = {
  getAll: (params?: { skip?: number; limit?: number }) => 
    api.get<Blueprint[]>("/blueprints", { params }).then(res => res.data),
    
  getOne: (id: string) => 
    api.get<Blueprint>(`/blueprints/${id}`).then(res => res.data),
    
  create: (data: Partial<Blueprint>) => 
    api.post<Blueprint>("/blueprints", data).then(res => res.data),
    
  getPages: (id: string) => 
    api.get<BlueprintPage[]>(`/blueprints/${id}/pages`).then(res => res.data),
    
  createPage: (id: string, data: Partial<BlueprintPage>) => 
    api.post<BlueprintPage>(`/blueprints/${id}/pages`, data).then(res => res.data),

  updatePage: (id: string, pageId: string, data: Partial<BlueprintPage>) =>
    api.put<BlueprintPage>(`/blueprints/${id}/pages/${pageId}`, data).then(res => res.data),

  deletePage: (id: string, pageId: string) =>
    api.delete<{ status: string }>(`/blueprints/${id}/pages/${pageId}`).then(res => res.data),
};
