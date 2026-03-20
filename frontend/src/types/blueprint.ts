export interface Blueprint {
  id: string;
  name: string;
  description?: string;
  created_at: string;
}

export interface BlueprintPage {
  id: string;
  blueprint_id: string;
  page_slug: string;
  page_title: string;
  page_type: string;
  keyword_template: string;
  keyword_template_brand?: string;
  filename: string;
  sort_order: number;
  show_in_nav: boolean;
  show_in_footer: boolean;
  use_serp: boolean;
}
