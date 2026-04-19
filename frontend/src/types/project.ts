export interface ProjectLogEntry {
  ts: string;
  msg: string;
  level?: string;
}

export interface SerpHealthInfo {
  status?: string;
  latency_ms?: number | null;
  detail?: string | null;
}

export interface ProjectPreview {
  blueprint: { id: string; name: string; total_pages: number };
  site: {
    id: string | null;
    name: string;
    domain: string;
    has_template: boolean;
    use_site_template: boolean;
    will_be_created: boolean;
  };
  author: {
    id: number | null;
    name: string | null;
    source: "manual" | "auto" | "none";
  };
  pages: Array<{
    sort_order: number;
    page_slug: string;
    page_title: string;
    page_type: string;
    keyword: string;
    template_used: "standard" | "brand";
    use_serp: boolean;
    pipeline_preset: string;
    filename: string;
  }>;
  warnings: string[];
  estimated_cost: number | null;
  avg_cost_per_page: number | null;
  serp_config?: Record<string, unknown>;
  serp_health?: Record<string, unknown>;
}

export interface Project {
  id: string;
  name: string;
  seed_keyword: string;
  seed_is_brand?: boolean;
  blueprint_id: string;
  site_id: string;
  country: string;
  language: string;
  author_id?: string;
  status: "pending" | "generating" | "stopped" | "completed" | "failed" | "awaiting_page_approval";
  progress: number;
  error_log?: string | null;
  created_at: string;
  tasks?: ProjectTaskExpanded[];
  is_archived?: boolean;
  total_tasks?: number;
  completed_tasks?: number;
  failed_tasks?: number;
  failed_count?: number;
  total_cost?: number;
  avg_cost_per_page?: number;
  started_at?: string | null;
  generation_started_at?: string | null;
  completed_at?: string | null;
  duration_seconds?: number | null;
  avg_seconds_per_page?: number | null;
  blueprint_page_count?: number;
  remaining_pages?: number;
  log_events?: ProjectLogEntry[];
  celery_task_id?: string | null;
  serp_config?: Record<string, unknown>;
  project_keywords?: {
    raw?: string[];
    clustered?: Record<
      string,
      { page_title: string; keyword: string; assigned_keywords: string[] }
    >;
    unassigned?: string[];
    clustering_model?: string;
    clustering_cost?: number;
  } | null;
  legal_template_map?: Record<string, string>;
  use_site_template?: boolean;
}

export interface ProjectTaskExpanded {
  id: string;
  blueprint_page_id: string | null;
  status: string;
  main_keyword: string;
  page_type: string;
  progress: number;
  current_step: string | null;
}

export interface ProjectClonePayload {
  name?: string;
  seed_keyword?: string;
  seed_is_brand?: boolean;
  target_site?: string;
  country?: string;
  language?: string;
  author_id?: number;
  legal_template_map?: Record<string, string>;
  use_site_template?: boolean;
}
