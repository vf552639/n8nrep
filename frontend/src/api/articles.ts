import api from "./client";
import { Article } from "@/types/article";

export const articlesApi = {
  getAll: (params?: { skip?: number; limit?: number }) =>
    api.get<Article[]>("/articles", { params }).then((res) => res.data),

  getOne: (id: string) => api.get<Article>(`/articles/${id}`).then((res) => res.data),

  update: (id: string, data: { html_content?: string; title?: string; description?: string }) =>
    api.patch<Article>(`/articles/${id}`, data).then((res) => res.data),

  getPreview: (id: string) => api.get<string>(`/articles/${id}/preview`).then((res) => res.data),

  resolveIssue: (id: string, issueIndex: number) =>
    api.post(`/articles/${id}/issues/${issueIndex}/resolve`).then((res) => res.data),

  downloadBlob: async (id: string, format: "html" | "docx" = "html") => {
    const res = await api.get<Blob>(`/articles/${id}/download`, {
      params: format === "docx" ? { format: "docx" } : {},
      responseType: "blob",
    });
    return res.data;
  },
};
