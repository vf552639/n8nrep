export interface Task {
  id: string;
  main_keyword: string;
  additional_keywords?: string;
  priority?: number;
  country: string;
  language: string;
  target_site_id?: string;
  author_id?: string;
  page_type: string;
  status: "pending" | "processing" | "completed" | "failed";
  error_log?: string | null;
  created_at: string;
  total_cost?: number;
  outline?: any;
  serp_data?: any;
  logs?: any[];
}

export interface TaskCreate {
  main_keyword: string;
  additional_keywords?: string;
  priority?: number;
  country: string;
  language: string;
  target_site_id: string;
  author_id?: string;
  page_type?: string;
}

export interface StepResult {
  status: "pending" | "running" | "completed" | "failed" | "skipped";
  duration_ms?: number;
  cost?: number;
  result?: any;
  error?: string;
  timestamp?: string;
}

export interface TaskStepResponse {
  task_id: string;
  status: string;
  total_cost: number;
  progress: number;
  step_results: Record<string, StepResult>;
  current_step?: string;
}
