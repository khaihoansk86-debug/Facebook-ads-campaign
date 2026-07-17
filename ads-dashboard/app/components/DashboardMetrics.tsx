import type { AdsPlan } from "../types/ads";
import { formatNumber } from "../lib/format";

function stat(plans: AdsPlan[], status: string) {
  return plans.filter((plan) => plan.status === status).length;
}

export function DashboardMetrics({ plans }: { plans: AdsPlan[] }) {
  const totalAds = plans.reduce((sum, plan) => sum + (plan.ads_count || 0), 0);

  return (
    <section className="metrics" aria-label="Tổng quan chiến dịch">
      <div className="metricCard metric-plan">
        <span>Tổng plan</span>
        <strong>{formatNumber(plans.length)}</strong>
      </div>
      <div className="metricCard metric-ads">
        <span>Tổng ads</span>
        <strong>{formatNumber(totalAds)}</strong>
      </div>
      <div className="metricCard metric-ready">
        <span>Sẵn sàng</span>
        <strong>{formatNumber(stat(plans, "ready"))}</strong>
      </div>
      <div className="metricCard metric-export">
        <span>Đã export</span>
        <strong>{formatNumber(stat(plans, "exported"))}</strong>
      </div>
    </section>
  );
}
