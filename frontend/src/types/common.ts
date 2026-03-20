export interface PaginatedList<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

export interface ApiResponse<T> {
  data?: T;
  message?: string;
  detail?: string;
}

export interface DashboardStats {
  total: number;
  processing: number;
  completed: number;
  failed: number;
  pending: number;
}
