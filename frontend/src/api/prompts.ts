import api from "./client";
import { Prompt, PromptVersion } from "@/types/prompt";

export const promptsApi = {
  getAll: (params?: { skip?: number; limit?: number }) => 
    api.get<Prompt[]>("/prompts", { params }).then(res => res.data),
    
  getOne: (id: string) => 
    api.get<Prompt>(`/prompts/${id}`).then(res => res.data),
    
  update: (id: string, data: Partial<Prompt>) => 
    api.put<Prompt>(`/prompts/${id}`, data).then(res => res.data),
    
  getVersions: (id: string) => 
    api.get<PromptVersion[]>(`/prompts/${id}/versions`).then(res => res.data),
    
  restoreVersion: (id: string, versionId: string) => 
    api.post(`/prompts/${id}/versions/${versionId}/restore`).then(res => res.data),
    
  testPrompt: (id: string, data: { context: Record<string, any>; model: string }) =>
    api.post(`/prompts/${id}/test`, data).then(res => res.data),
};
