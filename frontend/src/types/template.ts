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

export const LEGAL_PAGE_TYPE_LABELS: Record<string, string> = {
  privacy_policy: "Privacy Policy",
  terms_and_conditions: "Terms & Conditions",
  cookie_policy: "Cookie Policy",
  responsible_gambling: "Responsible Gambling",
  about_us: "About Us",
};

/** Same set as backend `LEGAL_PAGE_TYPES` — used for blueprint legal defaults UI. */
export const LEGAL_PAGE_TYPES_SET = new Set(Object.keys(LEGAL_PAGE_TYPE_LABELS));

export interface LegalPageTemplateRow {
  id: string;
  name: string;
  page_type: LegalPageType | string;
  content_format: string;
  is_active: boolean;
}

export interface LegalPageTemplateFull extends LegalPageTemplateRow {
  content: string;
  variables: Record<string, unknown>;
  notes?: string | null;
}

export interface LegalBlueprintPageTypeGroup {
  page_type: string;
  page_title: string;
  default_template_id?: string | null;
  templates: { id: string; name: string }[];
}

export interface LegalForBlueprintResponse {
  legal_page_types: LegalBlueprintPageTypeGroup[];
}
