export interface PromptPresetItem {
  id: string;
  agent_name: string;
  prompt_id: string;
}

export interface PromptPreset {
  id: string;
  name: string;
  description?: string | null;
  is_default: boolean;
  items: PromptPresetItem[];
  created_at: string;
  updated_at: string;
}

export interface PromptPresetCreate {
  name: string;
  description?: string | null;
  is_default?: boolean;
  items: { agent_name: string; prompt_id: string }[];
}
