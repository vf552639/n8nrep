import api from "./client";
import type { SiteTemplate, SiteTemplateInput } from "@/types/site";

export const siteTemplatesApi = {
  getAll: (siteId: string) =>
    api.get<SiteTemplateListItem[]>(`/sites/${siteId}/templates`).then((r) => r.data),

  getOne: (siteId: string, templateId: string) =>
    api.get<SiteTemplate>(`/sites/${siteId}/templates/${templateId}`).then((r) => r.data),

  create: (siteId: string, data: SiteTemplateInput) =>
    api.post<{ id: string }>(`/sites/${siteId}/templates`, data).then((r) => r.data),

  update: (siteId: string, templateId: string, data: Partial<SiteTemplateInput>) =>
    api.put<{ id: string }>(`/sites/${siteId}/templates/${templateId}`, data).then((r) => r.data),

  delete: (siteId: string, templateId: string) =>
    api.delete(`/sites/${siteId}/templates/${templateId}`).then((r) => r.data),
};

export interface SiteTemplateListItem {
  id: string;
  template_name: string;
  usage_count: number;
  is_active: boolean;
}
