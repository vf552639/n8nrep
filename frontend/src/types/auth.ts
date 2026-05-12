export type ProviderAuthMethod = "oauth" | "api_key" | null;

export interface LoginStatus {
  logged_in: boolean;
  method: ProviderAuthMethod;
  account_id: string | null;
}

export interface LoginStartResponse {
  method: "cli" | "browser";
  url?: string | null;
  cli_command?: string[] | null;
  notice: string;
}
