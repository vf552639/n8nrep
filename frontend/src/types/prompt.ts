export interface Prompt {
  id: string;
  agent_name: string;
  version: number;
  is_active: boolean;
  system_prompt: string;
  user_prompt: string;
  model: string;
  max_tokens?: number | null;
  max_tokens_enabled?: boolean;
  temperature: number;
  temperature_enabled?: boolean;
  frequency_penalty?: number;
  frequency_penalty_enabled?: boolean;
  presence_penalty?: number;
  presence_penalty_enabled?: boolean;
  top_p?: number;
  top_p_enabled?: boolean;
  response_format?: string;
  skip_in_pipeline?: boolean;
  min_output_length?: number;
  updated_at: string;
}

export interface PromptVersion {
  id: string;
  prompt_id: string;
  version: number;
  is_active?: boolean;
  updated_at?: string;
  system_prompt?: string;
  user_prompt?: string;
  created_at?: string;
}

export interface PromptTest {
  test_data: string;
}
