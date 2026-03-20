export interface Project {
  id: string;
  name: string;
  seed_keyword: string;
  target_site_id: string;
  country: string;
  language: string;
  author_id?: string;
  status: "pending" | "generating" | "stopped" | "completed" | "failed";
  progress: number;
  created_at: string;
}

export interface ProjectTask {
  id: string;
  project_id: string;
  task_id: string;
  page_slug: string;
}
