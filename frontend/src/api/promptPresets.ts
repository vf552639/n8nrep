import api from "@/api/client";
import type { PromptPreset, PromptPresetCreate } from "@/types/promptPreset";

export const promptPresetsApi = {
  list: () => api.get<PromptPreset[]>("/prompt-presets").then((r) => r.data),
  get: (id: string) => api.get<PromptPreset>(`/prompt-presets/${id}`).then((r) => r.data),
  create: (body: PromptPresetCreate) =>
    api.post<PromptPreset>("/prompt-presets", body).then((r) => r.data),
  update: (id: string, body: PromptPresetCreate) =>
    api.put<PromptPreset>(`/prompt-presets/${id}`, body).then((r) => r.data),
  remove: (id: string) => api.delete<void>(`/prompt-presets/${id}`).then(() => undefined),
};
