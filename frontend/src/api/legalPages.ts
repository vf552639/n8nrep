import api from "@/api/client";
import type {
  LegalForBlueprintResponse,
  LegalPageTemplateFull,
  LegalPageTemplateRow,
} from "@/types/template";

export const legalPagesApi = {
  getAll: (pageType?: string) =>
    api
      .get<LegalPageTemplateRow[]>("/legal-pages", {
        params: pageType ? { page_type: pageType } : {},
      })
      .then((r) => r.data),
  getOne: (id: string) => api.get<LegalPageTemplateFull>(`/legal-pages/${id}`).then((r) => r.data),
  getPageTypes: () =>
    api.get<{ page_types: string[] }>("/legal-pages/meta/page-types").then((r) => r.data.page_types),
  getForBlueprint: (blueprintId: string) =>
    api
      .get<LegalForBlueprintResponse>(`/legal-pages/for-blueprint/${blueprintId}`)
      .then((r) => r.data),
  getByPageType: (pageType: string) =>
    api
      .get<{ id: string; name: string; page_type: string; content_format: string }[]>(
        `/legal-pages/by-page-type/${pageType}`
      )
      .then((r) => r.data),
  create: (data: {
    name: string;
    page_type: string;
    content: string;
    content_format?: "text" | "html";
    variables?: Record<string, unknown>;
    notes?: string | null;
    is_active?: boolean;
  }) => api.post<{ id: string }>("/legal-pages", data).then((r) => r.data),
  update: (id: string, data: Partial<Omit<LegalPageTemplateFull, "id">>) =>
    api.put<{ id: string }>(`/legal-pages/${id}`, data).then((r) => r.data),
  delete: (id: string) => api.delete(`/legal-pages/${id}`).then((r) => r.data),
};
