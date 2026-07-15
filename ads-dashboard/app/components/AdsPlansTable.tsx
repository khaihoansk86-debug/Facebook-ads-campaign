import { formatDate, formatNumber } from "../lib/format";
import type { AdsPlan } from "../types/ads";

const statusLabels: Record<string, string> = {
  draft: "Draft",
  review: "Need review",
  ready: "Ready",
  exported: "Exported",
  error: "Error"
};

export function AdsPlansTable({ plans }: { plans: AdsPlan[] }) {
  return (
    <section className="panel">
      <div className="panelHead">
        <div>
          <h3>Ads plans</h3>
          <span>{plans.length ? `${plans.length} plan dang theo doi` : "Chua co du lieu dong bo"}</span>
        </div>
        <input aria-label="Search plans" placeholder="Search campaign, owner, objective" />
      </div>

      <div className="tableWrap">
        <table>
          <thead>
            <tr>
              <th>Plan</th>
              <th>Status</th>
              <th>Objective</th>
              <th>Scale</th>
              <th>Owner</th>
              <th>Last export</th>
              <th>Links</th>
            </tr>
          </thead>
          <tbody>
            {plans.map((plan) => (
              <tr key={plan.id}>
                <td>
                  <strong>{plan.name}</strong>
                  <span>Updated {formatDate(plan.updated_at)}</span>
                </td>
                <td>
                  <span className={`status ${plan.status}`}>{statusLabels[plan.status] || plan.status}</span>
                </td>
                <td>{plan.objective || "-"}</td>
                <td>
                  {formatNumber(plan.ads_count)} ads / {formatNumber(plan.adsets_count)} ad sets
                </td>
                <td>{plan.owner_name || "-"}</td>
                <td>{formatDate(plan.last_exported_at)}</td>
                <td className="linkCell">
                  {plan.latest_csv_url ? <a href={plan.latest_csv_url}>CSV</a> : <span>-</span>}
                  {plan.notion_url ? <a href={plan.notion_url}>Notion</a> : null}
                </td>
              </tr>
            ))}
            {!plans.length ? (
              <tr>
                <td colSpan={7} className="empty">
                  Tool desktop sync len Supabase xong thi campaign se hien o day.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
