/** List row from GET /templates */
export interface HtmlTemplate {
  id: string;
  name: string;
  html_template?: string;
  description?: string | null;
  preview_screenshot?: string | null;
  is_active: boolean;
  sites_count?: number;
}

export interface HtmlTemplateInput {
  name: string;
  html_template: string;
  description?: string | null;
  preview_screenshot?: string | null;
  is_active?: boolean;
}

export type LegalPageType =
  | "privacy_policy"
  | "terms_and_conditions"
  | "cookie_policy"
  | "responsible_gambling"
  | "about_us";

export interface LegalPageTemplateRow {
  id: string;
  country: string;
  page_type: LegalPageType | string;
  title: string;
  is_active: boolean;
}

export interface LegalPageTemplateFull extends LegalPageTemplateRow {
  html_content: string;
  variables: Record<string, unknown>;
  notes?: string | null;
}
