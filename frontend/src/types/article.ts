export interface Article {
  id: string;
  task_id: string;
  title: string;
  description: string;
  html_content: string;
  full_page_html?: string;
  word_count: number;
  char_count?: number;
  cost?: number;
  fact_check_status?: 'passed' | 'needs_review' | 'failed';
  needs_review?: boolean;
  created_at: string;
}

export interface FactCheckIssue {
  claim: string;
  severity: "high" | "medium" | "low";
  recommendation: string;
}
