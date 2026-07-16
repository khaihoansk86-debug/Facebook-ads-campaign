import { formatCurrency, formatDate } from "../lib/format";
import type { AdsPlan, AdsPlanItem } from "../types/ads";

type SetupGroup = {
  name: string;
  count: number;
  plans: Set<string>;
  examples: string[];
};

function allItems(plans: AdsPlan[]) {
  return plans.flatMap((plan) => (plan.ads_plan_items || []).map((item) => ({ item, plan })));
}

function groupBySetup(
  plans: AdsPlan[],
  getName: (item: AdsPlanItem) => string | null,
  getExample: (item: AdsPlanItem) => string | null
) {
  const groups = new Map<string, SetupGroup>();

  for (const { item, plan } of allItems(plans)) {
    const name = getName(item)?.trim();
    if (!name) continue;

    const group = groups.get(name) || {
      name,
      count: 0,
      plans: new Set<string>(),
      examples: []
    };
    const example = getExample(item);

    group.count += 1;
    group.plans.add(plan.name);
    if (example && !group.examples.includes(example) && group.examples.length < 3) {
      group.examples.push(example);
    }
    groups.set(name, group);
  }

  return [...groups.values()].sort((a, b) => b.count - a.count);
}

function SetupPanel({
  id,
  title,
  description,
  empty,
  groups
}: {
  id: string;
  title: string;
  description: string;
  empty: string;
  groups: SetupGroup[];
}) {
  return (
    <section className="opsPanel" id={id}>
      <div className="opsPanelHead">
        <div>
          <p className="eyebrow">Khu setup</p>
          <h3>{title}</h3>
          <span>{description}</span>
        </div>
        <span className="countBadge">{groups.length}</span>
      </div>

      {groups.length ? (
        <div className="setupList">
          {groups.map((group) => (
            <button className="setupItem" type="button" key={group.name}>
              <span className="setupItemTop">
                <strong>{group.name}</strong>
                <em>{group.count} ads</em>
              </span>
              <span className="setupTags">
                {[...group.plans].slice(0, 2).map((plan) => (
                  <span className="tagChip compact" key={plan}>
                    <b>Plan</b>
                    {plan}
                  </span>
                ))}
                {group.examples.map((example) => (
                  <span className="tagChip compact" key={example}>
                    <b>Ads</b>
                    {example}
                  </span>
                ))}
              </span>
            </button>
          ))}
        </div>
      ) : (
        <p className="empty small">{empty}</p>
      )}
    </section>
  );
}

function ExportsPanel({ plans }: { plans: AdsPlan[] }) {
  const exportedPlans = plans.filter((plan) => plan.latest_csv_url || plan.last_exported_at);

  return (
    <section className="opsPanel" id="exports">
      <div className="opsPanelHead">
        <div>
          <p className="eyebrow">File bàn giao</p>
          <h3>File export</h3>
          <span>Gom CSV cuối cùng để team ads tải và kiểm tra trước khi upload.</span>
        </div>
        <span className="countBadge">{exportedPlans.length}</span>
      </div>

      {exportedPlans.length ? (
        <div className="setupList">
          {exportedPlans.map((plan) => (
            <a className="setupItem" href={plan.latest_csv_url || "#"} key={plan.id}>
              <span className="setupItemTop">
                <strong>{plan.name}</strong>
                <em>{formatDate(plan.last_exported_at)}</em>
              </span>
              <span className="setupTags">
                <span className="tagChip compact">
                  <b>Ads</b>
                  {plan.ads_count || 0}
                </span>
                <span className="tagChip compact">
                  <b>Ngân sách</b>
                  {formatCurrency(plan.budget_total)}
                </span>
              </span>
            </a>
          ))}
        </div>
      ) : (
        <p className="empty small">Chưa có file export từ desktop.</p>
      )}
    </section>
  );
}

export function OpsBreakdown({ plans }: { plans: AdsPlan[] }) {
  const audiences = groupBySetup(
    plans,
    (item) => item.audience_name,
    (item) => item.ad_name || item.adset_name
  );
  const placements = groupBySetup(
    plans,
    (item) => item.placement_summary,
    (item) => item.ad_name || item.adset_name
  );

  return (
    <section className="opsGrid" aria-label="Khu setup chi tiết">
      <SetupPanel
        id="audiences"
        title="Đối tượng"
        description="Tách riêng audience để team marketing và ads kiểm tra trước khi xuất CSV."
        empty="Chưa có đối tượng. Sync lại desktop sau khi bundle có audience."
        groups={audiences}
      />
      <SetupPanel
        id="placements"
        title="Vị trí quảng cáo"
        description="Tách placement ra khỏi dòng ads để dễ rà soát nơi chạy quảng cáo."
        empty="Chưa có vị trí quảng cáo. Sync lại desktop sau khi bundle có placement."
        groups={placements}
      />
      <ExportsPanel plans={plans} />
    </section>
  );
}
