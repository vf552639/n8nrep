import axios from "axios";
import toast from "react-hot-toast";
import { formatApiErrorDetail } from "@/lib/apiErrorMessage";

const api = axios.create({
  // Fallback to localhost:8000/api if the env variable isn't set
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000/api",
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("api_key");
    if (token) {
      config.headers["Authorization"] = `Bearer ${token}`;
      config.headers["X-API-Key"] = token;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const cfg = error.config;
    if (error.response?.status === 401 || error.response?.status === 403) {
      if (!cfg?.skipErrorToast) {
        toast.error("Authentication failed or missing API Key.");
      }
    } else if (!cfg?.skipErrorToast) {
      const raw = error.response?.data?.detail;
      const msg =
        formatApiErrorDetail(raw) ||
        error.message ||
        "An unknown error occurred";
      toast.error(msg);
    }
    return Promise.reject(error);
  }
);

export default api;
