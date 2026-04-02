import api from "@/api/client";
import type { LegalPageTemplateFull, LegalPageTemplateRow } from "@/types/template";

export const legalPagesApi = {
  getAll: (country?: string) =>
    api
      .get<LegalPageTemplateRow[]>("/legal-pages", { params: country ? { country } : {} })
      .then((r) => r.data),
  getOne: (id: string) => api.get<LegalPageTemplateFull>(`/legal-pages/${id}`).then((r) => r.data),
  getPageTypes: () => api.get<{ page_types: string[] }>("/legal-pages/meta/page-types").then((r) => r.data.page_types),
  create: (data: {
    country: string;
    page_type: string;
    title: string;
    html_content: string;
    variables?: Record<string, unknown>;
    notes?: string | null;
    is_active?: boolean;
  }) => api.post<{ id: string }>("/legal-pages", data).then((r) => r.data),
  update: (id: string, data: Partial<Omit<LegalPageTemplateFull, "id">>) =>
    api.put<{ id: string }>(`/legal-pages/${id}`, data).then((r) => r.data),
  delete: (id: string) => api.delete(`/legal-pages/${id}`).then((r) => r.data),
};
