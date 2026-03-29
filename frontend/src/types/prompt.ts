export interface Prompt {
  id: string;
  agent_name: string;
  version: number;
  is_active: boolean;
  system_prompt: string;
  user_prompt: string;
  model: string;
  max_tokens?: number | null;
  temperature: number;
  frequency_penalty?: number;
  presence_penalty?: number;
  top_p?: number;
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
