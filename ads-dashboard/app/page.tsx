import { AdsPlansTable } from "./components/AdsPlansTable";
import { AppSidebar } from "./components/AppSidebar";
import { DashboardMetrics } from "./components/DashboardMetrics";
import { OpsBreakdown } from "./components/OpsBreakdown";
import { fetchAdsPlans, isSupabaseConfigured } from "./lib/supabase-rest";

export default async function Home() {
  const configured = isSupabaseConfigured();
  const plans = configured ? await fetchAdsPlans() : [];

  return (
    <main className="shell">
      <AppSidebar />

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Bảng điều phối chiến dịch</p>
            <h2>Theo dõi plan, bundle và file export</h2>
          </div>
          <div className="actions">
            <button type="button">Làm mới</button>
            <button type="button" className="primary">Plan mới</button>
          </div>
        </header>

        {!configured ? (
          <section className="notice">
            <strong>Cần thêm Supabase URL</strong>
            <span>
              Điền `NEXT_PUBLIC_SUPABASE_URL` trong `.env.local` hoặc trên Vercel để dashboard đọc dữ liệu thật.
            </span>
          </section>
        ) : null}

        <DashboardMetrics plans={plans} />
        <AdsPlansTable plans={plans} />
        <OpsBreakdown plans={plans} />
      </section>
    </main>
  );
}
