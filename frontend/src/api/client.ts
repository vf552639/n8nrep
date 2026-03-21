import axios from "axios";
import toast from "react-hot-toast";

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
    if (error.response?.status === 401 || error.response?.status === 403) {
      toast.error("Authentication failed or missing API Key.");
    } else {
      // Attempt to extract the detail message from FastAPI HTTPExceptions
      const msg = error.response?.data?.detail || error.message || "An unknown error occurred";
      toast.error(msg);
    }
    return Promise.reject(error);
  }
);

export default api;
