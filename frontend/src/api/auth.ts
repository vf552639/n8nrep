import api from "@/api/client";
import type { LoginStartResponse, LoginStatus } from "@/types/auth";

export const codexAuthApi = {
  status: () => api.get<LoginStatus>("/auth/codex/status").then((r) => r.data),
  login: () => api.post<LoginStartResponse>("/auth/codex/login").then((r) => r.data),
  logout: () => api.post<{ logged_out: boolean }>("/auth/codex/logout").then((r) => r.data),
};
