import type { AdsPlan } from "../types/ads";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const publishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

export function isSupabaseConfigured() {
  return Boolean(
    supabaseUrl &&
      publishableKey &&
      !supabaseUrl.includes("your-project-ref")
  );
}

export async function fetchAdsPlans(): Promise<AdsPlan[]> {
  if (!isSupabaseConfigured()) {
    return [];
  }

  const params = new URLSearchParams({
    select: "*,ads_plan_items(*)",
    order: "updated_at.desc"
  });
  const response = await fetch(`${supabaseUrl}/rest/v1/ads_plans?${params}`, {
    headers: {
      apikey: publishableKey as string,
      Authorization: `Bearer ${publishableKey}`
    },
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`Supabase returned ${response.status}`);
  }

  return response.json();
}
