import api from "./client";

export const dashboardApi = {
  getStats: () => api.get("/dashboard/stats").then((res) => res.data),

  getQueue: () => api.get("/dashboard/queue").then((res) => res.data),

  getSerpHealth: (force?: boolean) =>
    api
      .get<Record<string, unknown>>("/health/serp", {
        params: force ? { force: true } : {},
      })
      .then((res) => res.data),
};
