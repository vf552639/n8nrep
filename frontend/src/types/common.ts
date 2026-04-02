// PaginatedList removed as backend returns T[] directly.
export interface ApiResponse<T> {
  data?: T;
  message?: string;
  detail?: string;
}

export interface DashboardStats {
  tasks: {
    total: number;
    completed: number;
    failed: number;
    processing: number;
    pending: number;
  };
  sites: number;
  sequential_mode: boolean;
  /** Last ~30 days, completed tasks only — sum of total_cost per UTC day */
  cost_by_day?: { date: string; cost: number }[];
}

export interface QueueStatus {
  celery_workers_online: boolean;
  active_tasks?: Record<string, any>;
  queued_tasks?: Record<string, any>;
  error?: string;
}
