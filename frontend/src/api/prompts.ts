import api from "./client";
import { Prompt, PromptVersion } from "@/types/prompt";

export const promptsApi = {
  getAll: (params?: { skip?: number; limit?: number }) => 
    api.get<Prompt[]>("/prompts", { params }).then(res => res.data),
    
  getOne: (id: string) => 
    api.get<Prompt>(`/prompts/${id}`).then(res => res.data),
    
  update: (data: Partial<Prompt>) => 
    api.post<Prompt>(`/prompts/`, data).then(res => res.data),
    
  getVersions: (id: string) => 
    api.get<PromptVersion[]>(`/prompts/${id}/versions`).then(res => res.data),
    
  restoreVersion: (id: string, versionId: string) => 
    api.post(`/prompts/${id}/versions/${versionId}/restore`).then(res => res.data),
    
  testPrompt: (
    id: string,
    data: { context: Record<string, unknown>; model: string; max_tokens?: number | null }
  ) => api.post(`/prompts/${id}/test`, data).then((res) => res.data),
};
