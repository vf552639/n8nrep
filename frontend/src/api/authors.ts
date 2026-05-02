import api from "./client";
import { Author, AuthorFormPayload } from "@/types/author";

export type AuthorsListParams = {
  offset?: number;
  limit?: number;
  /** When true, includes bio, imitation, rhythms_style, exclude_words, etc. */
  full?: boolean;
};

export const authorsApi = {
  getAll: (params?: AuthorsListParams) =>
    api.get<Author[]>("/authors/", { params }).then((res) => res.data),

  getOne: (id: string) => api.get<Author>(`/authors/${id}`).then((res) => res.data),

  create: (data: AuthorFormPayload) => api.post<{ id: string }>("/authors", data).then((res) => res.data),

  update: (id: string, data: AuthorFormPayload) =>
    api.put<{ id: string; status: string }>(`/authors/${id}`, data).then((res) => res.data),
};

/** Aligns with React Query caching for author dropdowns (task51 egress). */
export const AUTHORS_LIST_STALE_MS = 5 * 60 * 1000;

export const authorsLightListQueryOptions = () =>
  ({
    queryKey: ["authors", "light"] as const,
    queryFn: () => authorsApi.getAll({ limit: 500 }),
    staleTime: AUTHORS_LIST_STALE_MS,
  }) as const;

export const authorsFullListQueryOptions = () =>
  ({
    queryKey: ["authors", "full"] as const,
    queryFn: () => authorsApi.getAll({ limit: 500, full: true }),
    staleTime: AUTHORS_LIST_STALE_MS,
  }) as const;
