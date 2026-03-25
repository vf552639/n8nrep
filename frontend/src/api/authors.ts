import api from "./client";
import { Author, AuthorFormPayload } from "@/types/author";

export const authorsApi = {
  getAll: (params?: { skip?: number; limit?: number }) => 
    api.get<Author[]>("/authors", { params }).then(res => res.data),
    
  getOne: (id: string) => 
    api.get<Author>(`/authors/${id}`).then(res => res.data),

  create: (data: AuthorFormPayload) => 
    api.post<{ id: string }>("/authors", data).then(res => res.data),

  update: (id: string, data: AuthorFormPayload) =>
    api.put<{ id: string; status: string }>(`/authors/${id}`, data).then((res) => res.data),
};
