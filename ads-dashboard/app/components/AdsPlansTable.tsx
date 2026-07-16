import { formatCurrency, formatDate, formatNumber } from "../lib/format";
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

      <div className="planStack">
        {plans.map((plan) => {
          const items = [...(plan.ads_plan_items || [])].sort((a, b) => a.row_index - b.row_index);

          return (
            <article className="planCard" key={plan.id}>
              <div className="planCardTop">
                <div>
                  <p className="eyebrow">Campaign plan</p>
                  <h4>{plan.name}</h4>
                  <span>Updated {formatDate(plan.updated_at)}</span>
                </div>
                <div className="planMeta">
                  <span className={`status ${plan.status}`}>{statusLabels[plan.status] || plan.status}</span>
                  <strong>{formatNumber(plan.ads_count)} ads</strong>
                  <span>{formatNumber(plan.adsets_count)} ad sets</span>
                </div>
              </div>

              <div className="planFacts">
                <span>Objective: <strong>{plan.objective || "-"}</strong></span>
                <span>Budget: <strong>{formatCurrency(plan.budget_total)}</strong></span>
                <span>Last export: <strong>{formatDate(plan.last_exported_at)}</strong></span>
                <span className="linkCell">
                  {plan.latest_csv_url ? <a href={plan.latest_csv_url}>CSV</a> : null}
                  {plan.notion_url ? <a href={plan.notion_url}>Notion</a> : null}
                </span>
              </div>

              <div className="bundlePreview">
                <div className="bundleHeader">
                  <strong>Bundle preview</strong>
                  <span>{items.length ? `${items.length} synced rows` : "Waiting for next desktop sync"}</span>
                </div>
                {items.length ? (
                  <div className="bundleGrid">
                    {items.map((item) => (
                      <div className="bundleItem" key={item.id}>
                        <div className="bundleItemHead">
                          <span>#{item.row_index}</span>
                          <strong>{item.ad_name || item.campaign_name || "Untitled ad"}</strong>
                        </div>
                        <dl>
                          <div>
                            <dt>Ad set</dt>
                            <dd>{item.adset_name || "-"}</dd>
                          </div>
                          <div>
                            <dt>Goal</dt>
                            <dd>{item.optimization_goal || item.objective || "-"}</dd>
                          </div>
                          <div>
                            <dt>Destination</dt>
                            <dd>{item.destination_type || "-"}</dd>
                          </div>
                          <div>
                            <dt>Audience</dt>
                            <dd>{item.audience_name || "-"}</dd>
                          </div>
                          <div>
                            <dt>Placement</dt>
                            <dd>{item.placement_summary || "-"}</dd>
                          </div>
                          <div>
                            <dt>Budget</dt>
                            <dd>{formatCurrency(item.budget_amount)}</dd>
                          </div>
                        </dl>
                        <div className="linkCell">
                          {item.post_url ? <a href={item.post_url}>Post</a> : null}
                          {item.notion_url ? <a href={item.notion_url}>Notion row</a> : null}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="empty">Chay export/sync lai tu desktop de dashboard hien tung adset, audience va placement.</p>
                )}
              </div>
            </article>
          );
        })}
        {!plans.length ? (
          <p className="empty">
            Tool desktop sync len Supabase xong thi campaign se hien o day.
          </p>
        ) : null}
      </div>
    </section>
  );
}
