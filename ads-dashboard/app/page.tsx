import { AdsPlansTable } from "./components/AdsPlansTable";
import { AppSidebar } from "./components/AppSidebar";
import { DashboardMetrics } from "./components/DashboardMetrics";
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
            <p className="eyebrow">Campaign dashboard</p>
            <h2>Theo doi plan va file export</h2>
          </div>
          <div className="actions">
            <button type="button">Refresh</button>
            <button type="button" className="primary">New plan</button>
          </div>
        </header>

        {!configured ? (
          <section className="notice">
            <strong>Can them Supabase URL</strong>
            <span>
              Dien `NEXT_PUBLIC_SUPABASE_URL` trong `.env.local` hoac tren Vercel de dashboard doc du lieu that.
            </span>
          </section>
        ) : null}

        <DashboardMetrics plans={plans} />
        <AdsPlansTable plans={plans} />
      </section>
    </main>
  );
}
