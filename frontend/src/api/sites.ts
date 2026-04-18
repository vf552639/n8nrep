import api from "@/api/client";
import { Site, SiteCreateInput, SiteUpdateInput } from "@/types/site";

export const sitesApi = {
  getAll: () => api.get<Site[]>("/sites").then((res) => res.data),
  getOne: (id: string) => api.get<Site>(`/sites/${id}`).then((res) => res.data),
  create: (data: SiteCreateInput) => api.post<{ id: string }>("/sites", data).then((res) => res.data),
  update: (id: string, data: SiteUpdateInput) => api.patch<{ id: string }>(`/sites/${id}`, data).then((res) => res.data),
  delete: (id: string, opts?: { force?: boolean }) =>
    api
      .delete<{ msg: string; site_id?: string }>(`/sites/${id}`, {
        params: opts?.force ? { force: true } : {},
      })
      .then((res) => res.data),
};
