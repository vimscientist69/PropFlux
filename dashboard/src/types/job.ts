export interface JobRequest {
  site: string;
  url?: string;
  limit?: number;
  max_pages?: number;
  skip_dynamic_fields?: boolean;
  settings_overrides?: Record<string, unknown>;
}

