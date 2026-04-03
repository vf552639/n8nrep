import api from "./client";
import { Prompt, PromptVersion } from "@/types/prompt";

export interface PromptSaveResponse {
  id: string;
  version: number;
}

export const promptsApi = {
  getAll: (params?: { skip?: number; limit?: number }) => 
    api.get<Prompt[]>("/prompts", { params }).then(res => res.data),
    
  getOne: (id: string) => 
    api.get<Prompt>(`/prompts/${id}`).then(res => res.data),
    
  update: (data: Partial<Prompt>) =>
    api.post<PromptSaveResponse>(`/prompts/`, data).then(res => res.data),

  /** Save edits to the same DB row (no new version). */
  updateInPlace: (
    id: string,
    data: {
      system_prompt: string;
      user_prompt: string;
      model: string;
      max_tokens?: number | null;
      temperature: number;
      frequency_penalty?: number;
      presence_penalty?: number;
      top_p?: number;
      skip_in_pipeline: boolean;
    }
  ) => api.put<Prompt>(`/prompts/${id}`, data).then((res) => res.data),
    
  getVersions: (id: string) => 
    api.get<PromptVersion[]>(`/prompts/${id}/versions`).then(res => res.data),
    
  restoreVersion: (id: string, versionId: string) => 
    api.post(`/prompts/${id}/versions/${versionId}/restore`).then(res => res.data),
    
  testPrompt: (
    id: string,
    data: { context: Record<string, unknown>; model: string; max_tokens?: number | null }
  ) => api.post(`/prompts/${id}/test`, data).then((res) => res.data),
};
