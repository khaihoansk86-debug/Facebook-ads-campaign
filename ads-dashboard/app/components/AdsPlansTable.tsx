import { formatCurrency, formatDate, formatNumber } from "../lib/format";
import type { AdsPlan } from "../types/ads";

const statusLabels: Record<string, string> = {
  draft: "Nháp",
  review: "Cần duyệt",
  ready: "Sẵn sàng",
  exported: "Đã export",
  error: "Có lỗi"
};

export function AdsPlansTable({ plans }: { plans: AdsPlan[] }) {
  return (
    <section className="panel">
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
                  <strong>Preview bundle</strong>
                  <span>{items.length ? `${items.length} dòng đã đồng bộ` : "Đang chờ lần sync desktop tiếp theo"}</span>
                </div>
                {items.length ? (
                  <div className="bundleGrid">
                    {items.map((item) => (
                      <div className="bundleItem" key={item.id}>
                        <div className="bundleItemHead">
                          <span>#{item.row_index}</span>
                          <strong>{item.ad_name || item.campaign_name || "Ads chưa đặt tên"}</strong>
                        </div>
                        <dl>
                          <div>
                            <dt>Nhóm QC</dt>
                            <dd>{item.adset_name || "-"}</dd>
                          </div>
                          <div>
                            <dt>Tối ưu</dt>
                            <dd>{item.optimization_goal || item.objective || "-"}</dd>
                          </div>
                          <div>
                            <dt>Chuyển đổi</dt>
                            <dd>{item.destination_type || "-"}</dd>
                          </div>
                          <div>
                            <dt>Đối tượng</dt>
                            <dd>{item.audience_name || "-"}</dd>
                          </div>
                          <div>
                            <dt>Vị trí</dt>
                            <dd>{item.placement_summary || "-"}</dd>
                          </div>
                          <div>
                            <dt>Ngân sách</dt>
                            <dd>{formatCurrency(item.budget_amount)}</dd>
                          </div>
                        </dl>
                        <div className="linkCell">
                          {item.post_url ? <a href={item.post_url}>Bài viết</a> : null}
                          {item.notion_url ? <a href={item.notion_url}>Dòng Notion</a> : null}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="empty">Chạy export/sync lại từ desktop để dashboard hiện từng nhóm quảng cáo, đối tượng và vị trí.</p>
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
