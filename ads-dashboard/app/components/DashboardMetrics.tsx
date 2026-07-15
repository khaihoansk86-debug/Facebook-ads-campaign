import type { AdsPlan } from "../types/ads";
import { formatNumber } from "../lib/format";

function stat(plans: AdsPlan[], status: string) {
  return plans.filter((plan) => plan.status === status).length;
}

export function DashboardMetrics({ plans }: { plans: AdsPlan[] }) {
  const totalAds = plans.reduce((sum, plan) => sum + (plan.ads_count || 0), 0);

  return (
    <section className="metrics" aria-label="Campaign summary">
      <div>
        <span>Total plans</span>
        <strong>{formatNumber(plans.length)}</strong>
      </div>
      <div>
        <span>Total ads</span>
        <strong>{formatNumber(totalAds)}</strong>
      </div>
      <div>
        <span>Ready</span>
        <strong>{formatNumber(stat(plans, "ready"))}</strong>
      </div>
      <div>
        <span>Exported</span>
        <strong>{formatNumber(stat(plans, "exported"))}</strong>
      </div>
    </section>
  );
}
