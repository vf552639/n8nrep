export interface Task {
  id: string;
  main_keyword: string;
  country: string;
  language: string;
  target_site_id: string;
  author_id?: string;
  status: "pending" | "processing" | "completed" | "failed";
  error_log?: string;
  created_at: string;
  updated_at: string;
  progress: number;
  cost: number;
}

export interface TaskCreate {
  main_keyword: string;
  country: string;
  language: string;
  target_site_id: string;
  author_id?: string;
  page_type?: string;
}

export interface StepResult {
  step_name: string;
  status: "pending" | "running" | "completed" | "failed" | "skipped";
  duration_ms?: number;
  cost?: number;
  result_data?: any;
  error?: string;
}
