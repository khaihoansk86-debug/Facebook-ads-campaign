import Link from 'next/link';
import { formatCurrency, formatDate, formatNumber } from "../lib/format";
import type { AdsPlan, AdsPlanItem } from "../types/ads";

const statusLabels: Record<string, string> = {
  draft: "Nháp",
  review: "Cần duyệt",
  ready: "Sẵn sàng",
  exported: "Đã export",
  error: "Có lỗi"
};

function tag(label: string, value?: string | number | null, href?: string) {
  if (!value) return null;

  if (href) {
    return (
      <Link href={href} className="tagChip" style={{ textDecoration: 'none' }}>
        <b>{label}</b>
        {value}
      </Link>
    );
  }

  return (
    <span className="tagChip">
      <b>{label}</b>
      {value}
    </span>
  );
}

function adTitle(item: AdsPlanItem) {
  return item.ad_name || item.campaign_name || "Ads chưa đặt tên";
}

export function AdsPlansTable({ plans }: { plans: AdsPlan[] }) {
  return (
    <section className="panel" id="campaigns">
      <div className="panelHead">
        <div>
          <h3>Plan quảng cáo</h3>
          <span>{plans.length ? `${plans.length} plan đang theo dõi` : "Chưa có dữ liệu đồng bộ"}</span>
        </div>
        <input aria-label="Tìm kiếm plan" placeholder="Tìm chiến dịch, người phụ trách, mục tiêu" />
      </div>

      <div className="planStack">
        {plans.map((plan) => {
          const items = [...(plan.ads_plan_items || [])].sort((a, b) => a.row_index - b.row_index);

          return (
            <article className="planCard" key={plan.id}>
              <div className="planCardTop">
                <div>
                  <p className="eyebrow">Plan chiến dịch</p>
                  <h4>{plan.name}</h4>
                  <span>Cập nhật {formatDate(plan.updated_at)}</span>
                </div>
                <div className="planMeta">
                  <span className={`status ${plan.status}`}>{statusLabels[plan.status] || plan.status}</span>
                  <strong>{formatNumber(plan.ads_count)} ads</strong>
                  <span>{formatNumber(plan.adsets_count)} nhóm quảng cáo</span>
                </div>
              </div>

              <div className="planFacts">
                <span>Mục tiêu: <strong>{plan.objective || "-"}</strong></span>
                <span>Ngân sách: <strong>{formatCurrency(plan.budget_total)}</strong></span>
                <span>Export gần nhất: <strong>{formatDate(plan.last_exported_at)}</strong></span>
                <span className="linkCell">
                  {plan.latest_csv_url ? <a href={plan.latest_csv_url}>CSV</a> : null}
                  {plan.notion_url ? <a href={plan.notion_url}>Notion</a> : null}
                </span>
              </div>

              <div className="bundlePreview">
                <div className="bundleHeader">
                  <div>
                    <strong>Dòng ads trong bundle</strong>
                    <span>{items.length ? `${items.length} dòng đã đồng bộ` : "Đang chờ lần sync desktop tiếp theo"}</span>
                  </div>
                  <span className="hintText">Mỗi dòng là 1 ads, tag là thông tin setup nhanh.</span>
                </div>

                {items.length ? (
                  <div className="adRows">
                    {items.map((item) => (
                      <div className="adRow" key={item.id}>
                        <div className="adRowIndex">#{item.row_index || 1}</div>
                        <div className="adRowMain">
                          <strong>{adTitle(item)}</strong>
                          <span>{item.adset_name || "Chưa có nhóm quảng cáo"}</span>
                        </div>
                        <div className="adRowTags">
                          {tag("Tối ưu", item.optimization_goal || item.objective)}
                          {tag("Đích", item.destination_type)}
                          {tag("Đối tượng", item.audience_name, `/?tab=audiences#${item.audience_name ? encodeURIComponent(item.audience_name) : ''}`)}
                          {tag("Vị trí", item.placement_summary, `/?tab=placements#${item.placement_summary ? encodeURIComponent(item.placement_summary) : ''}`)}
                          {tag("Ngân sách", formatCurrency(item.budget_amount))}
                        </div>
                        <div className="adRowLinks">
                          {item.post_url ? <a href={item.post_url}>Bài viết</a> : null}
                          {item.notion_url ? <a href={item.notion_url}>Notion</a> : null}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="empty">
                    Chạy export/sync lại từ desktop để dashboard hiện từng ads, nhóm quảng cáo, đối tượng và vị trí.
                  </p>
                )}
              </div>
            </article>
          );
        })}
        {!plans.length ? (
          <p className="empty">
            Tool desktop sync lên Supabase xong thì chiến dịch sẽ hiện ở đây.
          </p>
        ) : null}
      </div>
    </section>
  );
}
