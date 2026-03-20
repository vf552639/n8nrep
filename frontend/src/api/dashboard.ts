import api from "./client";

export const dashboardApi = {
  getStats: () => 
    api.get("/dashboard/stats").then(res => res.data),
    
  getQueue: () => 
    api.get("/dashboard/queue").then(res => res.data),
};

export const settingsApi = {
  getSettings: () => 
    api.get("/settings/").then(res => res.data),
    
  updateSettings: (data: any) => 
    api.put("/settings/", data).then(res => res.data),
};
