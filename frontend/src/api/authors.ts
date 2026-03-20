import api from "./client";
import { Author } from "@/types/author";

export const authorsApi = {
  getAll: (params?: { skip?: number; limit?: number }) => 
    api.get<Author[]>("/authors", { params }).then(res => res.data),
    
  getOne: (id: string) => 
    api.get<Author>(`/authors/${id}`).then(res => res.data),
    
  create: (data: Partial<Author>) => 
    api.post<Author>("/authors", data).then(res => res.data),
};
