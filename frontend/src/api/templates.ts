import api from "@/api/client";
import type { HtmlTemplate, HtmlTemplateInput } from "@/types/template";

export const templatesApi = {
  getAll: () => api.get<HtmlTemplate[]>("/templates").then((r) => r.data),
  getOne: (id: string) => api.get<HtmlTemplate>(`/templates/${id}`).then((r) => r.data),
  create: (data: HtmlTemplateInput) => api.post<{ id: string }>("/templates", data).then((r) => r.data),
  update: (id: string, data: Partial<HtmlTemplateInput>) =>
    api.put<{ id: string }>(`/templates/${id}`, data).then((r) => r.data),
  delete: (id: string) => api.delete(`/templates/${id}`).then((r) => r.data),
};
