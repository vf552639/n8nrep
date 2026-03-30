import "axios";

declare module "axios" {
  interface AxiosRequestConfig {
    /** When true, response error interceptor skips `toast.error` (caller handles). */
    skipErrorToast?: boolean;
  }
}
