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
  tasks?: ProjectTaskExpanded[];
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
