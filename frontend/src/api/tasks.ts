import api from "./client";
import { Task, TaskCreate, TaskStepResponse } from "@/types/task";

export type TasksListResponse = { items: Task[]; total: number };

export const tasksApi = {
  getAll: (params?: {
    skip?: number;
    limit?: number;
    status?: string;
    search?: string;
    site_id?: string;
  }) => api.get<TasksListResponse>("/tasks", { params }).then((res) => res.data),
  
  getOne: (id: string) => 
    api.get<Task>(`/tasks/${id}`).then(res => res.data),
    
  getSteps: (id: string) => 
    api.get<TaskStepResponse>(`/tasks/${id}/steps`).then(res => res.data),
    
  create: (data: TaskCreate) => 
    api.post<{id: string, status: string}>("/tasks", data).then(res => res.data),
    
  bulkImport: (formData: FormData) =>
    api.post("/tasks/bulk", formData, {
      headers: { "Content-Type": "multipart/form-data" }
    }).then(res => res.data),
    
  startNext: () => 
    api.post("/tasks/next").then(res => res.data),
    
  startAll: () => 
    api.post("/tasks/start-all").then(res => res.data),

  startSelected: (taskIds: string[]) =>
    api.post<{ started: number; msg: string }>("/tasks/start-selected", { task_ids: taskIds }).then((res) => res.data),

  deleteSelected: (taskIds: string[]) =>
    api.post<{ deleted: number }>("/tasks/delete-selected", { task_ids: taskIds }).then((res) => res.data),

  retry: (id: string) => api.post<{ msg: string }>(`/tasks/${id}/retry`).then((res) => res.data),
    
  delete: (id: string) => 
    api.delete(`/tasks/${id}`).then(res => res.data),
    
  forceStatus: (id: string, action: "complete" | "fail") => 
    api.post(`/tasks/${id}/force-status`, { action }).then(res => res.data),
    
  rerunStep: (id: string, cascade: boolean, step_name: string, feedback: string) =>
    api.post(`/tasks/${id}/rerun-step`, { step_name, cascade, feedback }).then(res => res.data),

  updateStepResult: (taskId: string, stepName: string, result: string) =>
    api
      .put<{ status: string }>(`/tasks/${taskId}/step-result`, {
        step_name: stepName,
        result,
      })
      .then((res) => res.data),

  approve: (id: string) =>
    api.post<{msg: string}>(`/tasks/${id}/approve`).then(res => res.data),

  getSerpUrls: (id: string) =>
    api
      .get<{
        urls: Array<{
          url: string;
          title: string;
          description: string;
          position: number;
          domain: string;
          manually_added: boolean;
        }>;
        paused: boolean;
        keyword: string;
      }>(`/tasks/${id}/serp-urls`)
      .then((res) => res.data),

  approveSerpUrls: (id: string, urls: string[]) =>
    api
      .post<{ msg: string; urls_count: number }>(`/tasks/${id}/approve-serp-urls`, { urls })
      .then((res) => res.data),

  getImages: (id: string) =>
    api.get<{ images: any[]; summary: any; paused: boolean }>(`/tasks/${id}/images`).then(res => res.data),

  approveImages: (id: string, approvedIds: string[], skippedIds: string[]) =>
    api.post<{ msg: string; approved_count: number; skipped_count: number }>(
      `/tasks/${id}/approve-images`, { approved_ids: approvedIds, skipped_ids: skippedIds }
    ).then(res => res.data),

  regenerateImage: (id: string, imageId: string, newPrompt?: string) =>
    api.post<{ image: any }>(
      `/tasks/${id}/regenerate-image`, { image_id: imageId, new_prompt: newPrompt || "" }
    ).then(res => res.data),

  exportDocx: async (id: string) => {
    const res = await api.get<Blob>(`/tasks/${id}/export-docx`, { responseType: "blob" });
    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = url;
    const disp = res.headers["content-disposition"] as string | undefined;
    const m = disp?.match(/filename="?([^";]+)"?/);
    a.download = m?.[1]?.trim() || `task_${id}.docx`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },
};

