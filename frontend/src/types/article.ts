export interface Article {
  id: string;
  task_id: string;
  title: string;
  description: string;
  html_content: string;
  full_page_html?: string;
  word_count: number;
  char_count?: number;
  /** Total pipeline cost from linked task */
  total_cost?: number;
  /** @deprecated use total_cost */
  cost?: number;
  main_keyword?: string;
  fact_check_status?: string;
  fact_check_issues?: FactCheckIssue[] | Record<string, unknown>[] | null;
  needs_review?: boolean;
  created_at: string;
}

export interface FactCheckIssue {
  claim: string;
  severity:
    | "critical"
    | "high"
    | "medium"
    | "low"
    | "warning"
    | "info"
    | string;
  problem?: string;
  suggestion?: string;
  recommendation?: string;
  location?: string;
  confidence?: string;
  resolved?: boolean;
}
