import api from "./client";

export interface Settings {
  OPENROUTER_API_KEY?: string;
  DATAFORSEO_LOGIN?: string;
  DATAFORSEO_PASSWORD?: string;
  SERPAPI_API_KEY?: string;
  SERPER_API_KEY?: string;
  EXCLUDE_WORDS_DEFAULTS?: string;
  EXCLUDED_DOMAINS?: string;
  [key: string]: any;
}

export const settingsApi = {
  getSettings: () => 
    api.get<Settings>("/settings/").then(res => res.data),
    
  updateSettings: (data: Settings) => 
    api.put("/settings/", data).then(res => res.data),
};
