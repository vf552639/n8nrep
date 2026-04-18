export interface Site {
  id: string;
  name: string;
  domain: string;
  country: string;
  language: string;
  is_active: boolean;
  template_id?: string | null;
  template_name?: string | null;
  /** True when site.template_id is set (same as Boolean(template_id); explicit for UI). */
  has_template?: boolean;
  legal_info?: Record<string, string>;
  niche?: string;
}

export interface SiteCreateInput {
  name: string;
  domain: string;
  country: string;
  language: string;
  is_active?: boolean;
  template_id?: string | null;
  legal_info?: Record<string, string>;
}

export interface SiteUpdateInput {
  name?: string;
  domain?: string;
  country?: string;
  language?: string;
  is_active?: boolean;
  template_id?: string | null;
  legal_info?: Record<string, string>;
}
