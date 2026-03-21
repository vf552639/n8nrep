import api from "./client";
import { Task, TaskCreate, TaskStepResponse } from "@/types/task";

export const tasksApi = {
  getAll: (params?: { skip?: number; limit?: number; status?: string }) => 
    api.get<Task[]>("/tasks", { params }).then(res => res.data),
  
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
    
  delete: (id: string) => 
    api.delete(`/tasks/${id}`).then(res => res.data),
    
  forceStatus: (id: string, action: "complete" | "fail") => 
    api.post(`/tasks/${id}/force-status`, { action }).then(res => res.data),
    
  rerunStep: (id: string, cascade: boolean, step_name: string, feedback: string) =>
    api.post(`/tasks/${id}/rerun-step`, { step_name, cascade, feedback }).then(res => res.data),
};
