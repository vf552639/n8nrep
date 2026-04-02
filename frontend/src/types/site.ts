export interface Site {
  id: string;
  name: string;
  domain: string;
  country: string;
  language: string;
  is_active: boolean;
  template_id?: string | null;
  template_name?: string | null;
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
