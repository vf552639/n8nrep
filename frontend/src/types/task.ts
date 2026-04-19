export interface Task {
  id: string;
  main_keyword: string;
  additional_keywords?: string;
  country: string;
  language: string;
  target_site_id?: string;
  author_id?: string;
  page_type: string;
  status: "pending" | "processing" | "completed" | "failed" | "stale" | "paused";
  error_log?: string | null;
  created_at: string;
  total_cost?: number;
  outline?: any;
  serp_data?: any;
  step_results?: any;
  serp_config?: SerpConfig;
  /** Pipeline execution log lines (backend: log_events) */
  log_events?: any[];
}

export interface SerpConfig {
  search_engine: "google" | "bing" | "google+bing";
  depth: 10 | 20 | 30 | 50 | 100;
  device: "mobile" | "desktop";
  os: "android" | "ios" | "windows" | "macos";
}

export interface TaskCreate {
  main_keyword: string;
  additional_keywords?: string;
  country: string;
  language: string;
  target_site: string;
  author_id?: string | null;
  page_type?: string;
  serp_config?: SerpConfig;
}

export interface StepResult {
  status: "pending" | "running" | "completed" | "failed" | "skipped";
  duration_ms?: number;
  cost?: number;
  result?: any;
  error?: string;
  timestamp?: string;
  resolved_prompts?: { system_prompt?: string; user_prompt?: string } | null;
  variables_snapshot?: Record<string, string> | null;
  exclude_words_violations?: Record<string, number> | string[] | null;
  input_word_count?: number;
  output_word_count?: number;
  word_count_warning?: boolean;
  word_loss_percentage?: number;
  started_at?: string;
}

export interface TaskStepResponse {
  task_id: string;
  status: string;
  total_cost: number;
  progress: number;
  step_results: Record<string, StepResult>;
  current_step?: string;
}
