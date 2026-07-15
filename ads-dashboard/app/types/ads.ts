export type AdsPlan = {
  id: string;
  external_id: string | null;
  name: string;
  status: string;
  objective: string | null;
  owner_name: string | null;
  ads_count: number | null;
  adsets_count: number | null;
  audiences_count: number | null;
  budget_total: number | null;
  source: string;
  source_payload: Record<string, unknown>;
  notion_url: string | null;
  latest_csv_url: string | null;
  last_exported_at: string | null;
  created_at: string;
  updated_at: string;
};
