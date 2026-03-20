export interface Site {
  id: string;
  name: string;
  domain: string;
  country: string;
  language: string;
  is_active: boolean;
  niche?: string;
}

export interface SiteTemplate {
  id: string;
  site_id: string;
  template_name: string;
  html_template: string;
  pages_config: any;
  usage_count: number;
  is_active: boolean;
}
